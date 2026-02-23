#!/usr/bin/env python3
"""
Phase 2b: Extract tables from PDF as CSV files.

For each table found in discovery.json:
1. Detect multi-page tables (config-driven backward/forward scan)
2. Render + stitch page images into one combined image
3. Send to LLM vision with optional extraction hints from config
4. Save CSV + update tables_page_map.json

Config-driven features:
- extraction.tables.multi_page: auto-detect tables spanning multiple pages
- extraction.tables.hints: inject LLM prompt instructions for specific table types

Depends on: Phase 1 discovery.json
Output: intermediates/tables_page_map.json + intermediates/tables_csv/*.csv
"""

import json
import re
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Set

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.config import (
    get_page_offset, get_llm_config, get_intermediates_dir,
    get_tables_csv_dir, get_tables_images_dir,
    get_table_multi_page_config, find_matching_hint
)
from shared.pdf_utils import (
    open_pdf, render_page_to_image, get_page_text,
    stitch_page_images_vertically, resize_image_if_needed
)
from shared.llm_client import LLMClient
from shared.utils import load_json, save_json, print_step


def extract_tables(config: dict, pdf_path: Path,
                   skip_existing: bool = False,
                   model: str = None,
                   workers: int = None):
    """Main entry point for table extraction.
    
    1. Load discovery.json for table inventory
    2. Render each table page as image
    3. LLM vision → CSV
    4. Generate abstract
    5. Save CSV + update tracking JSON
    """
    intermediates = get_intermediates_dir()
    csv_dir = get_tables_csv_dir()
    images_dir = get_tables_images_dir()
    output_path = intermediates / "tables_page_map.json"
    
    # Load discovery
    discovery_path = intermediates / "discovery.json"
    if not discovery_path.exists():
        print("ERROR: Run 'discover' phase first")
        return
    discovery = load_json(discovery_path)
    tables = discovery.get("toc", {}).get("tables", [])
    
    if not tables:
        print("  No tables found in discovery.json")
        return
    
    # Load existing map if skip_existing
    existing_map = {}
    if skip_existing and output_path.exists():
        existing_data = load_json(output_path)
        for t in existing_data.get("tables", []):
            existing_map[t["id"]] = t
    
    # Setup
    llm_config = get_llm_config(config)
    num_workers = workers or llm_config.get("max_workers", 4)
    multi_cfg = get_table_multi_page_config(config)
    
    doc = open_pdf(pdf_path)
    llm = LLMClient(config, model_override=model)
    
    # Step 1: Detect pages for each table
    print_step("1/3", f"Detecting table pages (multi_page={'ON' if multi_cfg.get('enabled') else 'OFF'})...")
    
    table_pages = {}  # table_id -> sorted list of 0-indexed pages
    all_pages_needed = set()
    for table in tables:
        pages = _detect_table_pages(table, tables, doc, multi_cfg)
        table_pages[table["id"]] = pages
        all_pages_needed.update(pages)
        if len(pages) > 1:
            print(f"    {table['id']}: multi-page -> {len(pages)} pages (pdf {[p+1 for p in pages]})")
    
    # Step 2: Render page images
    print_step("2/3", f"Rendering {len(all_pages_needed)} unique page images...")
    
    page_images = {}
    for pdf_page in sorted(all_pages_needed):
        img_bytes = render_page_to_image(doc, pdf_page, dpi=200)
        page_images[pdf_page] = img_bytes
        img_path = images_dir / f"page_{pdf_page + 1}.png"
        if not img_path.exists():
            img_path.write_bytes(img_bytes)
    
    doc.close()
    
    # Step 3: LLM extraction
    print_step("3/3", f"Converting tables to CSV via LLM vision...")
    
    results = []
    completed = 0
    total = len(tables)
    
    for table in tables:
        table_id = table["id"]
        
        # Skip if already done (check CSV exists on disk AND JSON map)
        if skip_existing:
            csv_path = csv_dir / f"{table_id}.csv"
            if csv_path.exists() and csv_path.stat().st_size > 10:
                if table_id in existing_map:
                    existing = existing_map[table_id]
                    if existing.get("conversion", {}).get("status") == "COMPLETED":
                        results.append(existing)
                        completed += 1
                        continue
                # CSV exists but not in JSON map — record it
                table["conversion"] = {
                    "status": "COMPLETED",
                    "csv_file": str(csv_path.relative_to(intermediates.parent)),
                    "model": llm.model,
                    "note": "resumed from existing CSV"
                }
                table["abstract"] = ""
                results.append(table)
                completed += 1
                continue
        
        # Build image (stitch if multi-page)
        pages = table_pages.get(table_id, [table["definition_page"] - 1])
        images = [page_images[p] for p in pages if p in page_images]
        
        if not images:
            table["conversion"] = {"status": "FAILED", "error": "No images rendered"}
            results.append(table)
            completed += 1
            continue
        
        image_data = stitch_page_images_vertically(images) if len(images) > 1 else images[0]
        image_data = resize_image_if_needed(image_data)  # Stay under API max 8000px
        
        # Find matching hint from config
        hint = find_matching_hint(config, table.get("title", ""))
        
        # LLM vision -> CSV
        try:
            csv_text, abstract = _convert_table_to_csv(llm, table, image_data, hint)
            
            # Save CSV
            csv_path = csv_dir / f"{table_id}.csv"
            csv_path.write_text(csv_text, encoding='utf-8')
            
            table["conversion"] = {
                "status": "COMPLETED",
                "csv_file": str(csv_path.relative_to(intermediates.parent)),
                "model": llm.model,
                "pages_used": [p + 1 for p in pages],
                "multi_page": len(pages) > 1,
                "hint_applied": hint["name"] if hint else None
            }
            table["abstract"] = abstract
            
        except Exception as e:
            table["conversion"] = {
                "status": "FAILED",
                "error": str(e)[:200]
            }
        
        results.append(table)
        completed += 1
        if completed % 5 == 0 or completed == total:
            print(f"    Tables: {completed}/{total}")
    
    # Build output
    success = sum(1 for t in results if t.get("conversion", {}).get("status") == "COMPLETED")
    multi_count = sum(1 for t in results if t.get("conversion", {}).get("multi_page", False))
    hint_count = sum(1 for t in results if t.get("conversion", {}).get("hint_applied"))
    
    output = {
        "_metadata": {
            "source": config["spec"]["name"],
            "extraction_date": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "total_tables": len(results),
            "converted": success,
            "failed": len(results) - success,
            "multi_page_tables": multi_count,
            "hint_applied_count": hint_count,
            "llm_stats": llm.stats
        },
        "tables": results
    }
    
    save_json(output, output_path)
    print(f"  Tables: {success}/{len(results)} converted ({multi_count} multi-page, {hint_count} with hints)")


