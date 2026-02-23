#!/usr/bin/env python3
"""
Phase 3: Merge all intermediates into unified metadata.json.

Combines:
- intermediates/tables_page_map.json  → TABLE nodes
- intermediates/figures_page_map.json → FIGURE nodes
- intermediates/sections.json         → SPEC_CHUNK nodes
- intermediates/registers.json        → REGISTER + REG_CLASS nodes
- intermediates/features.json         → FEATURE + HD_SEQUENCE nodes

Into: metadata/metadata.json (same schema as v1)

This is purely deterministic — no LLM calls.
"""

import json
import re
import time
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.config import (
    get_page_offset, get_classification_rules, get_intermediates_dir,
    get_output_dir, PIPELINE_ROOT
)
from shared.data_classes import Node, Relation
from shared.utils import (
    load_json, save_json, extract_keywords, extract_technical_terms,
    find_table_references, find_figure_references, classify_by_rules,
    normalize_offset, print_step, print_done
)


METADATA_VERSION = "2.0.0"


def merge_all(config: dict, dry_run: bool = False, validate_only: bool = False):
    """Merge all intermediate files into metadata.json."""
    
    intermediates = get_intermediates_dir()
    output_dir = get_output_dir()
    output_path = output_dir / "metadata.json"
    page_offset = get_page_offset(config)
    
    # Validate only mode
    if validate_only:
        if output_path.exists():
            metadata = load_json(output_path)
            _validate(metadata)
        else:
            print("  No metadata.json found to validate")
        return
    
    # Collect all nodes and relations
    all_nodes = []
    all_relations = []
    
    # --- TABLE nodes ---
    tables_path = intermediates / "tables_page_map.json"
    if tables_path.exists():
        print_step("1/5", "Processing TABLE nodes...")
        tables_data = load_json(tables_path)
        table_rules = get_classification_rules(config, "TABLE")
        table_nodes = _create_table_nodes(tables_data, table_rules, page_offset)
        all_nodes.extend(table_nodes)
        print(f"    TABLE nodes: {len(table_nodes)}")
    
    # --- FIGURE nodes ---
    figures_path = intermediates / "figures_page_map.json"
    if figures_path.exists():
        print_step("2/5", "Processing FIGURE nodes...")
        figures_data = load_json(figures_path)
        figure_rules = get_classification_rules(config, "FIGURE")
        figure_nodes = _create_figure_nodes(figures_data, figure_rules, page_offset)
        all_nodes.extend(figure_nodes)
        print(f"    FIGURE nodes: {len(figure_nodes)}")
    
    # --- SPEC_CHUNK nodes ---
    sections_path = intermediates / "sections.json"
    if sections_path.exists():
        print_step("3/5", "Processing SPEC_CHUNK nodes...")
        sections_data = load_json(sections_path)
        chunk_nodes, chunk_relations = _create_chunk_nodes(sections_data, page_offset)
        all_nodes.extend(chunk_nodes)
        all_relations.extend(chunk_relations)
        print(f"    SPEC_CHUNK nodes: {len(chunk_nodes)}")
        print(f"    CHILD_OF relations: {len(chunk_relations)}")
    
    # --- REGISTER + REG_CLASS nodes ---
    registers_path = intermediates / "registers.json"
    if registers_path.exists():
        print_step("4/5", "Processing REGISTER + REG_CLASS nodes...")
        registers_data = load_json(registers_path)
        reg_nodes, reg_class_nodes, reg_relations = _create_register_nodes(
            registers_data, page_offset
        )
        all_nodes.extend(reg_nodes)
        all_nodes.extend(reg_class_nodes)
        all_relations.extend(reg_relations)
        print(f"    REGISTER nodes: {len(reg_nodes)}")
        print(f"    REG_CLASS nodes: {len(reg_class_nodes)}")
        print(f"    Register relations: {len(reg_relations)}")
    
    # --- FEATURE + HD_SEQUENCE nodes ---
    features_path = intermediates / "features.json"
    if features_path.exists():
        print_step("5/5", "Processing FEATURE + HD_SEQUENCE nodes...")
        features_data = load_json(features_path)
        feat_nodes, hd_nodes, feat_relations = _create_feature_nodes(features_data)
        all_nodes.extend(feat_nodes)
        all_nodes.extend(hd_nodes)
        all_relations.extend(feat_relations)
        print(f"    FEATURE nodes: {len(feat_nodes)}")
        print(f"    HD_SEQUENCE nodes: {len(hd_nodes)}")
        print(f"    Feature relations: {len(feat_relations)}")
    
    # --- Cross-reference relations ---
    print(f"  Building cross-reference relations...")
    node_ids = {n["id"] for n in all_nodes}
    xref_relations = _build_cross_references(all_nodes, node_ids)
    all_relations.extend(xref_relations)
    print(f"    Cross-reference relations: {len(xref_relations)}")
    
    # --- Statistics ---
    by_type = {}
    for n in all_nodes:
        t = n["type"]
        by_type[t] = by_type.get(t, 0) + 1
    
    rel_by_type = {}
    for r in all_relations:
        t = r["type"]
        rel_by_type[t] = rel_by_type.get(t, 0) + 1
    
    # --- Build final output ---
    metadata = {
        "metadata_version": METADATA_VERSION,
        "spec_info": {
            "name": config["spec"]["name"],
            "version": config["spec"]["version"],
            "page_offset": get_page_offset(config)
        },
        "extraction_info": {
            "extracted_date": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pipeline": "rag_v2",
            "sources": {
                "tables": str(tables_path) if tables_path.exists() else None,
                "figures": str(figures_path) if figures_path.exists() else None,
                "sections": str(sections_path) if sections_path.exists() else None,
                "registers": str(registers_path) if registers_path.exists() else None,
                "features": str(features_path) if features_path.exists() else None,
            },
            "statistics": {
                "total_nodes": len(all_nodes),
                "by_type": by_type,
                "total_relations": len(all_relations),
                "relations_by_type": rel_by_type
            }
        },
        "nodes": all_nodes,
        "relations": all_relations
    }
    
    # Validate
    issues = _validate(metadata)
    
    if dry_run:
        print(f"\n  [DRY RUN] Would write metadata.json:")
        print(f"    Nodes: {len(all_nodes)}")
        print(f"    Relations: {len(all_relations)}")
        for t, c in sorted(by_type.items()):
            print(f"      {t}: {c}")
        return
    
    # Backup existing
    if output_path.exists():
        backup_dir = output_dir / "backups"
        backup_dir.mkdir(exist_ok=True)
        timestamp = time.strftime("%Y%m%dT%H%M%S")
        backup_path = backup_dir / f"metadata_{timestamp}.json"
        shutil.copy2(output_path, backup_path)
        print(f"  Backed up to: {backup_path}")
    
    # Write
    save_json(metadata, output_path)
    
    print(f"\n  Summary:")
    print(f"    Total nodes:     {len(all_nodes)}")
    print(f"    Total relations: {len(all_relations)}")
    for t, c in sorted(by_type.items()):
        print(f"      {t:15s}: {c}")


