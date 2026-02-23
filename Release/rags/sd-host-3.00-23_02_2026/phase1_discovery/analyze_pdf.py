#!/usr/bin/env python3
"""
Phase 1a: Analyze PDF structure.

Extracts basic metadata about the PDF: page count, detected TOC regions,
page offset validation, etc. No LLM calls — purely deterministic.
"""

import re
from pathlib import Path
from typing import Dict, Any

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.pdf_utils import open_pdf, get_page_count, get_page_text
from shared.config import get_page_offset


def analyze_pdf_structure(config: dict, pdf_path: Path) -> dict:
    """Analyze PDF structure and return structural metadata.
    
    Returns:
        {
            "pdf_file": str,
            "total_pages": int,
            "page_offset": int,
            "total_spec_pages": int,
            "detected_toc_sections": [...],
            "has_table_of_tables": bool,
            "has_table_of_figures": bool,
            "sample_spec_pages": {...}
        }
    """
    doc = open_pdf(pdf_path)
    page_offset = get_page_offset(config)
    total_pages = get_page_count(doc)
    
    result = {
        "pdf_file": str(pdf_path.name),
        "total_pages": total_pages,
        "page_offset": page_offset,
        "total_spec_pages": total_pages - page_offset,
        "detected_features": {}
    }
    
    # Check for Table of Tables
    toc_tables_pages = config["toc"]["tables"]["pages"]
    table_pattern = config["toc"]["tables"]["pattern"]
    table_count = 0
    for page_idx in toc_tables_pages:
        if page_idx < total_pages:
            text = get_page_text(doc, page_idx)
            table_count += len(re.findall(table_pattern, text, re.IGNORECASE))
    result["detected_features"]["tables"] = {
        "found": table_count > 0,
        "count": table_count,
        "toc_pages": toc_tables_pages
    }
    
    # Check for Table of Figures
    toc_figures_pages = config["toc"]["figures"]["pages"]
    figure_pattern = config["toc"]["figures"]["pattern"]
    figure_count = 0
    for page_idx in toc_figures_pages:
        if page_idx < total_pages:
            text = get_page_text(doc, page_idx)
            figure_count += len(re.findall(figure_pattern, text, re.IGNORECASE))
    result["detected_features"]["figures"] = {
        "found": figure_count > 0,
        "count": figure_count,
        "toc_pages": toc_figures_pages
    }
    
    # Check for section TOC
    toc_sections_pages = config["toc"]["sections"]["pages"]
    section_pattern = config["toc"]["sections"]["pattern"]
    section_count = 0
    for page_idx in toc_sections_pages:
        if page_idx < total_pages:
            text = get_page_text(doc, page_idx)
            section_count += len(re.findall(section_pattern, text, re.MULTILINE))
    result["detected_features"]["sections"] = {
        "found": section_count > 0,
        "count": section_count,
        "toc_pages": toc_sections_pages
    }
    
    # Validate page offset — check first spec page has expected content
    first_spec_page_idx = page_offset  # 0-indexed
    if first_spec_page_idx < total_pages:
        first_text = get_page_text(doc, first_spec_page_idx)
        # Check if it looks like a chapter/section start
        has_chapter = bool(re.search(r'Chapter\s+\d+|Section\s+\d+|^\d+\.\s+', first_text, re.MULTILINE))
        result["page_offset_validation"] = {
            "first_spec_page_text_preview": first_text[:200],
            "looks_like_content_start": has_chapter
        }
    
    doc.close()
    
    print(f"  PDF: {pdf_path.name}")
    print(f"  Total pages: {total_pages}")
    print(f"  Spec pages: {result['total_spec_pages']} (offset={page_offset})")
    print(f"  Tables in TOC: {table_count}")
    print(f"  Figures in TOC: {figure_count}")
    print(f"  Sections in TOC: {section_count}")
    
    return result