def _convert_table_to_csv(llm: LLMClient, table: dict,
                          image_data: bytes,
                          hint: Optional[dict] = None) -> tuple:
    """Convert a table image to CSV using LLM vision.
    
    Args:
        hint: Optional extraction hint from config (expected_columns, instruction)
    
    Returns:
        (csv_text, abstract)
    """
    system_prompt, user_prompt = _build_prompt(table, hint)
    
    response = llm.call_with_image(
        system_prompt,
        user_prompt,
        image_data,
        max_tokens=4096
    )
    
    # Parse CSV from response
    csv_match = re.search(r'```csv\s*\n(.*?)```', response, re.DOTALL)
    if csv_match:
        csv_text = csv_match.group(1).strip()
    else:
        csv_text = response.strip()
    
    # Parse abstract
    abstract_match = re.search(r'ABSTRACT:\s*(.+)', response)
    abstract = abstract_match.group(1).strip() if abstract_match else ""
    
    return csv_text, abstract


# =============================================================================
# MULTI-PAGE DETECTION HELPERS
# =============================================================================

def _build_definition_page_set(tables: List[dict]) -> Set[int]:
    """Build set of 1-indexed PDF pages that are definition pages for any table."""
    return {t["definition_page"] for t in tables}


def _detect_table_pages(table: dict, tables: List[dict],
                        doc, multi_cfg: dict) -> List[int]:
    """Detect all PDF pages (0-indexed) belonging to this table.
    
    Scans backward/forward from definition_page, stopping when:
    - Another table's definition page is hit
    - The page has no table-like content
    - max_pages_before/after limit is reached
    
    Returns sorted list of 0-indexed PDF page indices.
    """
    def_page_1 = table["definition_page"]  # 1-indexed
    def_page_0 = def_page_1 - 1             # 0-indexed
    all_def_pages = _build_definition_page_set(tables)
    pages = [def_page_0]
    
    if not multi_cfg.get("enabled", False):
        return pages
    
    max_before = multi_cfg.get("max_pages_before", 2)
    max_after = multi_cfg.get("max_pages_after", 2)
    
    # Scan backward
    for offset in range(1, max_before + 1):
        candidate_1 = def_page_1 - offset
        candidate_0 = candidate_1 - 1
        if candidate_0 < 0:
            break
        if candidate_1 in all_def_pages:
            break
        text = get_page_text(doc, candidate_0)
        if not _looks_like_table_continuation(text, table):
            break
        pages.append(candidate_0)
    
    # Scan forward
    for offset in range(1, max_after + 1):
        candidate_1 = def_page_1 + offset
        candidate_0 = candidate_1 - 1
        if candidate_0 >= len(doc):
            break
        if candidate_1 in all_def_pages:
            break
        text = get_page_text(doc, candidate_0)
        if not _looks_like_table_continuation(text, table):
            break
        pages.append(candidate_0)
    
    return sorted(set(pages))