# =============================================================================
# NODE GENERATORS
# =============================================================================

def _create_table_nodes(tables_data: dict, rules: list, page_offset: int) -> List[dict]:
    """Create TABLE nodes from tables_page_map.json."""
    nodes = []
    for table in tables_data.get("tables", []):
        completed = table.get("conversion", {}).get("status") == "COMPLETED"
        table_type = classify_by_rules(table.get("title", ""), rules) if rules else "OTHER"
        
        node = {
            "id": table["id"],
            "type": "TABLE",
            "name": table.get("title", table["spec_reference"]),
            "description": table.get("abstract", ""),
            "index_keywords": extract_keywords(table.get("title", "") + " " + table.get("abstract", "")),
            "source": {
                "page": table.get("spec_page", 0),
                "pdf_page": table.get("definition_page", 0),
                "spec_reference": table.get("spec_reference", "")
            },
            "coverage": {"status": "NOT_IMPLEMENTED", "notes": "", "implemented_in": ""},
            "confidence": 0.95 if completed else 0.7,
            "validation_status": "AUTO",
            "extras": {
                "table_number": table.get("spec_reference", ""),
                "csv_file": table.get("conversion", {}).get("csv_file", ""),
                "table_type": table_type
            }
        }
        nodes.append(node)
    return nodes


