#!/usr/bin/env python3
"""
Extract all table references from the SD Host 3.0 PDF.
Outputs a JSON file mapping each table to its page number and metadata.

The script parses the Table of Tables (TOC) to extract:
- Table ID (e.g., "1-1")
- Title (cleaned, without dots and page number)
- Spec page number (from TOC, after the dots)
- Real PDF page = spec_page + PAGE_OFFSET (since spec page 1 = PDF page 12)

Usage:
    python extract_tables_map.py

Output:
    tables_page_map.json - Complete inventory of all tables with page numbers
"""

import pymupdf
import re
import json
from pathlib import Path
from collections import defaultdict

# Configuration
SCRIPT_DIR = Path(__file__).parent
PDF_PATH = SCRIPT_DIR.parent / "source" / "sd_host_3_00.pdf"
OUTPUT_PATH = SCRIPT_DIR / "tables_page_map.json"

# The spec content starts at PDF page 12 (0-indexed: 11)
# So spec page 1 = PDF page 12, meaning offset = 11
PAGE_OFFSET = 11

def extract_tables():
    """Extract all table references with their page numbers and context."""
    
    doc = pymupdf.open(str(PDF_PATH))
    
    # Pattern to match TOC entries: "Table X-Y : Title............... page_num"
    # Captures: chapter, table_num, title, spec_page
    toc_entry_pattern = re.compile(
        r'Table\s+(\d+)[-.](\d+)\s*:\s*(.+?)\.{3,}\s*(\d+)',
        re.IGNORECASE
    )
    
    # Store table definitions from TOC
    table_definitions = {}
    
    # Scan TOC pages (pages 10-11, indices 9-10) for table entries
    toc_pages = [9, 10]  # 0-indexed PDF pages for Table of Tables
    
    print(f"Scanning Table of Tables on PDF pages {[p+1 for p in toc_pages]}...")
    
    for page_idx in toc_pages:
        if page_idx < len(doc):
            page = doc[page_idx]
            text = page.get_text()
            
            for match in toc_entry_pattern.finditer(text):
                chapter = match.group(1)
                table_num = match.group(2)
                table_id = f"{chapter}-{table_num}"
                raw_title = match.group(3).strip()
                spec_page = int(match.group(4))
                
                # Clean title: remove trailing dots
                title = re.sub(r'\.+\s*$', '', raw_title).strip()
                
                # Calculate real PDF page (1-indexed)
                pdf_page = spec_page + PAGE_OFFSET
                
                if table_id not in table_definitions:
                    table_definitions[table_id] = {
                        "title": title,
                        "spec_page": spec_page,
                        "pdf_page": pdf_page
                    }
    
    print(f"Found {len(table_definitions)} tables in TOC")
    
    # Now scan all pages for references to tables
    reference_pattern = re.compile(r'Table\s+(\d+)[-.](\d+)', re.IGNORECASE)
    table_references = defaultdict(list)
    
    print(f"Scanning {len(doc)} pages for table references...")
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        
        for match in reference_pattern.finditer(text):
            chapter = match.group(1)
            table_num = match.group(2)
            table_id = f"{chapter}-{table_num}"
            # Store 1-indexed page
            table_references[table_id].append(page_num + 1)
    
    doc.close()
    
    # Build the final output structure
    tables = []
    
    for table_id in sorted(table_definitions.keys(), key=lambda x: (int(x.split('-')[0]), int(x.split('-')[1]))):
        definition = table_definitions[table_id]
        refs = table_references.get(table_id, [definition["pdf_page"]])
        
        # Filter out TOC page references (pages 10, 11) from referenced_on_pages
        non_toc_refs = [p for p in refs if p not in [10, 11]]
        
        table_entry = {
            "id": f"TABLE_{table_id.replace('-', '_')}",
            "spec_reference": f"Table {table_id}",
            "title": definition["title"],
            "spec_page": definition["spec_page"],
            "definition_page": definition["pdf_page"],
            "referenced_on_pages": sorted(set(non_toc_refs)),
            "reference_count": len(non_toc_refs),
            # Table structure (to be analyzed from image)
            "columns": [],  # List of column names
            "nb_lines": 0,  # Number of data rows
            "nb_columns": 0,  # Number of columns
            # Table content (to be extracted by conversion script)
            "content": {},  # Dict: column_name -> [row values]
            "raw_content": "",  # Raw text extracted from table
            # Abstract (to be filled by conversion script)
            "abstract": "",
            # Conversion metadata (to be filled by conversion script)
            "conversion": {
                "status": "NOT_STARTED",  # NOT_STARTED | IN_PROGRESS | COMPLETED | INCOMPLETE | FAILED
                "file_format": "",  # CSV | MD
                "file_name": "",
                "validated": False,
                "validation_notes": ""
            }
        }
        
        tables.append(table_entry)
    
    # Build output
    output = {
        "_metadata": {
            "source_pdf": str(PDF_PATH.name),
            "total_pages": len(pymupdf.open(str(PDF_PATH))),
            "extraction_date": "2026-01-31",
            "total_tables": len(tables),
            "page_offset": PAGE_OFFSET,
            "page_offset_note": "Real PDF page = spec_page + page_offset (spec page 1 = PDF page 12)",
            "conversion_progress": {
                "not_started": len(tables),
                "in_progress": 0,
                "completed": 0,
                "incomplete": 0,
                "failed": 0
            }
        },
        "tables": tables
    }
    
    # Write output
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*60}")
    print(f"TABLE EXTRACTION COMPLETE")
    print(f"{'='*60}")
    print(f"Total unique tables found: {len(tables)}")
    print(f"Page offset: {PAGE_OFFSET} (spec page 1 = PDF page {PAGE_OFFSET + 1})")
    print(f"Output written to: {OUTPUT_PATH}")
    print(f"\n{'='*60}")
    print("TABLES BY CHAPTER:")
    print(f"{'='*60}")
    
    # Group by chapter
    chapters = defaultdict(list)
    for table in tables:
        chapter = table["spec_reference"].split()[1].split('-')[0]
        chapters[chapter].append(table)
    
    for chapter in sorted(chapters.keys(), key=int):
        print(f"\nChapter {chapter}: {len(chapters[chapter])} tables")
        for table in chapters[chapter]:
            title_preview = table["title"][:45] + "..." if len(table["title"]) > 45 else table["title"]
            print(f"  [ ] {table['spec_reference']:15} Spec p{table['spec_page']:3} -> PDF p{table['definition_page']:3}  {title_preview}")
    
    print(f"\n{'='*60}")
    print("NEXT STEPS:")
    print(f"{'='*60}")
    print("1. Run extract_table_images.py to export table page images")
    print("2. Run convert_tables_to_csv.py to convert tables to CSV/MD format")
    print("3. Check tables/tables_to_check.md for incomplete tables")
    
    return output

if __name__ == "__main__":
    extract_tables()
