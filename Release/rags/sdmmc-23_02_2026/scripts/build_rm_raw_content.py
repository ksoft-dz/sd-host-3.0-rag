#!/usr/bin/env python3
"""
Build rm_raw_content chunks from the full RM0452 PDF using bookmarks.

Extracts top-level chapter bookmarks, splits into per-chapter raw text chunks.
These give an agent lightweight context about the broader SoC without running
the full LLM pipeline on 3897 pages.
"""

import json
from pathlib import Path
import fitz  # PyMuPDF


def build_rm_raw_content(pdf_path: str, out_path: str, max_pages_per_chunk: int = 40):
    """
    Extract per-chapter raw text from the full RM using bookmarks.
    
    Chapters larger than max_pages_per_chunk are split into sub-chunks.
    """
    doc = fitz.open(pdf_path)
    toc = doc.get_toc()  # list of [level, title, page_number]
    total_pages = len(doc)
    
    # Get chapter-level bookmarks (level 3 in RM0452)
    chapters = []
    for level, title, page_num in toc:
        if level == 3:
            chapters.append({
                "title": title.strip(),
                "start_page": page_num  # 1-indexed
            })
    
    # Calculate end pages
    for i in range(len(chapters)):
        if i < len(chapters) - 1:
            chapters[i]["end_page"] = chapters[i + 1]["start_page"] - 1
        else:
            chapters[i]["end_page"] = total_pages
    
    print(f"Found {len(chapters)} top-level chapters")
    
    chunks = []
    for ch in chapters:
        start = ch["start_page"]
        end = ch["end_page"]
        page_count = end - start + 1
        title = ch["title"]
        
        if page_count <= max_pages_per_chunk:
            # Single chunk for the chapter
            text = ""
            for p in range(start - 1, end):  # fitz is 0-indexed
                text += doc[p].get_text()
            
            # Truncate if too large
            words = text.split()
            if len(words) > 8000:
                text = " ".join(words[:8000]) + "\n... [truncated]"
            
            chunks.append({
                "id": f"RM_RAW_{len(chunks) + 1:03d}",
                "title": title,
                "page_range": f"{start}-{end}",
                "page_count": page_count,
                "word_count": len(text.split()),
                "content": text.strip()
            })
        else:
            # Split into sub-chunks
            sub_start = start
            sub_idx = 0
            while sub_start <= end:
                sub_end = min(sub_start + max_pages_per_chunk - 1, end)
                text = ""
                for p in range(sub_start - 1, sub_end):
                    if p < total_pages:
                        text += doc[p].get_text()
                
                words = text.split()
                if len(words) > 8000:
                    text = " ".join(words[:8000]) + "\n... [truncated]"
                
                sub_idx += 1
                chunks.append({
                    "id": f"RM_RAW_{len(chunks) + 1:03d}",
                    "title": f"{title} (part {sub_idx})",
                    "page_range": f"{sub_start}-{sub_end}",
                    "page_count": sub_end - sub_start + 1,
                    "word_count": len(text.split()),
                    "content": text.strip()
                })
                sub_start = sub_end + 1
    
    doc.close()
    
    # Build output
    result = {
        "source": Path(pdf_path).name,
        "total_chapters": len(chapters),
        "total_chunks": len(chunks),
        "chunks": chunks
    }
    
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    total_words = sum(c["word_count"] for c in chunks)
    print(f"Built {len(chunks)} chunks from {len(chapters)} chapters")
    print(f"Total words: {total_words:,}")
    print(f"Output: {out}")
    
    # Summary
    for c in chunks:
        print(f"  {c['id']}  p{c['page_range']:>12s}  ({c['page_count']:3d}p, {c['word_count']:5d}w)  {c['title'][:60]}")
    
    return result


if __name__ == "__main__":
    rag_v2 = Path(__file__).parent.parent
    workspace = rag_v2.parent
    pdf_name = "rm0452-spc58-h-line--32-bit-power-architecture-automotive-mcu-triple-z4-cores-200-mhz-10-mbytes-flash-hsm-asild-stmicroelectronics.pdf"
    pdf = workspace / pdf_name
    out = rag_v2 / "intermediates" / "rm_raw_content.json"
    build_rm_raw_content(str(pdf), str(out), max_pages_per_chunk=40)
