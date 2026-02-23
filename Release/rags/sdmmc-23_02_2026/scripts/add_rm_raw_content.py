#!/usr/bin/env python3
"""
Post-processing: Add rm_raw_content chunks to metadata.json.

Adds a top-level "rm_raw_content" key to the merged metadata,
giving agents lightweight context about the broader SPC58 H-Line SoC.
"""

import json
from pathlib import Path


def add_rm_raw_content():
    base = Path(__file__).parent.parent
    metadata_path = base / "metadata" / "metadata.json"
    raw_path = base / "intermediates" / "rm_raw_content.json"
    
    if not metadata_path.exists():
        print(f"ERROR: {metadata_path} not found. Run merge first.")
        return
    if not raw_path.exists():
        print(f"ERROR: {raw_path} not found. Run build_rm_raw_content.py first.")
        return
    
    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    
    with open(raw_path, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
    
    # Add as top-level key
    metadata["rm_raw_content"] = {
        "description": "Raw text chunks from the full RM0452 reference manual (3897 pages). "
                       "Per-chapter extracts provide lightweight SoC context without full LLM processing. "
                       "SDMMC chapter (Section 57) is the detailed RAG target; other chapters are reference-only.",
        "source_pdf": raw_data["source"],
        "total_chapters": raw_data["total_chapters"],
        "total_chunks": raw_data["total_chunks"],
        "chunks": raw_data["chunks"]
    }
    
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    total_words = sum(c["word_count"] for c in raw_data["chunks"])
    print(f"Added {raw_data['total_chunks']} rm_raw_content chunks to metadata.json")
    print(f"  Total words: {total_words:,}")
    print(f"  Metadata size: {metadata_path.stat().st_size:,} bytes")


if __name__ == "__main__":
    add_rm_raw_content()
