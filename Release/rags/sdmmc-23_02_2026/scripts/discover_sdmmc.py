#!/usr/bin/env python3
"""
Custom discovery for SDMMC chapter extracted from RM0452.

Since the extracted PDF has no TOC pages (it's a single chapter pulled from a
3897-page reference manual), this script scans page content to find sections,
tables, and figures.
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import fitz  # PyMuPDF


def discover_sdmmc(pdf_path: str, out_path: str, page_offset: int = 2848):
    """
    Scan the extracted SDMMC PDF and produce discovery.json.
    
    page_offset: original_page = extracted_page + page_offset
                 extracted page 1 = original page 2849, so offset = 2848
    """
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    
    sections = []
    tables = []
    figures = []
    
    # Track table/figure IDs we've seen to avoid duplicates from continuations
    seen_table_ids = set()
    seen_figure_ids = set()
    
    for page_idx in range(total_pages):
        page_num = page_idx + 1  # 1-indexed relative page
        text = doc[page_idx].get_text()
        lines = text.split('\n')
        
        for line in lines:
            s = line.strip()
            
            # --- SECTIONS ---
            # Pattern 1: number alone on line (title on next line)
            # Pattern 2: number + title on same line: "57.3.2.10 Present state register (PRESENTSTATE)"
            sec_match = re.match(r'^(57(?:\.\d+)+)\s*$', s)
            sec_match_inline = None
            if not sec_match:
                sec_match_inline = re.match(r'^(57(?:\.\d+)+)\s+(.+)$', s)
            
            if sec_match or sec_match_inline:
                if sec_match:
                    sec_num = sec_match.group(1)
                    # Find the title on the next non-empty line
                    title = ""
                    line_idx = lines.index(line) if line in lines else -1
                    if line_idx >= 0:
                        for j in range(line_idx + 1, min(line_idx + 4, len(lines))):
                            candidate = lines[j].strip()
                            if candidate and not candidate.startswith('57.') and not re.match(r'^\d+/\d+$', candidate):
                                title = candidate
                                break
                else:
                    sec_num = sec_match_inline.group(1)
                    title = sec_match_inline.group(2).strip()
                
                # Avoid duplicates
                if any(s_['section_number'] == sec_num for s_ in sections):
                    continue
                
                depth = sec_num.count('.')
                sections.append({
                    "section_number": sec_num,
                    "title": title,
                    "spec_page": page_num,
                    "pdf_page": page_num,
                    "depth": depth
                })
            
            # --- TABLES ---
            # Match "Table 1808. SDMMC memory map" or "Table 1808. ... (continued)"
            tbl_match = re.match(r'^Table\s+(\d+)\.\s+(.+?)(?:\s*\(continued\))?$', s)
            if tbl_match:
                tbl_num = int(tbl_match.group(1))
                tbl_title = tbl_match.group(2).strip()
                is_continued = '(continued)' in s
                
                # Create a chapter-relative ID: Table 1808 -> TABLE_57_1, Table 1809 -> TABLE_57_2, etc.
                tbl_id = f"TABLE_57_{tbl_num - 1807}"
                
                if tbl_id not in seen_table_ids:
                    seen_table_ids.add(tbl_id)
                    tables.append({
                        "id": tbl_id,
                        "spec_reference": f"Table {tbl_num}",
                        "original_number": tbl_num,
                        "title": tbl_title,
                        "spec_page": page_num,
                        "definition_page": page_num,
                        "referenced_on_pages": [],
                        "conversion": {"status": "PENDING"}
                    })
            
            # --- FIGURES ---
            # Match "Figure 1830. 3MCR controller" etc.
            fig_match = re.match(r'^Figure\s+(\d+)\.\s+(.+?)$', s)
            if fig_match:
                fig_num = int(fig_match.group(1))
                fig_title = fig_match.group(2).strip()
                
                fig_id = f"FIG_57_{fig_num - 1829}"
                
                if fig_id not in seen_figure_ids:
                    seen_figure_ids.add(fig_id)
                    figures.append({
                        "id": fig_id,
                        "spec_reference": f"Figure {fig_num}",
                        "original_number": fig_num,
                        "title": fig_title,
                        "spec_page": page_num,
                        "definition_page": page_num,
                        "referenced_on_pages": [],
                        "transcription": {"status": "PENDING"}
                    })
    
    doc.close()
    
    # Build discovery.json
    discovery = {
        "pdf_structure": {
            "pdf_file": Path(pdf_path).name,
            "total_pages": total_pages,
            "page_offset": 0,  # Relative to extracted PDF
            "total_spec_pages": total_pages,
            "original_page_offset": page_offset,
            "detected_features": {
                "sections": {"found": len(sections) > 0, "count": len(sections), "toc_pages": []},
                "tables":   {"found": len(tables) > 0,   "count": len(tables),   "toc_pages": []},
                "figures":  {"found": len(figures) > 0,   "count": len(figures),  "toc_pages": []}
            },
            "page_offset_validation": {
                "first_spec_page_text_preview": "Section 57 - SDMMC chapter extracted from RM0452",
                "looks_like_content_start": True
            }
        },
        "toc": {
            "sections": sections,
            "tables": tables,
            "figures": figures
        },
        "generated_at": datetime.now(timezone.utc).isoformat()
    }
    
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(discovery, f, indent=2, ensure_ascii=False)
    
    print(f"Discovery complete:")
    print(f"  Sections: {len(sections)}")
    print(f"  Tables:   {len(tables)}")
    print(f"  Figures:  {len(figures)}")
    print(f"  Output:   {out}")
    
    return discovery


if __name__ == "__main__":
    rag_v2 = Path(__file__).parent.parent           # sdmmc_rag/_rag_v2
    workspace = rag_v2.parent                       # sdmmc_rag/
    pdf = workspace / "sdmmc_chapter_57.pdf"
    out = rag_v2 / "intermediates" / "discovery.json"
    discover_sdmmc(str(pdf), str(out))
