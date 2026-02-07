#!/usr/bin/env python3
"""
Merge all extracted resources into unified metadata.json graph.

This script combines:
- tables/tables_page_map.json (60 tables)
- figures/figures_page_map.json (83 figures)
- spec/sections.json (112 sections, 287 chunks)

Into a unified graph structure with nodes and relations.

Usage:
    python merge_metadata.py [--dry-run] [--validate-only]
"""

import json
import re
import os
import sys
import argparse
import time
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any

# =============================================================================
# CONFIGURATION
# =============================================================================

WORKSPACE_ROOT = Path(__file__).parent.parent
TABLES_MAP_PATH = WORKSPACE_ROOT / "tables" / "tables_page_map.json"
FIGURES_MAP_PATH = WORKSPACE_ROOT / "figures" / "figures_page_map.json"
SECTIONS_PATH = WORKSPACE_ROOT / "spec" / "sections.json"
REGISTERS_PATH = WORKSPACE_ROOT / "registers" / "registers.json"
OUTPUT_PATH = WORKSPACE_ROOT / "metadata" / "metadata.json"

PAGE_OFFSET = 11


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class SourceInfo:
    """Source location in PDF."""
    page: int = 0
    page_end: int = 0
    pdf_page: int = 0
    pdf_page_end: int = 0


@dataclass
class CoverageInfo:
    """Implementation coverage tracking."""
    status: str = "NOT_IMPLEMENTED"  # NOT_IMPLEMENTED | PARTIAL | IMPLEMENTED | NOT_APPLICABLE
    notes: str = ""
    implemented_in: str = ""


@dataclass
class Node:
    """Base node in the metadata graph."""
    id: str
    type: str  # TABLE | FIGURE | SPEC_CHUNK | REGISTER | FEATURE | STATE_MACHINE
    name: str
    description: str = ""
    index_keywords: List[str] = field(default_factory=list)
    source: Dict = field(default_factory=dict)
    coverage: Dict = field(default_factory=lambda: {
        "status": "NOT_IMPLEMENTED",
        "notes": "",
        "implemented_in": ""
    })
    confidence: float = 1.0
    validation_status: str = "AUTO"  # AUTO | USER_VALIDATED | NEEDS_REVIEW
    # Type-specific fields stored as extras
    extras: Dict = field(default_factory=dict)


@dataclass
class Relation:
    """Relation between nodes."""
    id: str
    type: str  # REFERENCES | CONTAINS | DESCRIBES | VISUALIZED_BY | DEFINED_BY | SEQUENCE_NEXT | CHILD_OF
    source_node: str
    target_node: str
    description: str = ""
    bidirectional: bool = False


# =============================================================================
# UTILITIES
# =============================================================================

def load_json(path: Path) -> dict:
    """Load JSON file."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(data: dict, path: Path):
    """Save JSON file with pretty printing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Saved: {path}")


def extract_keywords(text: str) -> List[str]:
    """Extract keywords from text."""
    # Remove common words
    stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
                  'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
                  'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'to', 'of',
                  'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into', 'through',
                  'during', 'before', 'after', 'above', 'below', 'between', 'under',
                  'and', 'or', 'but', 'if', 'then', 'else', 'when', 'where', 'why', 'how',
                  'this', 'that', 'these', 'those', 'it', 'its', 'they', 'them', 'their',
                  'which', 'who', 'whom', 'what', 'each', 'all', 'both', 'any', 'some'}
    
    # Extract words
    words = re.findall(r'\b[a-zA-Z][a-zA-Z0-9_]{2,}\b', text.lower())
    
    # Filter and dedupe
    keywords = []
    seen = set()
    for w in words:
        if w not in stop_words and w not in seen:
            seen.add(w)
            keywords.append(w)
    
    return keywords[:20]  # Limit to 20 keywords


