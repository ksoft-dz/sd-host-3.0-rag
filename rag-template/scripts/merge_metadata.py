#!/usr/bin/env python3
"""
Generic Metadata Merge Script

Combines extracted resources into a unified metadata.json graph:
- tables/tables_page_map.json
- figures/figures_page_map.json  
- spec/sections.json

Output: metadata/metadata.json

Usage:
    python merge_metadata.py [--dry-run] [--validate-only]
"""

import json
import re
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

# =============================================================================
# CONFIGURATION
# =============================================================================

WORKSPACE_ROOT = Path(__file__).parent.parent
CONFIG_PATH = WORKSPACE_ROOT / "config.json"

# Load config
if CONFIG_PATH.exists():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        CONFIG = json.load(f)
else:
    CONFIG = {"paths": {}, "source": {}}

# Paths from config or defaults
TABLES_PATH = WORKSPACE_ROOT / CONFIG.get("paths", {}).get("tables_map", "tables/tables_page_map.json")
FIGURES_PATH = WORKSPACE_ROOT / CONFIG.get("paths", {}).get("figures_map", "figures/figures_page_map.json")
SECTIONS_PATH = WORKSPACE_ROOT / CONFIG.get("paths", {}).get("sections", "spec/sections.json")
OUTPUT_PATH = WORKSPACE_ROOT / CONFIG.get("paths", {}).get("metadata_output", "metadata/metadata.json")

PAGE_OFFSET = CONFIG.get("source", {}).get("page_offset", 0)


# =============================================================================
# UTILITIES
# =============================================================================

def load_json(path: Path) -> Optional[dict]:
    """Load JSON file if it exists."""
    if not path.exists():
        print(f"  [SKIP] {path} not found")
        return None
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
    stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                  'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
                  'could', 'should', 'may', 'might', 'must', 'can', 'to', 'of',
                  'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into',
                  'and', 'or', 'but', 'if', 'then', 'else', 'when', 'where',
                  'this', 'that', 'these', 'those', 'it', 'its', 'they', 'them'}
    
    words = re.findall(r'\b[a-zA-Z][a-zA-Z0-9_]{2,}\b', text.lower())
    keywords = []
    seen = set()
    for w in words:
        if w not in stop_words and w not in seen:
            seen.add(w)
            keywords.append(w)
    return keywords[:20]


def find_table_references(text: str) -> List[str]:
    """Find Table X-Y references in text."""
    matches = re.findall(r'Table\s+(\d+)-(\d+)', text, re.IGNORECASE)
    return [f"TABLE_{m[0]}_{m[1]}" for m in matches]


def find_figure_references(text: str) -> List[str]:
    """Find Figure X-Y references in text."""
    matches = re.findall(r'Figure\s+(\d+)-(\d+)', text, re.IGNORECASE)
    return [f"FIG_{m[0]}_{m[1]}" for m in matches]


# =============================================================================
# NODE CREATORS
# =============================================================================

def create_table_nodes(tables_data: dict) -> List[dict]:
    """Create TABLE nodes from tables_page_map.json."""
    nodes = []
    for table in tables_data.get("tables", []):
        if table.get("_comment"):
            continue
        
        node = {
            "id": table["id"],
            "type": "TABLE",
            "name": table.get("title", table.get("spec_reference", table["id"])),
            "description": table.get("abstract", ""),
            "index_keywords": extract_keywords(
                table.get("title", "") + " " + table.get("abstract", "")
            ),
            "source": {
                "page": table.get("spec_page", 0),
                "pdf_page": table.get("definition_page", 0),
                "spec_reference": table.get("spec_reference", "")
            },
            "coverage": {
                "status": "NOT_IMPLEMENTED",
                "notes": "",
                "implemented_in": ""
            },
            "confidence": 0.95 if table.get("conversion", {}).get("status") == "COMPLETED" else 0.7,
            "validation_status": "AUTO",
            "extras": {
                "csv_file": f"tables/csv/{table['id']}.csv" 
                    if table.get("conversion", {}).get("status") == "COMPLETED" else ""
            }
        }
        nodes.append(node)
    return nodes