def _create_figure_nodes(figures_data: dict, rules: list, page_offset: int) -> List[dict]:
    """Create FIGURE nodes from figures_page_map.json."""
    nodes = []
    for figure in figures_data.get("figures", []):
        completed = figure.get("transcription", {}).get("status") == "COMPLETED"
        fig_type = classify_by_rules(
            figure.get("title", "") + " " + figure.get("abstract", ""), rules
        ) if rules else "OTHER"
        
        node = {
            "id": figure["id"],
            "type": "FIGURE",
            "name": figure.get("title", figure["spec_reference"]),
            "description": figure.get("abstract", ""),
            "index_keywords": extract_keywords(figure.get("title", "") + " " + figure.get("abstract", "")),
            "source": {
                "page": figure.get("spec_page", 0),
                "pdf_page": figure.get("definition_page", 0),
                "spec_reference": figure.get("spec_reference", "")
            },
            "coverage": {"status": "NOT_IMPLEMENTED", "notes": "", "implemented_in": ""},
            "confidence": 0.9 if completed else 0.7,
            "validation_status": "AUTO",
            "extras": {
                "figure_number": figure.get("spec_reference", ""),
                "figure_type": fig_type,
                "text_diagram_file": figure.get("transcription", {}).get("plantuml_file", ""),
                "text_diagram_format": "PLANTUML" if completed else "NONE"
            }
        }
        nodes.append(node)
    return nodes


def _create_chunk_nodes(sections_data: dict, page_offset: int) -> tuple:
    """Create SPEC_CHUNK nodes + CHILD_OF relations."""
    nodes = []
    relations = []
    
    sections = sections_data.get("sections", {})
    
    # Build parent mapping for CHILD_OF
    sec_nums = sorted(sections.keys())
    
    for sec_num, section in sections.items():
        for chunk in section.get("chunks", []):
            node = {
                "id": chunk["chunk_id"],
                "type": "SPEC_CHUNK",
                "name": f"{section['title']} (Chunk {chunk['chunk_index']})",
                "description": chunk.get("abstract", ""),
                "index_keywords": section.get("index", {}).get("keywords", []),
                "source": {
                    "page": chunk.get("spec_page", section["source"]["spec_page_start"]),
                    "pdf_page": chunk.get("spec_page", section["source"]["spec_page_start"]) + page_offset,
                    "section_number": sec_num
                },
                "coverage": {"status": "NOT_IMPLEMENTED", "notes": "", "implemented_in": ""},
                "confidence": section.get("extraction", {}).get("confidence", 0.9),
                "validation_status": "AUTO",
                "extras": {
                    "section_id": section.get("id", ""),
                    "section_number": sec_num,
                    "section_title": section["title"],
                    "chunk_index": chunk["chunk_index"],
                    "word_count": chunk.get("word_count", 0),
                    "full_text": chunk.get("raw", ""),
                    "technical_terms": section.get("index", {}).get("technical_terms", [])
                }
            }
            nodes.append(node)
    
    # Build CHILD_OF relations based on section hierarchy
    for sec_num in sec_nums:
        parts = sec_num.split('.')
        if len(parts) > 1:
            parent_num = '.'.join(parts[:-1])
            if parent_num in sections:
                # Find first chunk of each
                child_chunks = sections[sec_num].get("chunks", [])
                parent_chunks = sections[parent_num].get("chunks", [])
                if child_chunks and parent_chunks:
                    relations.append({
                        "id": f"REL_CHILD_{sec_num.replace('.', '_')}",
                        "type": "CHILD_OF",
                        "source_node": child_chunks[0]["chunk_id"],
                        "target_node": parent_chunks[0]["chunk_id"],
                        "description": f"Section {sec_num} is child of section {parent_num}"
                    })
    
    return nodes, relations