def extract_technical_terms(text: str) -> List[str]:
    """Extract technical terms (acronyms, hex values, register names)."""
    terms = []
    
    # Acronyms (2+ uppercase letters)
    acronyms = re.findall(r'\b[A-Z]{2,}[0-9]*\b', text)
    terms.extend(acronyms)
    
    # Hex offsets (e.g., "029h", "0x29")
    hex_vals = re.findall(r'\b(?:0x)?[0-9A-Fa-f]+h?\b', text)
    terms.extend([h for h in hex_vals if len(h) >= 2])
    
    # Bit ranges (e.g., "D07-D04", "bits 31:24")
    bit_ranges = re.findall(r'\b(?:D\d+-D\d+|bits?\s*\d+(?::\d+)?)\b', text, re.IGNORECASE)
    terms.extend(bit_ranges)
    
    # Dedupe
    return list(set(terms))[:15]


def find_table_references(text: str) -> List[str]:
    """Find Table X-Y references in text."""
    matches = re.findall(r'Table\s+(\d+)-(\d+)', text, re.IGNORECASE)
    return [f"TABLE_{m[0]}_{m[1]}" for m in matches]


def find_figure_references(text: str) -> List[str]:
    """Find Figure X-Y references in text."""
    matches = re.findall(r'Figure\s+(\d+)-(\d+)', text, re.IGNORECASE)
    return [f"FIG_{m[0]}_{m[1]}" for m in matches]


def find_section_references(text: str) -> List[str]:
    """Find Section X.Y.Z references in text."""
    matches = re.findall(r'Section\s+(\d+(?:\.\d+)*)', text, re.IGNORECASE)
    return [f"SEC_{m.replace('.', '_')}" for m in matches]


def parse_register_from_title(title: str) -> Optional[dict]:
    """Parse register info from section title like 'Power Control Register (Offset 029h)'."""
    match = re.search(r'(.+?)\s+Register\s*\(Offset\s*([0-9A-Fa-f]+)h?\)', title, re.IGNORECASE)
    if match:
        return {
            "name": match.group(1).strip(),
            "offset": match.group(2).upper()
        }
    return None


# =============================================================================
# NODE GENERATORS
# =============================================================================

def create_table_nodes(tables_data: dict) -> List[Node]:
    """Create TABLE nodes from tables_page_map.json."""
    nodes = []
    
    for table in tables_data.get("tables", []):
        node = Node(
            id=table["id"],
            type="TABLE",
            name=table.get("title", table["spec_reference"]),
            description=table.get("abstract", ""),
            index_keywords=extract_keywords(table.get("title", "") + " " + table.get("abstract", "")),
            source={
                "page": table.get("spec_page", 0),
                "pdf_page": table.get("definition_page", 0),
                "spec_reference": table.get("spec_reference", "")
            },
            confidence=0.95 if table.get("conversion", {}).get("status") == "COMPLETED" else 0.7,
            validation_status="AUTO",
            extras={
                "table_number": table.get("spec_reference", ""),
                "csv_file": f"tables/csv/{table['id']}.csv" if table.get("conversion", {}).get("status") == "COMPLETED" else "",
                "columns": table.get("columns", []),
                "table_type": classify_table_type(table)
            }
        )
        nodes.append(node)
    
    return nodes


def classify_table_type(table: dict) -> str:
    """Classify table type based on title/content."""
    title = table.get("title", "").lower()
    
    if "register" in title and ("field" in title or "bit" in title):
        return "REGISTER_FIELDS"
    elif "register" in title:
        return "REGISTER_MAP"
    elif "signal" in title or "port" in title:
        return "SIGNAL_LIST"
    elif "timing" in title:
        return "TIMING"
    else:
        return "OTHER"