def create_figure_nodes(figures_data: dict) -> List[dict]:
    """Create FIGURE nodes from figures_page_map.json."""
    nodes = []
    for figure in figures_data.get("figures", []):
        if figure.get("_comment"):
            continue
        
        transcription = figure.get("transcription", {})
        node = {
            "id": figure["id"],
            "type": "FIGURE",
            "name": figure.get("title", figure.get("spec_reference", figure["id"])),
            "description": figure.get("abstract", ""),
            "index_keywords": extract_keywords(
                figure.get("title", "") + " " + figure.get("abstract", "")
            ),
            "source": {
                "page": figure.get("spec_page", 0),
                "pdf_page": figure.get("definition_page", 0),
                "spec_reference": figure.get("spec_reference", "")
            },
            "coverage": {
                "status": "NOT_IMPLEMENTED",
                "notes": "",
                "implemented_in": ""
            },
            "confidence": 0.9 if transcription.get("status") == "COMPLETED" else 0.6,
            "validation_status": "AUTO",
            "extras": {
                "transcription_file": transcription.get("text_file", ""),
                "transcription_format": transcription.get("format", "")
            }
        }
        nodes.append(node)
    return nodes


def create_chunk_nodes(sections_data: dict) -> List[dict]:
    """Create SPEC_CHUNK nodes from sections.json."""
    nodes = []
    sections = sections_data.get("sections", {})
    
    for sec_num, section in sections.items():
        if section.get("_comment"):
            continue
        
        for chunk in section.get("chunks", []):
            node = {
                "id": chunk["id"],
                "type": "SPEC_CHUNK",
                "name": f"{section.get('title', 'Section')} (Chunk {chunk.get('chunk_index', 0) + 1})",
                "description": chunk.get("abstract", chunk.get("text", "")[:200]),
                "index_keywords": extract_keywords(chunk.get("text", "")),
                "source": {
                    "page": section.get("source", {}).get("spec_page_start", 0),
                    "pdf_page": section.get("source", {}).get("pdf_page_start", 0),
                    "section_number": section.get("section_number", ""),
                    "section_title": section.get("title", "")
                },
                "coverage": {
                    "status": "NOT_IMPLEMENTED",
                    "notes": "",
                    "implemented_in": ""
                },
                "confidence": 0.85,
                "validation_status": "AUTO",
                "extras": {
                    "section_id": section["id"],
                    "chunk_index": chunk.get("chunk_index", 0),
                    "word_count": chunk.get("word_count", 0),
                    "full_text": chunk.get("text", "")
                }
            }
            nodes.append(node)
    return nodes


# =============================================================================
# RELATION CREATORS
# =============================================================================

def create_relations(nodes: List[dict], sections_data: dict) -> List[dict]:
    """Create relations between nodes."""
    relations = []
    rel_id = 0
    node_ids = {n["id"] for n in nodes}
    
    # Create chunk sequence relations
    sections = sections_data.get("sections", {}) if sections_data else {}
    for sec_num, section in sections.items():
        if section.get("_comment"):
            continue
        chunks = section.get("chunks", [])
        for i in range(len(chunks) - 1):
            rel_id += 1
            relations.append({
                "id": f"REL_{rel_id:04d}",
                "type": "SEQUENCE_NEXT",
                "source_node": chunks[i]["id"],
                "target_node": chunks[i + 1]["id"],
                "description": "Next chunk in section",
                "bidirectional": False
            })
    
    # Create reference relations from chunk text
    for node in nodes:
        if node["type"] != "SPEC_CHUNK":
            continue
        
        text = node.get("extras", {}).get("full_text", "")
        
        # Find table references
        for table_id in find_table_references(text):
            if table_id in node_ids:
                rel_id += 1
                relations.append({
                    "id": f"REL_{rel_id:04d}",
                    "type": "REFERENCES",
                    "source_node": node["id"],
                    "target_node": table_id,
                    "description": f"Chunk references {table_id}",
                    "bidirectional": False
                })
        
        # Find figure references
        for fig_id in find_figure_references(text):
            if fig_id in node_ids:
                rel_id += 1
                relations.append({
                    "id": f"REL_{rel_id:04d}",
                    "type": "REFERENCES",
                    "source_node": node["id"],
                    "target_node": fig_id,
                    "description": f"Chunk references {fig_id}",
                    "bidirectional": False
                })
    
    return relations


