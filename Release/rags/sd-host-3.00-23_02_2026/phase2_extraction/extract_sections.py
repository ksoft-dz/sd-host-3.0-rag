#!/usr/bin/env python3
"""
Phase 2a: Extract and chunk specification text into sections.json.

Reads PDF page-by-page, chunks text at ~200-word boundaries,
uses LLM to generate abstracts and keywords for each chunk.

Depends on: Phase 1 discovery.json (for table/figure maps to exclude)
Output: intermediates/sections.json
"""

import json
import re
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.config import (
    get_page_offset, get_chunking_config, get_llm_model, get_llm_config,
    get_intermediates_dir, PIPELINE_ROOT
)
from shared.pdf_utils import open_pdf, get_page_text, get_page_count
from shared.llm_client import LLMClient
from shared.utils import (
    load_json, save_json, extract_keywords, extract_technical_terms,
    find_table_references, find_figure_references, print_step
)


def extract_sections(config: dict, pdf_path: Path,
                     skip_existing: bool = False,
                     model: str = None,
                     workers: int = None):
    """Main entry point for section extraction.
    
    1. Load discovery.json for TOC structure
    2. Process each spec page to extract text
    3. Chunk text at ~200-word boundaries
    4. LLM-generate abstracts and keywords for each chunk
    5. Build hierarchical sections.json
    """
    intermediates = get_intermediates_dir()
    output_path = intermediates / "sections.json"
    
    # Load discovery data
    discovery_path = intermediates / "discovery.json"
    if not discovery_path.exists():
        print("ERROR: Run 'discover' phase first to create discovery.json")
        return
    discovery = load_json(discovery_path)
    
    # Load existing if skip_existing
    existing = {}
    if skip_existing and output_path.exists():
        existing = load_json(output_path)
        print(f"  Loaded existing sections.json ({len(existing.get('sections', {}))} sections)")
    
    # Setup
    page_offset = get_page_offset(config)
    chunking = get_chunking_config(config)
    target_words = chunking.get("target_words", 200)
    max_words = chunking.get("max_words", 250)
    
    llm_config = get_llm_config(config)
    num_workers = workers or llm_config.get("max_workers", 4)
    
    # Build section tree from TOC
    toc_sections = discovery.get("toc", {}).get("sections", [])
    
    # Get table/figure page sets (to exclude from chunking)
    table_pages = set()
    for t in discovery.get("toc", {}).get("tables", []):
        table_pages.add(t.get("spec_page", 0))
    
    figure_pages = set()
    for f in discovery.get("toc", {}).get("figures", []):
        figure_pages.add(f.get("spec_page", 0))
    
    doc = open_pdf(pdf_path)
    total_pages = get_page_count(doc)
    
    # Build section structure
    sections = {}
    for sec in toc_sections:
        sec_num = sec["section_number"]
        if skip_existing and sec_num in existing.get("sections", {}):
            sections[sec_num] = existing["sections"][sec_num]
            continue
        
        sections[sec_num] = {
            "id": f"SEC_{sec_num.replace('.', '_')}",
            "section_number": sec_num,
            "title": sec["title"],
            "depth": sec["depth"],
            "source": {
                "spec_page_start": sec["spec_page"],
                "pdf_page_start": sec["pdf_page"]
            },
            "chunks": [],
            "index": {
                "keywords": [],
                "technical_terms": []
            },
            "extraction": {
                "status": "PENDING",
                "confidence": 0.0
            }
        }
    
    # Process pages and assign chunks to sections
    print_step("1/3", f"Extracting text from {total_pages - page_offset} spec pages...")
    
    # Collect raw page texts
    page_texts = {}
    for page_idx in range(page_offset, total_pages):
        spec_page = page_idx - page_offset + 1
        text = get_page_text(doc, page_idx)
        if text.strip():
            page_texts[spec_page] = text
    
    doc.close()
    
    # Chunk pages and assign to sections
    print_step("2/3", "Chunking text into ~200-word segments...")
    all_chunks = _chunk_pages(page_texts, toc_sections, target_words, max_words)
    
    # Use LLM to generate abstracts
    print_step("3/3", f"Generating abstracts via LLM ({num_workers} workers)...")
    llm = LLMClient(config, model_override=model)
    
    chunks_needing_abstract = [c for c in all_chunks if not c.get("abstract")]
    
    if chunks_needing_abstract:
        _generate_abstracts_parallel(llm, chunks_needing_abstract, num_workers)
    
    # Assign chunks to sections
    for chunk in all_chunks:
        sec_num = chunk.get("section_number", "")
        if sec_num in sections:
            sections[sec_num]["chunks"].append({
                "chunk_id": chunk["chunk_id"],
                "chunk_index": chunk["chunk_index"],
                "spec_page": chunk["spec_page"],
                "word_count": chunk["word_count"],
                "abstract": chunk.get("abstract", ""),
                "raw": chunk.get("raw", "")
            })
            sections[sec_num]["extraction"]["status"] = "COMPLETED"
            sections[sec_num]["extraction"]["confidence"] = 0.9
    
    # Generate section-level keywords
    for sec_num, sec in sections.items():
        all_text = " ".join(c.get("raw", "") for c in sec["chunks"])
        sec["index"]["keywords"] = extract_keywords(sec["title"] + " " + all_text)
        sec["index"]["technical_terms"] = extract_technical_terms(all_text)
    
    # Build output
    output = {
        "_metadata": {
            "source": config["spec"]["name"],
            "version": config["spec"]["version"],
            "extraction_date": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "total_sections": len(sections),
            "total_chunks": sum(len(s["chunks"]) for s in sections.values()),
            "llm_stats": llm.stats
        },
        "sections": sections
    }
    
    save_json(output, output_path)
    print(f"  Sections: {len(sections)}, Chunks: {output['_metadata']['total_chunks']}")