def create_figure_nodes(figures_data: dict) -> List[Node]:
    """Create FIGURE nodes from figures_page_map.json."""
    nodes = []
    
    for figure in figures_data.get("figures", []):
        # Determine figure type
        fig_type = classify_figure_type(figure)
        
        # Check for plantuml file
        plantuml_path = WORKSPACE_ROOT / "figures" / "plantuml" / f"{figure['id']}.puml"
        has_plantuml = plantuml_path.exists()
        
        node = Node(
            id=figure["id"],
            type="FIGURE",
            name=figure.get("title", figure["spec_reference"]),
            description=figure.get("abstract", ""),
            index_keywords=extract_keywords(figure.get("title", "") + " " + figure.get("abstract", "")),
            source={
                "page": figure.get("spec_page", 0),
                "pdf_page": figure.get("definition_page", 0),
                "spec_reference": figure.get("spec_reference", "")
            },
            confidence=0.9 if has_plantuml else 0.7,
            validation_status="AUTO",
            extras={
                "figure_number": figure.get("spec_reference", ""),
                "figure_type": fig_type,
                "text_diagram_file": f"figures/plantuml/{figure['id']}.puml" if has_plantuml else "",
                "text_diagram_format": "PLANTUML" if has_plantuml else "NONE",
                "image_file": f"figures/images/{figure['id']}.png"
            }
        )
        nodes.append(node)
    
    return nodes


def classify_figure_type(figure: dict) -> str:
    """Classify figure type based on title."""
    title = figure.get("title", "").lower()
    abstract = figure.get("abstract", "").lower()
    combined = title + " " + abstract
    
    if "state" in combined or "machine" in combined or "transition" in combined:
        return "STATE_DIAGRAM"
    elif "timing" in combined or "waveform" in combined:
        return "TIMING_DIAGRAM"
    elif "register" in combined and ("bit" in combined or "field" in combined or "layout" in combined):
        return "REGISTER_LAYOUT"
    elif "flow" in combined or "sequence" in combined:
        return "FLOWCHART"
    elif "block" in combined or "architecture" in combined or "diagram" in combined:
        return "BLOCK_DIAGRAM"
    else:
        return "OTHER"


def create_spec_chunk_nodes(sections_data: dict) -> List[Node]:
    """Create SPEC_CHUNK nodes from sections.json."""
    nodes = []
    
    for sec_num, section in sections_data.get("sections", {}).items():
        for chunk in section.get("chunks", []):
            node = Node(
                id=chunk["chunk_id"],
                type="SPEC_CHUNK",
                name=f"{section['title']} (Chunk {chunk['chunk_index']})",
                description=chunk.get("abstract", ""),
                index_keywords=section.get("index", {}).get("keywords", []),
                source={
                    "page": chunk.get("spec_page", section["source"]["spec_page_start"]),
                    "pdf_page": chunk.get("spec_page", section["source"]["spec_page_start"]) + PAGE_OFFSET,
                    "section_number": sec_num
                },
                confidence=section.get("extraction", {}).get("confidence", 0.9),
                validation_status="AUTO",
                extras={
                    "section_id": section["id"],
                    "section_number": sec_num,
                    "section_title": section["title"],
                    "chunk_index": chunk["chunk_index"],
                    "word_count": chunk.get("word_count", 0),
                    "full_text": chunk.get("raw", ""),
                    "technical_terms": section.get("index", {}).get("technical_terms", [])
                }
            )
            nodes.append(node)
    
    return nodes


