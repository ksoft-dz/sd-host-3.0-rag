#!/usr/bin/env python3
"""
Extract page images for all tables from the SD Host 3.0 PDF.
Reads tables_page_map.json and exports each table's page as a JPG image.

Usage:
    python extract_table_images.py

Output:
    tables/images/TABLE_X_Y.jpg - One image per table (page where table is defined)
"""

import pymupdf
import json
from pathlib import Path

# Configuration
SCRIPT_DIR = Path(__file__).parent
PDF_PATH = SCRIPT_DIR.parent / "source" / "sd_host_3_00.pdf"
TABLES_MAP_PATH = SCRIPT_DIR / "tables_page_map.json"
OUTPUT_DIR = SCRIPT_DIR / "images"

# Image quality settings
DPI = 150  # Resolution (150 DPI is good balance of quality/size)
ZOOM = DPI / 72  # PyMuPDF default is 72 DPI


def extract_table_images():
    """Extract page images for all tables."""
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load tables map
    with open(TABLES_MAP_PATH, 'r', encoding='utf-8') as f:
        tables_data = json.load(f)
    
    tables = tables_data["tables"]
    total = len(tables)
    
    print(f"Extracting {total} table page images...")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Resolution: {DPI} DPI")
    print("=" * 60)
    
    # Open PDF
    doc = pymupdf.open(str(PDF_PATH))
    
    # Track pages already exported (multiple tables can be on same page)
    exported_pages = {}
    
    for i, table in enumerate(tables, 1):
        table_id = table["id"]
        pdf_page = table["definition_page"]
        page_idx = pdf_page - 1  # 0-indexed
        
        output_path = OUTPUT_DIR / f"{table_id}.jpg"
        
        # Export the page as image (always export, even if same page as previous)
        page = doc[page_idx]
        
        # Create transformation matrix for zoom
        mat = pymupdf.Matrix(ZOOM, ZOOM)
        
        # Render page to pixmap
        pix = page.get_pixmap(matrix=mat)
        
        # Save as JPEG
        pix.save(str(output_path), "jpeg")
        
        # Track and log
        if pdf_page in exported_pages:
            # Multiple tables on same page
            print(f"[{i:3}/{total}] {table_id:15} - Page {pdf_page:3} -> {output_path.name} (same page as {exported_pages[pdf_page]})")
            exported_pages[pdf_page].append(table_id)
        else:
            exported_pages[pdf_page] = [table_id]
            print(f"[{i:3}/{total}] {table_id:15} - Page {pdf_page:3} -> {output_path.name}")
        
    doc.close()
    
    print("=" * 60)
    print(f"COMPLETE: {total} images exported to {OUTPUT_DIR}")
    print(f"Unique pages: {len(exported_pages)}")
    

if __name__ == "__main__":
    extract_table_images()
