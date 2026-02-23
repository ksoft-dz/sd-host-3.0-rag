#!/usr/bin/env python3
"""
Phase 1b: Extract all Tables of Contents from the PDF.

Parses TOC pages for sections, tables, and figures using config-driven patterns.
Also scans body pages for cross-references to build reference maps.
No LLM calls — purely regex + PyMuPDF.
"""

import re
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.pdf_utils import open_pdf, get_page_count, get_page_text
from shared.config import get_page_offset, get_toc_pages, get_toc_pattern


def extract_all_tocs(config: dict, pdf_path: Path) -> dict:
    """Extract sections, tables, and figures from TOC pages.
    
    Returns:
        {
            "sections": [...],
            "tables": [...],
            "figures": [...]
        }
    """
    doc = open_pdf(pdf_path)
    page_offset = get_page_offset(config)
    total_pages = get_page_count(doc)
    
    result = {}
    
    # Extract sections
    result["sections"] = _extract_section_toc(doc, config, page_offset)
    
    # Extract tables
    result["tables"] = _extract_table_toc(doc, config, page_offset, total_pages)
    
    # Extract figures  
    result["figures"] = _extract_figure_toc(doc, config, page_offset, total_pages)
    
    doc.close()
    return result


def _extract_section_toc(doc, config: dict, page_offset: int) -> List[dict]:
    """Extract section entries from section TOC pages."""
    pages = get_toc_pages(config, "sections")
    pattern_str = get_toc_pattern(config, "sections")
    pattern = re.compile(pattern_str, re.MULTILINE)
    
    sections = []
    seen = set()
    
    for page_idx in pages:
        if page_idx >= len(doc):
            continue
        text = get_page_text(doc, page_idx)
        for match in pattern.finditer(text):
            section_num = match.group(1)
            title = match.group(2).strip().rstrip('.')
            spec_page = int(match.group(3))
            
            if section_num in seen:
                continue
            seen.add(section_num)
            
            # Determine depth from section number
            depth = section_num.count('.') + 1
            
            sections.append({
                "section_number": section_num,
                "title": title,
                "spec_page": spec_page,
                "pdf_page": spec_page + page_offset,
                "depth": depth
            })
    
    print(f"  Sections extracted from TOC: {len(sections)}")
    return sections


def _extract_table_toc(doc, config: dict, page_offset: int, total_pages: int) -> List[dict]:
    """Extract table entries from Table of Tables.
    
    Supports both chapter-seq format (Table X-Y, 4 groups) and
    single-number format (Table N, 3 groups). Auto-detected from
    the number of capture groups in the regex pattern.
    """
    pages = get_toc_pages(config, "tables")
    pattern_str = get_toc_pattern(config, "tables")
    pattern = re.compile(pattern_str, re.IGNORECASE | re.DOTALL)
    
    # Detect format from number of capture groups
    num_groups = pattern.groups
    single_number = (num_groups == 3)  # (num, title, page) vs (chapter, seq, title, page)
    
    tables = []
    seen = set()
    
    for page_idx in pages:
        if page_idx >= len(doc):
            continue
        text = get_page_text(doc, page_idx)
        for match in pattern.finditer(text):
            if single_number:
                num = match.group(1)
                title = match.group(2).strip().rstrip('.')
                spec_page = int(match.group(3))
                table_id = f"TABLE_{num}"
                spec_ref = f"Table {num}"
            else:
                chapter = match.group(1)
                seq = match.group(2)
                title = match.group(3).strip().rstrip('.')
                spec_page = int(match.group(4))
                table_id = f"TABLE_{chapter}_{seq}"
                spec_ref = f"Table {chapter}-{seq}"
            
            if table_id in seen:
                continue
            seen.add(table_id)
            
            tables.append({
                "id": table_id,
                "spec_reference": spec_ref,
                "title": title,
                "spec_page": spec_page,
                "definition_page": spec_page + page_offset,
                "referenced_on_pages": [],
                "conversion": {"status": "PENDING"}
            })
    
    # Scan body pages for table references
    print(f"  Scanning body pages for table cross-references...")
    if single_number:
        ref_pattern = re.compile(r'Table\s+(\d+)(?!\d)', re.IGNORECASE)
    else:
        ref_pattern = re.compile(r'Table\s+(\d+)-(\d+)', re.IGNORECASE)
    
    # Build lookup set for valid table IDs
    valid_ids = {t["id"] for t in tables}
    
    for page_idx in range(page_offset, total_pages):
        text = get_page_text(doc, page_idx)
        for match in ref_pattern.finditer(text):
            if single_number:
                table_id = f"TABLE_{match.group(1)}"
            else:
                table_id = f"TABLE_{match.group(1)}_{match.group(2)}"
            if table_id not in valid_ids:
                continue
            spec_page = page_idx - page_offset + 1
            for table in tables:
                if table["id"] == table_id and spec_page not in table["referenced_on_pages"]:
                    if spec_page != table["spec_page"]:
                        table["referenced_on_pages"].append(spec_page)
    
    print(f"  Tables extracted from TOC: {len(tables)}")
    return tables