def _chunk_pages(page_texts: Dict[int, str], toc_sections: List[dict],
                 target_words: int, max_words: int) -> List[dict]:
    """Split page texts into chunks, assigning each to the nearest section."""
    
    # Build page→section mapping
    section_starts = sorted(toc_sections, key=lambda s: s["spec_page"])
    
    def find_section(spec_page: int) -> str:
        """Find which section a spec page belongs to."""
        best = ""
        for sec in section_starts:
            if sec["spec_page"] <= spec_page:
                best = sec["section_number"]
            else:
                break
        return best
    
    chunks = []
    chunk_idx_by_section = {}
    
    for spec_page in sorted(page_texts.keys()):
        text = page_texts[spec_page]
        section_num = find_section(spec_page)
        
        # Split into paragraphs
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        current_chunk_text = ""
        current_word_count = 0
        
        for para in paragraphs:
            para_words = len(para.split())
            
            if current_word_count + para_words > max_words and current_chunk_text:
                # Flush current chunk
                idx = chunk_idx_by_section.get(section_num, 0)
                chunks.append({
                    "chunk_id": f"CHUNK_{section_num.replace('.', '_')}_{idx}",
                    "chunk_index": idx,
                    "section_number": section_num,
                    "spec_page": spec_page,
                    "word_count": current_word_count,
                    "raw": current_chunk_text.strip(),
                    "abstract": ""
                })
                chunk_idx_by_section[section_num] = idx + 1
                current_chunk_text = ""
                current_word_count = 0
            
            current_chunk_text += para + "\n\n"
            current_word_count += para_words
        
        # Flush remaining text
        if current_chunk_text.strip():
            idx = chunk_idx_by_section.get(section_num, 0)
            chunks.append({
                "chunk_id": f"CHUNK_{section_num.replace('.', '_')}_{idx}",
                "chunk_index": idx,
                "section_number": section_num,
                "spec_page": spec_page,
                "word_count": current_word_count,
                "raw": current_chunk_text.strip(),
                "abstract": ""
            })
            chunk_idx_by_section[section_num] = idx + 1
    
    print(f"    Created {len(chunks)} chunks from {len(page_texts)} pages")
    return chunks


def _generate_abstracts_parallel(llm: LLMClient, chunks: List[dict], workers: int):
    """Generate LLM abstracts for chunks in parallel."""
    
    system_prompt = """You are a technical specification analyst. Given a text chunk from a hardware spec, produce:
1. A concise 1-2 sentence abstract
2. 5-10 index keywords

Respond in this exact JSON format:
{"abstract": "...", "keywords": ["...", "..."]}

No markdown, no explanation, just the JSON object."""

    completed = 0
    total = len(chunks)
    
    def process_chunk(chunk):
        text = chunk["raw"][:2000]  # Limit input size
        prompt = f"Chunk from section '{chunk['section_number']}' (page {chunk['spec_page']}):\n\n{text}"
        
        try:
            response = llm.call(system_prompt, prompt, max_tokens=512)
            # Parse JSON response
            data = json.loads(response)
            chunk["abstract"] = data.get("abstract", "")
            chunk_keywords = data.get("keywords", [])
            # Merge with extracted keywords
            existing = extract_keywords(text)
            chunk["keywords"] = list(set(existing + chunk_keywords))[:20]
        except (json.JSONDecodeError, Exception) as e:
            chunk["abstract"] = f"[LLM extraction failed: {str(e)[:100]}]"
        
        return chunk
    
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(process_chunk, c): c for c in chunks}
        for future in as_completed(futures):
            completed += 1
            if completed % 20 == 0 or completed == total:
                print(f"    Abstracts: {completed}/{total}")
            future.result()