def _looks_like_table_continuation(page_text: str, table: dict) -> bool:
    """Heuristic: does this page look like a table continuation?
    
    Checks for:
    - Enough text lines (> 5)
    - No figure captions (would indicate a diagram page, not table data)
    - No different table title heading
    - No new section heading (e.g. '2.2.10 Host Control 1 Register')
    - Some tabular content patterns
    """
    lines = [l.strip() for l in page_text.split('\n') if l.strip()]
    if len(lines) < 5:
        return False
    
    # Reject pages with figure captions — they are NOT table continuations
    figure_re = re.compile(r'Figure\s+\d+-\d+\s*:', re.IGNORECASE)
    figure_count = sum(1 for l in lines if figure_re.search(l))
    if figure_count >= 1:
        return False
    
    # Reject pages starting a different section (e.g. "2.2.10 Host Control 1")
    section_re = re.compile(r'^\d+\.\d+\.\d+\s+', re.IGNORECASE)
    for line in lines[:8]:
        if section_re.match(line):
            return False
    
    # Check for a DIFFERENT table title on this page
    current_ref = table.get("spec_reference", "")
    table_title_re = re.compile(r'Table\s+\d+-\d+\s*:', re.IGNORECASE)
    for line in lines[:10]:
        m = table_title_re.search(line)
        if m and current_ref and current_ref.lower() not in line.lower():
            return False
    
    # Check for tabular content (lines with 3+ whitespace-separated tokens)
    tabular = sum(1 for l in lines if len(l.split()) >= 3)
    return tabular >= 3


# =============================================================================
# PROMPT BUILDING
# =============================================================================

def _build_prompt(table: dict, hint: Optional[dict]) -> tuple:
    """Build system + user prompts, injecting config hints when available.
    
    Returns (system_prompt, user_prompt).
    """
    base = (
        'You are a table extraction specialist. Given an image of page(s) '
        'from a hardware specification PDF:\n\n'
        '1. Find the table titled (approximately): "{title}"\n'
        '2. Extract it as clean CSV\n'
        '3. Provide a 1-sentence abstract\n\n'
        'Rules:\n'
        '- Use comma as delimiter\n'
        '- Quote fields containing commas\n'
        '- Preserve all data accurately\n'
        '- Include column headers as first row'
    )
    
    if hint:
        instruction = hint.get("instruction", "")
        if instruction:
            base += f"\n\nSPECIAL INSTRUCTIONS:\n{instruction}"
    
    base += (
        '\n\nRespond in this exact format:\n'
        '```csv\n'
        'CSV content here\n'
        '```\n\n'
        'ABSTRACT: one-sentence description'
    )
    
    system_prompt = base.format(title=table["title"])
    
    user_prompt = f"Extract table '{table['spec_reference']}' ({table['title']}) from this page image."
    if hint:
        col_names = [col.get("names", [""])[0] for col in hint.get("expected_columns", [])]
        if col_names:
            user_prompt += f"\nExpected columns: {', '.join(col_names)}"
    
    return system_prompt, user_prompt