def _extract_figure_toc(doc, config: dict, page_offset: int, total_pages: int) -> List[dict]:
    """Extract figure entries from Table of Figures.
    
    Supports both chapter-seq format (Figure X-Y, 4 groups) and
    single-number format (Figure N, 3 groups). Auto-detected from
    the number of capture groups in the regex pattern.
    """
    pages = get_toc_pages(config, "figures")
    pattern_str = get_toc_pattern(config, "figures")
    pattern = re.compile(pattern_str, re.IGNORECASE | re.DOTALL)
    
    # Detect format from number of capture groups
    num_groups = pattern.groups
    single_number = (num_groups == 3)  # (num, title, page) vs (chapter, seq, title, page)
    
    figures = []
    seen = set()
    
    for page_idx in pages:
        if page_idx >= len(doc):
            continue
        text = get_page_text(doc, page_idx)
        for match in pattern.finditer(text):
            if single_number:
                num = match.group(1)
                title = match.group(2).strip().rstrip('.')
                spec_page = int(match.group(3))
                fig_id = f"FIG_{num}"
                spec_ref = f"Figure {num}"
            else:
                chapter = match.group(1)
                seq = match.group(2)
                title = match.group(3).strip().rstrip('.')
                spec_page = int(match.group(4))
                fig_id = f"FIG_{chapter}_{seq}"
                spec_ref = f"Figure {chapter}-{seq}"
            
            if fig_id in seen:
                continue
            seen.add(fig_id)
            
            figures.append({
                "id": fig_id,
                "spec_reference": spec_ref,
                "title": title,
                "spec_page": spec_page,
                "definition_page": spec_page + page_offset,
                "referenced_on_pages": [],
                "transcription": {"status": "PENDING"}
            })
    
    # Scan body pages for figure references
    print(f"  Scanning body pages for figure cross-references...")
    if single_number:
        ref_pattern = re.compile(r'Figure\s+(\d+)(?!\d)', re.IGNORECASE)
    else:
        ref_pattern = re.compile(r'Figure\s+(\d+)-(\d+)', re.IGNORECASE)
    
    # Build lookup set for valid figure IDs
    valid_ids = {f["id"] for f in figures}
    
    for page_idx in range(page_offset, total_pages):
        text = get_page_text(doc, page_idx)
        for match in ref_pattern.finditer(text):
            if single_number:
                fig_id = f"FIG_{match.group(1)}"
            else:
                fig_id = f"FIG_{match.group(1)}_{match.group(2)}"
            if fig_id not in valid_ids:
                continue
            spec_page = page_idx - page_offset + 1
            for figure in figures:
                if figure["id"] == fig_id and spec_page not in figure["referenced_on_pages"]:
                    if spec_page != figure["spec_page"]:
                        figure["referenced_on_pages"].append(spec_page)
    
    print(f"  Figures extracted from TOC: {len(figures)}")
    return figures