def _create_register_nodes(registers_data: dict, page_offset: int) -> tuple:
    """Create REGISTER + REG_CLASS nodes and relations."""
    reg_nodes = []
    reg_class_nodes = []
    relations = []
    rel_counter = 0
    
    # REG_CLASS nodes
    for rc in registers_data.get("register_classes", []):
        node = {
            "id": rc["id"],
            "type": "REG_CLASS",
            "name": rc["name"],
            "description": f"Register class: {rc['name']} ({rc['address_start']} - {rc['address_end']})",
            "index_keywords": extract_keywords(rc["name"]),
            "source": {"table": "TABLE_1_1"},
            "coverage": {"status": "NOT_IMPLEMENTED", "notes": "", "implemented_in": ""},
            "confidence": 1.0,
            "validation_status": "AUTO",
            "extras": {
                "address_range": {"start": rc["address_start"], "end": rc["address_end"]},
                "version_support": {"1.00": True, "2.00": True, "3.00": True}
            }
        }
        reg_class_nodes.append(node)
    
    # REGISTER nodes
    for reg in registers_data.get("registers", []):
        offset_hex = reg.get("offset", "")
        offset_norm = normalize_offset(offset_hex)
        
        node = {
            "id": reg["id"],
            "type": "REGISTER",
            "name": reg["name"],
            "description": f"Register at offset {offset_hex}",
            "index_keywords": extract_keywords(reg["name"]) + [f"offset {offset_hex}", f"0x{offset_norm}"],
            "source": {
                "page": reg.get("source", {}).get("page", 0),
                "pdf_page": reg.get("source", {}).get("definition_page", 0),
                "section_number": reg.get("spec_section", "")
            },
            "coverage": {"status": "NOT_IMPLEMENTED", "notes": "", "implemented_in": ""},
            "confidence": 0.95,
            "validation_status": "AUTO",
            "extras": {
                "offset": f"0x{offset_norm}",
                "offset_hex": offset_hex,
                "size_bits": sum(f.get("width", 0) for f in reg.get("fields", [])),
                "spec_section": reg.get("spec_section", ""),
                "spec_table": reg.get("spec_table", ""),
                "class_id": reg.get("class_id", ""),
                "fields": reg.get("fields", [])
            }
        }
        reg_nodes.append(node)
        
        # BELONGS_TO relation
        if reg.get("class_id"):
            rel_counter += 1
            relations.append({
                "id": f"REL_BELONGS_{rel_counter:03d}",
                "type": "BELONGS_TO",
                "source_node": reg["id"],
                "target_node": reg["class_id"]
            })
        
        # DEFINED_BY relation (if spec_table exists)
        if reg.get("spec_table"):
            rel_counter += 1
            relations.append({
                "id": f"REL_DEFINED_{rel_counter:03d}",
                "type": "DEFINED_BY",
                "source_node": reg["id"],
                "target_node": reg["spec_table"]
            })
    
    return reg_nodes, reg_class_nodes, relations