# =============================================================================
# MAIN MERGE
# =============================================================================

def merge_all(dry_run: bool = False):
    """Merge all sources into unified metadata."""
    print("=" * 60)
    print("Merging metadata sources...")
    print("=" * 60)
    
    # Load sources
    print("\nLoading sources:")
    tables_data = load_json(TABLES_PATH)
    figures_data = load_json(FIGURES_PATH)
    sections_data = load_json(SECTIONS_PATH)
    
    # Create nodes
    print("\nCreating nodes:")
    nodes = []
    
    if tables_data:
        table_nodes = create_table_nodes(tables_data)
        nodes.extend(table_nodes)
        print(f"  TABLE nodes: {len(table_nodes)}")
    
    if figures_data:
        figure_nodes = create_figure_nodes(figures_data)
        nodes.extend(figure_nodes)
        print(f"  FIGURE nodes: {len(figure_nodes)}")
    
    if sections_data:
        chunk_nodes = create_chunk_nodes(sections_data)
        nodes.extend(chunk_nodes)
        print(f"  SPEC_CHUNK nodes: {len(chunk_nodes)}")
    
    # Create relations
    print("\nCreating relations:")
    relations = create_relations(nodes, sections_data)
    print(f"  Total relations: {len(relations)}")
    
    # Build output
    output = {
        "metadata_version": "1.0.0",
        "spec_info": {
            "name": CONFIG.get("project", {}).get("name", "Specification"),
            "version": CONFIG.get("project", {}).get("version", "1.0"),
            "source_file": CONFIG.get("source", {}).get("pdf_file", ""),
            "total_pages": CONFIG.get("source", {}).get("total_pages", 0)
        },
        "extraction_info": {
            "extracted_date": datetime.now(timezone.utc).isoformat(),
            "extractor_version": "1.0.0",
            "sources": {
                "tables": str(TABLES_PATH),
                "figures": str(FIGURES_PATH),
                "sections": str(SECTIONS_PATH)
            },
            "validation_status": "DRAFT",
            "statistics": {
                "total_nodes": len(nodes),
                "by_type": {
                    "TABLE": len([n for n in nodes if n["type"] == "TABLE"]),
                    "FIGURE": len([n for n in nodes if n["type"] == "FIGURE"]),
                    "SPEC_CHUNK": len([n for n in nodes if n["type"] == "SPEC_CHUNK"])
                },
                "total_relations": len(relations)
            }
        },
        "nodes": nodes,
        "relations": relations
    }
    
    # Output
    print(f"\nTotal nodes: {len(nodes)}")
    print(f"Total relations: {len(relations)}")
    
    if dry_run:
        print("\n[DRY RUN] Would write to:", OUTPUT_PATH)
    else:
        save_json(output, OUTPUT_PATH)
        print("\nMerge complete!")


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Merge extracted metadata into unified graph")
    parser.add_argument("--dry-run", action="store_true", help="Don't write output file")
    parser.add_argument("--validate-only", action="store_true", help="Only validate sources")
    args = parser.parse_args()
    
    if args.validate_only:
        print("Validating sources...")
        for path in [TABLES_PATH, FIGURES_PATH, SECTIONS_PATH]:
            status = "✓" if path.exists() else "✗"
            print(f"  {status} {path}")
        return
    
    merge_all(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