def create_register_nodes(sections_data: dict, tables_data: dict, registers_data: dict = None) -> List[Node]:
    """Create REGISTER nodes from registers.json (or fall back to section parsing)."""
    nodes = []
    
    # If we have detailed register data from extraction, use it
    if registers_data and registers_data.get("registers"):
        for reg in registers_data["registers"]:
            node = Node(
                id=reg["id"],
                type="REGISTER",
                name=reg["name"],
                description=f"Register at offset {reg['offset']}",
                index_keywords=extract_keywords(reg["name"]) + [f"offset {reg['offset']}", f"0x{reg['offset'].rstrip('h')}"],
                source={
                    "page": reg.get("source", {}).get("page", 0),
                    "pdf_page": reg.get("source", {}).get("definition_page", 0),
                    "section_number": reg.get("spec_section", "")
                },
                confidence=0.95,  # High confidence - LLM extracted
                validation_status="AUTO",
                extras={
                    "offset": f"0x{reg['offset'].rstrip('h')}",
                    "offset_hex": reg["offset"],
                    "size_bits": sum(f.get("width", 0) for f in reg.get("fields", [])),
                    "reset_value": "",
                    "access": "",
                    "spec_section": reg.get("spec_section", ""),
                    "spec_table": reg.get("spec_table", ""),
                    "spec_figure": "",
                    "class_id": reg.get("class_id", ""),
                    "fields": reg.get("fields", [])
                }
            )
            nodes.append(node)
        return nodes
    
    # Fallback: parse from section titles (legacy behavior)
    for sec_num, section in sections_data.get("sections", {}).items():
        # Look for register sections (typically 2.2.X)
        reg_info = parse_register_from_title(section["title"])
        if reg_info:
            offset = reg_info["offset"]
            reg_id = f"REG_{offset}"
            
            # Find associated table and figure
            table_refs = section.get("references", {}).get("tables", [])
            figure_refs = section.get("references", {}).get("figures", [])
            
            node = Node(
                id=reg_id,
                type="REGISTER",
                name=reg_info["name"] + " Register",
                description=section.get("abstract", ""),
                index_keywords=extract_keywords(section["title"]) + [f"offset {offset}h", f"0x{offset}"],
                source={
                    "page": section["source"]["spec_page_start"],
                    "pdf_page": section["source"]["pdf_page_start"],
                    "section_number": sec_num
                },
                confidence=0.85,
                validation_status="AUTO",
                extras={
                    "offset": f"0x{offset}",
                    "offset_hex": offset,
                    "size_bits": 8,  # Default, would need to parse table for actual
                    "reset_value": "",
                    "access": "",
                    "spec_section": sec_num,
                    "spec_table": table_refs[0] if table_refs else "",
                    "spec_figure": figure_refs[0] if figure_refs else "",
                    "fields": []  # Would be populated from table CSV
                }
            )
            nodes.append(node)
    
    return nodes


def create_reg_class_nodes(registers_data: dict) -> List[Node]:
    """Create REG_CLASS nodes from registers.json."""
    nodes = []
    
    if not registers_data or not registers_data.get("reg_classes"):
        return nodes
    
    for reg_class in registers_data["reg_classes"]:
        addr_range = reg_class.get("address_range", {})
        version_support = reg_class.get("version_support", {})
        
        node = Node(
            id=reg_class["id"],
            type="REG_CLASS",
            name=reg_class["name"],
            description=f"Register class covering addresses {addr_range.get('start', '')} to {addr_range.get('end', '')}",
            index_keywords=extract_keywords(reg_class["name"]) + [
                addr_range.get("start", ""),
                addr_range.get("end", "")
            ],
            source={
                "table": reg_class.get("source", {}).get("table", "TABLE_1_1"),
                "figure": reg_class.get("source", {}).get("figure", "FIG_1_2")
            },
            confidence=0.95,
            validation_status="AUTO",
            extras={
                "address_range": addr_range,
                "version_support": version_support
            }
        )
        nodes.append(node)
    
    return nodes


# =============================================================================
# RELATION GENERATORS
# =============================================================================

def create_reference_relations(chunks: List[Node], tables: List[Node], figures: List[Node]) -> List[Relation]:
    """Create REFERENCES relations from chunks to tables/figures mentioned in text."""
    relations = []
    rel_id = 0
    
    table_ids = {n.id for n in tables}
    figure_ids = {n.id for n in figures}
    
    for chunk in chunks:
        text = chunk.extras.get("full_text", "") + " " + chunk.description
        
        # Find table references
        for table_id in find_table_references(text):
            if table_id in table_ids:
                rel_id += 1
                relations.append(Relation(
                    id=f"REL_{rel_id:04d}",
                    type="REFERENCES",
                    source_node=chunk.id,
                    target_node=table_id,
                    description="Chunk references table"
                ))
        
        # Find figure references
        for fig_id in find_figure_references(text):
            if fig_id in figure_ids:
                rel_id += 1
                relations.append(Relation(
                    id=f"REL_{rel_id:04d}",
                    type="REFERENCES",
                    source_node=chunk.id,
                    target_node=fig_id,
                    description="Chunk references figure"
                ))
    
    return relations


