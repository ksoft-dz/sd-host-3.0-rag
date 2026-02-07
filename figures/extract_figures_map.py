#!/usr/bin/env python3
"""
Extract all figure references from the SD Host 3.0 PDF.
Outputs a JSON file mapping each figure to its page number and context.

The script parses the Table of Figures (TOC) to extract:
- Figure ID (e.g., "1-1")
- Title (cleaned, without dots and page number)
- Spec page number (from TOC, after the dots)
- Real PDF page = spec_page + PAGE_OFFSET (since spec page 1 = PDF page 12)

Usage:
    python extract_figures_map.py

Output:
    figures_page_map.json - Complete inventory of all figures with page numbers
"""

import pymupdf
import re
import json
from pathlib import Path
from collections import defaultdict

# Configuration
PDF_PATH = Path(__file__).parent.parent / "source" / "sd_host_3_00.pdf"
OUTPUT_PATH = Path(__file__).parent / "figures_page_map.json"

# The spec content starts at PDF page 12 (0-indexed: 11)
# So spec page 1 = PDF page 12, meaning offset = 11
PAGE_OFFSET = 11

def extract_figures():
    """Extract all figure references with their page numbers and context."""
    
    doc = pymupdf.open(str(PDF_PATH))
    
    # Pattern to match TOC entries: "Figure X-Y : Title............... page_num"
    # Captures: chapter, figure_num, title, spec_page
    toc_entry_pattern = re.compile(
        r'Figure\s+(\d+)[-.](\d+)\s*:\s*(.+?)\.{3,}\s*(\d+)',
        re.IGNORECASE
    )
    
    # Store figure definitions from TOC
    figure_definitions = {}
    
    # Scan TOC pages (pages 8-9, indices 7-8) for figure entries
    toc_pages = [7, 8]  # 0-indexed PDF pages for Table of Figures
    
    print(f"Scanning Table of Figures on PDF pages {[p+1 for p in toc_pages]}...")
    
    for page_idx in toc_pages:
        if page_idx < len(doc):
            page = doc[page_idx]
            text = page.get_text()
            
            for match in toc_entry_pattern.finditer(text):
                chapter = match.group(1)
                fig_num = match.group(2)
                fig_id = f"{chapter}-{fig_num}"
                raw_title = match.group(3).strip()
                spec_page = int(match.group(4))
                
                # Clean title: remove trailing dots
                title = re.sub(r'\.+\s*$', '', raw_title).strip()
                
                # Calculate real PDF page (1-indexed)
                pdf_page = spec_page + PAGE_OFFSET
                
                if fig_id not in figure_definitions:
                    figure_definitions[fig_id] = {
                        "title": title,
                        "spec_page": spec_page,
                        "pdf_page": pdf_page
                    }
    
    print(f"Found {len(figure_definitions)} figures in TOC")
    
    # Now scan all pages for references to figures
    reference_pattern = re.compile(r'Figure\s+(\d+)[-.](\d+)', re.IGNORECASE)
    figure_references = defaultdict(list)
    
    print(f"Scanning {len(doc)} pages for figure references...")
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        
        for match in reference_pattern.finditer(text):
            chapter = match.group(1)
            fig_num = match.group(2)
            fig_id = f"{chapter}-{fig_num}"
            # Store 1-indexed page
            figure_references[fig_id].append(page_num + 1)
    
    doc.close()
    
    # Build the final output structure
    figures = []
    
    for fig_id in sorted(figure_definitions.keys(), key=lambda x: (int(x.split('-')[0]), int(x.split('-')[1]))):
        definition = figure_definitions[fig_id]
        refs = figure_references.get(fig_id, [definition["pdf_page"]])
        
        # Filter out TOC page references (pages 8, 9) from referenced_on_pages
        non_toc_refs = [p for p in refs if p not in [8, 9]]
        
        figure_entry = {
            "id": f"FIG_{fig_id.replace('-', '_')}",
            "spec_reference": f"Figure {fig_id}",
            "title": definition["title"],
            "spec_page": definition["spec_page"],
            "definition_page": definition["pdf_page"],
            "referenced_on_pages": sorted(set(non_toc_refs)),
            "reference_count": len(non_toc_refs),
            # Searchable content from the diagram (to be filled after Mermaid transcription)
            "content": [],
            # Phase -1 fields (to be filled by user)
            "transcription": {
                "status": "NOT_STARTED",  # NOT_STARTED | IN_PROGRESS | COMPLETED | SKIPPED
                "text_file": "",
                "image_file": "",
                "format": "",  # MERMAID | PLANTUML | ASCII | MARKDOWN | NONE
                "validated": False,
                "validation_notes": ""
            }
        }
        
        figures.append(figure_entry)
    
    # Build output
    output = {
        "_metadata": {
            "source_pdf": str(PDF_PATH.name),
            "total_pages": len(pymupdf.open(str(PDF_PATH))),
            "extraction_date": "2026-01-31",
            "total_figures": len(figures),
            "page_offset": PAGE_OFFSET,
            "page_offset_note": "Real PDF page = spec_page + page_offset (spec page 1 = PDF page 12)",
            "transcription_progress": {
                "not_started": len(figures),
                "in_progress": 0,
                "completed": 0,
                "skipped": 0
            }
        },
        "figures": figures
    }
    
    # Write output
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*60}")
    print(f"FIGURE EXTRACTION COMPLETE")
    print(f"{'='*60}")
    print(f"Total unique figures found: {len(figures)}")
    print(f"Page offset: {PAGE_OFFSET} (spec page 1 = PDF page {PAGE_OFFSET + 1})")
    print(f"Output written to: {OUTPUT_PATH}")
    print(f"\n{'='*60}")
    print("FIGURES BY CHAPTER:")
    print(f"{'='*60}")
    
    # Group by chapter
    chapters = defaultdict(list)
    for fig in figures:
        chapter = fig["spec_reference"].split()[1].split('-')[0]
        chapters[chapter].append(fig)
    
    for chapter in sorted(chapters.keys(), key=int):
        print(f"\nChapter {chapter}: {len(chapters[chapter])} figures")
        for fig in chapters[chapter]:
            status = "[ ]" if fig["transcription"]["status"] == "NOT_STARTED" else "[x]"
            title_preview = fig["title"][:45] + "..." if len(fig["title"]) > 45 else fig["title"]
            print(f"  {status} {fig['spec_reference']:15} Spec p{fig['spec_page']:3} → PDF p{fig['definition_page']:3}  {title_preview}")
    
    print(f"\n{'='*60}")
    print("NEXT STEPS (Phase -1):")
    print(f"{'='*60}")
    print("1. Open the PDF and export each figure as PNG")
    print("2. Use LLM vision to transcribe to text format")
    print("3. Save text files as: figure_X-Y_description.md")
    print("4. Update figures_page_map.json with transcription status")
    print("5. When all complete, copy to figures_index.json")
    
    return output

if __name__ == "__main__":
    extract_figures()
