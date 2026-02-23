#!/usr/bin/env python3
"""
PDF Utilities — Shared helpers for PDF manipulation.

Wraps PyMuPDF (fitz) for page text extraction, image rendering, etc.
"""

import re
import io
from pathlib import Path
from typing import List, Optional, Tuple

try:
    import fitz  # PyMuPDF
except ImportError:
    try:
        import pymupdf as fitz
    except ImportError:
        print("ERROR: PyMuPDF not installed. Run: pip install pymupdf")
        import sys
        sys.exit(1)


def open_pdf(pdf_path: Path) -> fitz.Document:
    """Open a PDF file."""
    return fitz.open(str(pdf_path))


def get_page_text(doc: fitz.Document, page_idx: int) -> str:
    """Get text from a 0-indexed PDF page."""
    if page_idx < 0 or page_idx >= len(doc):
        return ""
    return doc[page_idx].get_text()


def get_page_count(doc: fitz.Document) -> int:
    """Get total page count."""
    return len(doc)


def render_page_to_image(doc: fitz.Document, page_idx: int,
                         dpi: int = 200) -> bytes:
    """Render a PDF page to PNG bytes.
    
    Args:
        doc: Open PDF document
        page_idx: 0-indexed page number
        dpi: Resolution (200 = good balance of quality/size)
    
    Returns:
        PNG image as bytes
    """
    page = doc[page_idx]
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    return pix.tobytes("png")


def render_page_region(doc: fitz.Document, page_idx: int,
                       clip_rect: fitz.Rect, dpi: int = 200) -> bytes:
    """Render a specific region of a PDF page to PNG bytes."""
    page = doc[page_idx]
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, clip=clip_rect)
    return pix.tobytes("png")


def spec_to_pdf_page(spec_page: int, page_offset: int) -> int:
    """Convert spec page number to 0-indexed PDF page index.
    
    spec_page 1 with offset 11 → PDF page 12 → index 11
    """
    return spec_page + page_offset - 1


def pdf_to_spec_page(pdf_page_idx: int, page_offset: int) -> int:
    """Convert 0-indexed PDF page to spec page number."""
    return pdf_page_idx - page_offset + 1


def extract_toc_entries(doc: fitz.Document, page_indices: List[int],
                        pattern: str) -> List[dict]:
    """Extract TOC entries from specific PDF pages using a regex pattern.
    
    Args:
        doc: Open PDF document
        page_indices: 0-indexed page numbers to scan
        pattern: Regex pattern with named or positional groups
    
    Returns:
        List of match dicts with group values
    """
    compiled = re.compile(pattern, re.IGNORECASE)
    entries = []
    
    for page_idx in page_indices:
        if page_idx >= len(doc):
            continue
        text = doc[page_idx].get_text()
        for match in compiled.finditer(text):
            entries.append({
                "groups": match.groups(),
                "pdf_page": page_idx,
                "full_match": match.group(0)
            })
    
    return entries


def find_text_on_page(doc: fitz.Document, page_idx: int, search_text: str) -> bool:
    """Check if text appears on a specific PDF page."""
    if page_idx < 0 or page_idx >= len(doc):
        return False
    text = doc[page_idx].get_text()
    return search_text.lower() in text.lower()


def stitch_page_images_vertically(image_list: List[bytes]) -> bytes:
    """Stitch multiple PNG page images vertically into one image.

    Args:
        image_list: List of PNG bytes (top-to-bottom order)

    Returns:
        Combined PNG image as bytes
    """
    if len(image_list) == 1:
        return image_list[0]

    pixmaps = []
    for img_bytes in image_list:
        pixmaps.append(fitz.Pixmap(img_bytes))

    # Compute combined dimensions
    max_width = max(p.width for p in pixmaps)
    total_height = sum(p.height for p in pixmaps)

    # Match colorspace and alpha from source pixmaps
    cs = pixmaps[0].colorspace or fitz.csRGB
    has_alpha = pixmaps[0].alpha

    # Create output pixmap
    combined = fitz.Pixmap(cs, fitz.IRect(0, 0, max_width, total_height), has_alpha)
    combined.clear_with(255)  # white background

    y_offset = 0
    for pix in pixmaps:
        # Create a repositioned pixmap with origin at (0, y_offset)
        dst_rect = fitz.IRect(0, y_offset, pix.width, y_offset + pix.height)
        repositioned = fitz.Pixmap(cs, dst_rect, has_alpha)
        repositioned.clear_with(255)
        # Copy source into repositioned (source has origin at 0,0 so use its own irect)
        repositioned.copy(pix, pix.irect)
        # Now copy repositioned into combined
        combined.copy(repositioned, dst_rect)
        y_offset += pix.height

    return combined.tobytes("png")


def resize_image_if_needed(img_bytes: bytes, max_dim: int = 7500) -> bytes:
    """Downscale a PNG if it exceeds max_dim in either dimension.
    
    Uses Pillow for high-quality LANCZOS resampling.
    Returns original bytes if within limits.
    """
    pix = fitz.Pixmap(img_bytes)
    if pix.height <= max_dim and pix.width <= max_dim:
        return img_bytes
    
    from PIL import Image
    scale = max_dim / max(pix.height, pix.width)
    new_width = int(pix.width * scale)
    new_height = int(pix.height * scale)
    
    img = Image.open(io.BytesIO(img_bytes))
    img = img.resize((new_width, new_height), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()