def create_hierarchy_relations(sections_data: dict, chunks: List[Node]) -> List[Relation]:
    """Create CHILD_OF relations from section hierarchy."""
    relations = []
    rel_id = 1000  # Start at different range
    
    # Build mapping of section_number to chunk IDs
    section_to_chunks = {}
    for chunk in chunks:
        sec_num = chunk.extras.get("section_number", "")
        if sec_num:
            if sec_num not in section_to_chunks:
                section_to_chunks[sec_num] = []
            section_to_chunks[sec_num].append(chunk.id)
    
    for sec_num, section in sections_data.get("sections", {}).items():
        parent_sec_num = None
        parent_id = section.get("hierarchy", {}).get("parent")
        
        # Find parent section number from parent ID (SEC_1_2 -> "1.2")
        if parent_id:
            parent_sec_num = parent_id.replace("SEC_", "").replace("_", ".")
        
        if parent_sec_num and parent_sec_num in section_to_chunks:
            # Link each chunk in this section to the first chunk of parent section
            parent_chunks = section_to_chunks.get(parent_sec_num, [])
            if parent_chunks:
                for chunk in section.get("chunks", []):
                    rel_id += 1
                    relations.append(Relation(
                        id=f"REL_{rel_id:04d}",
                        type="CHILD_OF",
                        source_node=chunk["chunk_id"],
                        target_node=parent_chunks[0],  # Link to first chunk of parent
                        description=f"Chunk in section {sec_num} under parent {parent_sec_num}"
                    ))
    
    return relations


def create_register_relations(registers: List[Node], tables: List[Node], figures: List[Node], chunks: List[Node], registers_data: dict = None) -> List[Relation]:
    """Create relations for registers (from registers.json or fallback to node extras)."""
    relations = []
    rel_id = 2000
    
    # If we have pre-computed relations from registers.json, use them
    if registers_data and registers_data.get("relations"):
        for rel in registers_data["relations"]:
            rel_id += 1
            # Map registers.json relation types to our relation types
            rel_type = rel.get("type", "REFERENCES")
            # Convert DEFINED_IN -> DEFINED_BY for consistency
            if rel_type == "DEFINED_IN":
                rel_type = "DEFINED_BY"
            
            relations.append(Relation(
                id=f"REL_{rel_id:04d}",
                type=rel_type,
                source_node=rel["source"],
                target_node=rel["target"],
                description=f"Register relation: {rel_type}"
            ))
        
        # Also add DESCRIBES relations from chunks to registers
        register_ids = {r.id for r in registers}
        for chunk in chunks:
            sec_num = chunk.extras.get("section_number", "")
            if sec_num:
                for reg in registers:
                    if reg.extras.get("spec_section") == sec_num:
                        rel_id += 1
                        relations.append(Relation(
                            id=f"REL_{rel_id:04d}",
                            type="DESCRIBES",
                            source_node=chunk.id,
                            target_node=reg.id,
                            description="Chunk describes register"
                        ))
        
        return relations
    
    # Fallback: generate relations from node extras
    for reg in registers:
        # Link to table
        table_id = reg.extras.get("spec_table", "")
        if table_id:
            rel_id += 1
            relations.append(Relation(
                id=f"REL_{rel_id:04d}",
                type="DEFINED_BY",
                source_node=reg.id,
                target_node=table_id,
                description="Register fields defined in table"
            ))
        
        # Link to figure
        figure_id = reg.extras.get("spec_figure", "")
        if figure_id:
            rel_id += 1
            relations.append(Relation(
                id=f"REL_{rel_id:04d}",
                type="VISUALIZED_BY",
                source_node=reg.id,
                target_node=figure_id,
                description="Register layout shown in figure"
            ))
        
        # Link to section chunks
        sec_num = reg.extras.get("spec_section", "")
        if sec_num:
            for chunk in chunks:
                if chunk.extras.get("section_number") == sec_num:
                    rel_id += 1
                    relations.append(Relation(
                        id=f"REL_{rel_id:04d}",
                        type="DESCRIBES",
                        source_node=chunk.id,
                        target_node=reg.id,
                        description="Chunk describes register"
                    ))
    
    return relations


# =============================================================================
# MAIN MERGE LOGIC
# =============================================================================

