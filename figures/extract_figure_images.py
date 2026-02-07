#!/usr/bin/env python3
"""
Extract page images for all figures from the SD Host 3.0 PDF.
Reads figures_page_map.json and exports each figure's page as a JPG image.

Usage:
    python extract_figure_images.py

Output:
    figures/images/FIG_X_Y.jpg - One image per figure (page where figure is defined)
"""

import pymupdf
import json
from pathlib import Path

# Configuration
SCRIPT_DIR = Path(__file__).parent
PDF_PATH = SCRIPT_DIR.parent / "source" / "sd_host_3_00.pdf"
FIGURES_MAP_PATH = SCRIPT_DIR / "figures_page_map.json"
OUTPUT_DIR = SCRIPT_DIR / "images"

# Image quality settings
DPI = 150  # Resolution (150 DPI is good balance of quality/size)
ZOOM = DPI / 72  # PyMuPDF default is 72 DPI


def extract_figure_images():
    """Extract page images for all figures."""
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load figures map
    with open(FIGURES_MAP_PATH, 'r', encoding='utf-8') as f:
        figures_data = json.load(f)
    
    figures = figures_data["figures"]
    total = len(figures)
    
    print(f"Extracting {total} figure page images...")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Resolution: {DPI} DPI")
    print("=" * 60)
    
    # Open PDF
    doc = pymupdf.open(str(PDF_PATH))
    
    # Track pages already exported (multiple figures can be on same page)
    exported_pages = {}
    
    for i, fig in enumerate(figures, 1):
        fig_id = fig["id"]
        pdf_page = fig["definition_page"]
        page_idx = pdf_page - 1  # 0-indexed
        
        output_path = OUTPUT_DIR / f"{fig_id}.jpg"
        
        # Check if we already exported this page
        if pdf_page in exported_pages:
            # Copy from existing export (or just note it's the same page)
            print(f"[{i:3}/{total}] {fig_id:15} - Page {pdf_page:3} (same as {exported_pages[pdf_page]})")
            # For figures on same page, we still create the file (copy or re-export)
        
        # Export the page as image
        page = doc[page_idx]
        
        # Create transformation matrix for zoom
        mat = pymupdf.Matrix(ZOOM, ZOOM)
        
        # Render page to pixmap
        pix = page.get_pixmap(matrix=mat)
        
        # Save as JPEG
        pix.save(str(output_path), "jpeg")
        
        if pdf_page not in exported_pages:
            exported_pages[pdf_page] = fig_id
            print(f"[{i:3}/{total}] {fig_id:15} - Page {pdf_page:3} → {output_path.name}")
        
    doc.close()
    
    print("=" * 60)
    print(f"COMPLETE: {total} images exported to {OUTPUT_DIR}")
    print(f"Unique pages: {len(exported_pages)}")
    

if __name__ == "__main__":
    extract_figure_images()