def _create_feature_nodes(features_data: dict) -> tuple:
    """Create FEATURE + HD_SEQUENCE nodes and relations."""
    feat_nodes = []
    hd_nodes = []
    relations = list(features_data.get("relations", []))
    
    for f in features_data.get("features", []):
        node = {
            "id": f["id"],
            "type": "FEATURE",
            "name": f["name"],
            "description": f.get("description", ""),
            "index_keywords": f.get("index_keywords", extract_keywords(f["name"])),
            "source": {},
            "coverage": {"status": "NOT_IMPLEMENTED", "notes": "", "implemented_in": ""},
            "confidence": f.get("confidence", 1.0),
            "validation_status": f.get("validation_status", "AUTO"),
            "extras": {
                "groups": f.get("groups", []),
                "priority": f.get("priority", "P0"),
                "parent_id": f.get("parent_id"),
                "figures": f.get("figures", []),
                "tables": f.get("tables", []),
                "registers": f.get("registers", []),
                "spec_sections": f.get("spec_sections", [])
            }
        }
        feat_nodes.append(node)
    
    for h in features_data.get("hd_sequences", []):
        node = {
            "id": h["id"],
            "type": "HD_SEQUENCE",
            "name": h["name"],
            "description": h.get("description", ""),
            "index_keywords": h.get("index_keywords", extract_keywords(h["name"])),
            "source": {},
            "coverage": {"status": "NOT_IMPLEMENTED", "notes": "", "implemented_in": ""},
            "confidence": h.get("confidence", 1.0),
            "validation_status": h.get("validation_status", "AUTO"),
            "extras": {
                "groups": h.get("groups", []),
                "primary_spec_section": h.get("primary_spec_section", ""),
                "figures": h.get("figures", []),
                "tables": h.get("tables", []),
                "spec_sections": h.get("spec_sections", []),
                "uses_features": h.get("uses_features", [])
            }
        }
        hd_nodes.append(node)
    
    return feat_nodes, hd_nodes, relations


# =============================================================================
# CROSS-REFERENCE BUILDER
# =============================================================================

def _build_cross_references(all_nodes: List[dict], node_ids: set) -> List[dict]:
    """Build REFERENCES relations by scanning text content for table/figure mentions."""
    relations = []
    rel_counter = 0
    
    for node in all_nodes:
        if node["type"] != "SPEC_CHUNK":
            continue
        
        text = node.get("extras", {}).get("full_text", "")
        if not text:
            continue
        
        # Find table references
        table_refs = find_table_references(text)
        for ref in table_refs:
            if ref in node_ids:
                rel_counter += 1
                relations.append({
                    "id": f"REL_REF_{rel_counter:04d}",
                    "type": "REFERENCES",
                    "source_node": node["id"],
                    "target_node": ref,
                    "description": f"Chunk references {ref}"
                })
        
        # Find figure references
        fig_refs = find_figure_references(text)
        for ref in fig_refs:
            if ref in node_ids:
                rel_counter += 1
                relations.append({
                    "id": f"REL_REF_{rel_counter:04d}",
                    "type": "REFERENCES",
                    "source_node": node["id"],
                    "target_node": ref,
                    "description": f"Chunk references {ref}"
                })
    
    return relations


# =============================================================================
# VALIDATION
# =============================================================================

def _validate(metadata: dict) -> List[str]:
    """Validate metadata.json structure and consistency."""
    issues = []
    
    nodes = metadata.get("nodes", [])
    relations = metadata.get("relations", [])
    node_ids = {n["id"] for n in nodes}
    
    # Check for duplicate node IDs
    seen_ids = set()
    for n in nodes:
        if n["id"] in seen_ids:
            issues.append(f"Duplicate node ID: {n['id']}")
        seen_ids.add(n["id"])
    
    # Check dangling relations
    for r in relations:
        if r["source_node"] not in node_ids:
            issues.append(f"Dangling source: {r['source_node']} in relation {r['id']}")
        if r["target_node"] not in node_ids:
            issues.append(f"Dangling target: {r['target_node']} in relation {r['id']}")
    
    # Check required fields
    for n in nodes:
        if not n.get("id"):
            issues.append(f"Node missing ID: {n}")
        if not n.get("type"):
            issues.append(f"Node missing type: {n['id']}")
        if not n.get("name"):
            issues.append(f"Node missing name: {n['id']}")
    
    if issues:
        print(f"\n  VALIDATION: {len(issues)} issues found:")
        for issue in issues[:20]:
            print(f"    - {issue}")
        if len(issues) > 20:
            print(f"    ... and {len(issues) - 20} more")
    else:
        print(f"  VALIDATION: OK (no issues)")
    
    return issues