def build_metadata(tables_data: dict, figures_data: dict, sections_data: dict, registers_data: dict = None) -> dict:
    """Build the complete metadata structure."""
    
    print("\n" + "=" * 60)
    print("Building Metadata Graph")
    print("=" * 60)
    
    # Phase 1: Create base nodes
    print("\nPhase 1: Creating base nodes...")
    
    table_nodes = create_table_nodes(tables_data)
    print(f"  TABLE nodes: {len(table_nodes)}")
    
    figure_nodes = create_figure_nodes(figures_data)
    print(f"  FIGURE nodes: {len(figure_nodes)}")
    
    chunk_nodes = create_spec_chunk_nodes(sections_data)
    print(f"  SPEC_CHUNK nodes: {len(chunk_nodes)}")
    
    # Phase 2: Create derived nodes
    print("\nPhase 2: Creating derived nodes...")
    
    # Use registers.json if available, otherwise fall back to section parsing
    register_nodes = create_register_nodes(sections_data, tables_data, registers_data)
    print(f"  REGISTER nodes: {len(register_nodes)}")
    
    # Create REG_CLASS nodes from registers.json
    reg_class_nodes = create_reg_class_nodes(registers_data) if registers_data else []
    print(f"  REG_CLASS nodes: {len(reg_class_nodes)}")
    
    # Count total fields in registers
    total_fields = sum(len(r.extras.get("fields", [])) for r in register_nodes)
    print(f"  (Total register fields: {total_fields})")
    
    # Combine all nodes
    all_nodes = table_nodes + figure_nodes + chunk_nodes + register_nodes + reg_class_nodes
    print(f"\n  Total nodes: {len(all_nodes)}")
    
    # Phase 3: Create relations
    print("\nPhase 3: Creating relations...")
    
    ref_relations = create_reference_relations(chunk_nodes, table_nodes, figure_nodes)
    print(f"  REFERENCES relations: {len(ref_relations)}")
    
    hierarchy_relations = create_hierarchy_relations(sections_data, chunk_nodes)
    print(f"  CHILD_OF relations: {len(hierarchy_relations)}")
    
    register_relations = create_register_relations(register_nodes, table_nodes, figure_nodes, chunk_nodes, registers_data)
    print(f"  REGISTER relations: {len(register_relations)}")
    
    # Combine all relations
    all_relations = ref_relations + hierarchy_relations + register_relations
    print(f"\n  Total relations: {len(all_relations)}")
    
    # Build statistics
    node_counts = {}
    for node in all_nodes:
        node_counts[node.type] = node_counts.get(node.type, 0) + 1
    
    # Build sources dict
    sources = {
        "tables": str(TABLES_MAP_PATH),
        "figures": str(FIGURES_MAP_PATH),
        "sections": str(SECTIONS_PATH)
    }
    if registers_data:
        sources["registers"] = str(REGISTERS_PATH)
    
    # Build output structure
    metadata = {
        "metadata_version": "1.1.0",  # Bumped for register field support
        "spec_info": {
            "name": "SD Host Controller Simplified Specification",
            "version": "3.00",
            "date": "February 2011",
            "source_file": "sd_host_3_00.pdf",
            "total_pages": 157
        },
        "extraction_info": {
            "extracted_date": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "extractor_version": "1.1.0",
            "sources": sources,
            "validation_status": "DRAFT",
            "statistics": {
                "total_nodes": len(all_nodes),
                "by_type": node_counts,
                "total_relations": len(all_relations),
                "register_fields": total_fields
            }
        },
        "nodes": [asdict(n) for n in all_nodes],
        "relations": [asdict(r) for r in all_relations]
    }
    
    return metadata


def validate_metadata(metadata: dict) -> dict:
    """Validate the metadata structure."""
    print("\n" + "=" * 60)
    print("Validating Metadata")
    print("=" * 60)
    
    issues = []
    warnings = []
    
    # Check for orphan nodes (nodes not in any relation)
    node_ids = {n["id"] for n in metadata["nodes"]}
    nodes_in_relations = set()
    for rel in metadata["relations"]:
        nodes_in_relations.add(rel["source_node"])
        nodes_in_relations.add(rel["target_node"])
    
    orphans = node_ids - nodes_in_relations
    if orphans:
        warnings.append(f"Found {len(orphans)} orphan nodes (no relations)")
    
    # Check for dangling relations (reference non-existent nodes)
    for rel in metadata["relations"]:
        if rel["source_node"] not in node_ids:
            issues.append(f"Relation {rel['id']} references non-existent source: {rel['source_node']}")
        if rel["target_node"] not in node_ids:
            issues.append(f"Relation {rel['id']} references non-existent target: {rel['target_node']}")
    
    # Check node completeness
    for node in metadata["nodes"]:
        if not node.get("name"):
            issues.append(f"Node {node['id']} missing name")
        if not node.get("index_keywords"):
            warnings.append(f"Node {node['id']} has no keywords")
    
    print(f"\n  Issues: {len(issues)}")
    print(f"  Warnings: {len(warnings)}")
    
    if issues:
        print("\n  Critical Issues:")
        for issue in issues[:10]:
            print(f"    - {issue}")
    
    if warnings:
        print("\n  Warnings:")
        for warn in warnings[:10]:
            print(f"    - {warn}")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings
    }


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Merge extracted resources into metadata.json")
    parser.add_argument("--dry-run", action="store_true", help="Don't write output, just show stats")
    parser.add_argument("--validate-only", action="store_true", help="Only validate existing metadata.json")
    parser.add_argument("--no-registers", action="store_true", help="Skip loading registers.json (use section-based fallback)")
    args = parser.parse_args()
    
    print("=" * 60)
    print("SD Host 3.0 Metadata Merge")
    print("=" * 60)
    
    # Check input files exist
    print("\nChecking input files...")
    required_files = [
        (TABLES_MAP_PATH, "Tables map"),
        (FIGURES_MAP_PATH, "Figures map"),
        (SECTIONS_PATH, "Sections")
    ]
    
    for path, name in required_files:
        if path.exists():
            print(f"  ✓ {name}: {path}")
        else:
            print(f"  ✗ {name}: {path} NOT FOUND")
            sys.exit(1)
    
    # Check optional registers file
    has_registers = REGISTERS_PATH.exists() and not args.no_registers
    if has_registers:
        print(f"  ✓ Registers: {REGISTERS_PATH}")
    else:
        print(f"  ⚠ Registers: {'skipped (--no-registers)' if args.no_registers else 'NOT FOUND (using section-based fallback)'}")
    
    if args.validate_only:
        if OUTPUT_PATH.exists():
            print(f"\nValidating existing: {OUTPUT_PATH}")
            metadata = load_json(OUTPUT_PATH)
            result = validate_metadata(metadata)
            sys.exit(0 if result["valid"] else 1)
        else:
            print(f"\nNo metadata.json found at {OUTPUT_PATH}")
            sys.exit(1)
    
    # Load sources
    print("\nLoading sources...")
    tables_data = load_json(TABLES_MAP_PATH)
    print(f"  Tables: {len(tables_data.get('tables', []))}")
    
    figures_data = load_json(FIGURES_MAP_PATH)
    print(f"  Figures: {len(figures_data.get('figures', []))}")
    
    sections_data = load_json(SECTIONS_PATH)
    print(f"  Sections: {len(sections_data.get('sections', {}))}")
    
    registers_data = None
    if has_registers:
        registers_data = load_json(REGISTERS_PATH)
        print(f"  Registers: {len(registers_data.get('registers', []))} registers, {registers_data.get('_metadata', {}).get('total_fields', 0)} fields")
    
    # Build metadata
    metadata = build_metadata(tables_data, figures_data, sections_data, registers_data)
    
    # Validate
    result = validate_metadata(metadata)
    
    # Save
    if not args.dry_run:
        save_json(metadata, OUTPUT_PATH)
        print(f"\n✓ Metadata saved to: {OUTPUT_PATH}")
    else:
        print("\n[DRY RUN] Would save to:", OUTPUT_PATH)
    
    print("\nDone!")


if __name__ == "__main__":
    main()
