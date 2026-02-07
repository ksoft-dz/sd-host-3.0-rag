#!/usr/bin/env python3
"""
Extract sections and chunks from SD Host 3.0 PDF specification.

This script:
1. Extracts ToC/section structure from PDF
2. Processes page-by-page to extract text chunks
3. Uses LLM (Claude Haiku) to identify chunk boundaries and generate abstracts
4. Builds sections.json with hierarchical structure

Usage:
    python extract_sections.py [--skip-existing] [--start-page N] [--end-page N] [--workers N]
"""

import json
import re
import os
import sys
import argparse
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from typing import Optional
import fitz  # PyMuPDF

# Add parent to path for shared utilities
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import anthropic
except ImportError:
    print("ERROR: anthropic package not installed. Run: pip install anthropic")
    sys.exit(1)


# =============================================================================
# CONFIGURATION
# =============================================================================

WORKSPACE_ROOT = Path(__file__).parent.parent
PDF_PATH = WORKSPACE_ROOT / "source" / "sd_host_3_00.pdf"
TABLES_MAP_PATH = WORKSPACE_ROOT / "tables" / "tables_page_map.json"
FIGURES_MAP_PATH = WORKSPACE_ROOT / "figures" / "figures_page_map.json"
OUTPUT_PATH = WORKSPACE_ROOT / "spec" / "sections.json"
TOC_RAW_PATH = WORKSPACE_ROOT / "spec" / "toc_raw.json"

PAGE_OFFSET = 11  # spec_page + PAGE_OFFSET = pdf_page (0-indexed: pdf_page - 1)
CHUNK_TARGET_WORDS = 200
CHUNK_MAX_WORDS = 250  # Hard limit - split at paragraph boundaries if exceeded
MAX_RETRIES = 3
DEFAULT_WORKERS = 4  # Default number of parallel workers
RATE_LIMIT_DELAY = 1.5  # Delay between requests in parallel mode to avoid 429 errors

# Claude model selection
MODEL_HAIKU = "claude-haiku-4-5-20251001"    # Fastest/cheapest
MODEL_SONNET = "claude-sonnet-4-5-20250929"  # Balanced (default)
MODEL_OPUS = "claude-opus-4-5-20251101"      # Most capable

MODELS = {
    "haiku": MODEL_HAIKU,
    "sonnet": MODEL_SONNET,
    "opus": MODEL_OPUS
}

DEFAULT_MODEL = "sonnet"
LLM_MODEL = MODELS[DEFAULT_MODEL]  # Will be updated by --model argument


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Chunk:
    chunk_id: str
    chunk_index: int
    spec_page: int = 0
    word_count: int = 0
    abstract: str = ""
    raw: str = ""


@dataclass
class Section:
    id: str
    section_number: str
    title: str
    level: int
    hierarchy: dict = field(default_factory=lambda: {"parent": None, "children": []})
    source: dict = field(default_factory=lambda: {
        "spec_page_start": 0, "spec_page_end": 0,
        "pdf_page_start": 0, "pdf_page_end": 0
    })
    references: dict = field(default_factory=lambda: {"tables": [], "figures": [], "related": []})
    index: dict = field(default_factory=lambda: {"keywords": [], "technical_terms": []})
    abstract: str = ""
    word_count: int = 0
    chunks: list = field(default_factory=list)
    extraction: dict = field(default_factory=lambda: {
        "status": "NOT_STARTED", "confidence": 0.0, "validated": False
    })


# =============================================================================
# UTILITIES
# =============================================================================

def load_json(path: Path) -> dict:
    """Load JSON file."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(data: dict, path: Path):
    """Save JSON file with pretty printing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Saved: {path}")


def get_pages_with_chunks(sections_data: dict) -> set:
    """Get set of spec pages that have chunks extracted."""
    pages_with_chunks = set()
    for sec_num, section in sections_data.get("sections", {}).items():
        for chunk in section.get("chunks", []):
            spec_page = chunk.get("spec_page", 0)
            if spec_page > 0:
                pages_with_chunks.add(spec_page)
    return pages_with_chunks


def get_missing_pages(total_spec_pages: int, pages_with_chunks: set, page_offset: int) -> list:
    """Get list of PDF pages (1-indexed) that don't have chunks."""
    missing_pdf_pages = []
    for spec_page in range(1, total_spec_pages + 1):
        if spec_page not in pages_with_chunks:
            pdf_page = spec_page + page_offset
            missing_pdf_pages.append(pdf_page)
    return missing_pdf_pages


def _load_existing_chunks(sections_data: dict) -> dict:
    """Load existing chunks from sections.json into process_pages format."""
    all_chunks = {}
    for sec_num, section in sections_data.get("sections", {}).items():
        for chunk in section.get("chunks", []):
            if sec_num not in all_chunks:
                all_chunks[sec_num] = []
            all_chunks[sec_num].append({
                "text": chunk.get("raw", ""),
                "is_complete": True,
                "pdf_page": chunk.get("spec_page", 0) + PAGE_OFFSET,
                "spec_page": chunk.get("spec_page", 0),
                "abstract": chunk.get("abstract", "")
            })
    return all_chunks


def section_number_to_id(section_num: str) -> str:
    """Convert section number to ID format: '2.1.3' -> 'SEC_2_1_3', 'A.1' -> 'SEC_A_1'"""
    # Handle appendix format
    if section_num.startswith("Appendix_"):
        return "SEC_" + section_num.replace("Appendix_", "")
    return "SEC_" + section_num.replace(".", "_")


def id_to_section_number(section_id: str) -> str:
    """Convert ID to section number: 'SEC_2_1_3' -> '2.1.3', 'SEC_A_1' -> 'A.1'"""
    return section_id.replace("SEC_", "").replace("_", ".")


def get_section_level(section_num: str) -> int:
    """Get section depth level: '2.1.3' -> 3, 'A.1' -> 2, 'Appendix_A' -> 1"""
    if section_num.startswith("Appendix_"):
        return 1  # Top-level appendix
    return len(section_num.split("."))


def get_parent_section(section_num: str) -> Optional[str]:
    """Get parent section number: '2.1.3' -> '2.1', '2' -> None, 'A.1' -> 'Appendix_A'"""
    # Handle appendix subsections like "A.1" -> "Appendix_A"
    if re.match(r'^[A-Z]\.\d', section_num):
        return f"Appendix_{section_num[0]}"
    # Handle deeper appendix subsections like "C.3.2" -> "C.3"
    if re.match(r'^[A-Z]\.', section_num):
        parts = section_num.split(".")
        if len(parts) > 2:
            return ".".join(parts[:-1])
        return f"Appendix_{section_num[0]}"
    # Handle top-level appendix
    if section_num.startswith("Appendix_"):
        return None
    # Regular sections
    parts = section_num.split(".")
    if len(parts) <= 1:
        return None
    return ".".join(parts[:-1])


def section_sort_key(sec_num: str) -> list:
    """Generate sort key for section numbers, handling appendices."""
    # Handle appendix sections - sort after numeric sections
    if sec_num.startswith("Appendix_"):
        # Appendix_A -> (1000, ord('A'), 0, 0, ...)
        letter = sec_num.replace("Appendix_", "")
        return [1000, ord(letter)] + [0] * 10
    # Handle appendix subsections like "A.1", "C.3.2"
    if re.match(r'^[A-Z]\.', sec_num):
        parts = sec_num.split(".")
        letter = parts[0]
        nums = [int(p) for p in parts[1:]]
        return [1000, ord(letter)] + nums + [0] * (10 - len(nums))
    # Regular numeric sections
    parts = sec_num.split(".")
    nums = [int(p) for p in parts]
    return nums + [0] * (10 - len(nums))


def count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def clean_text(text: str) -> str:
    """Clean extracted text."""
    # Remove excessive whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    # Remove page headers/footers patterns (customize as needed)
    text = re.sub(r'SD Host Controller Simplified Specification Version \d+\.\d+', '', text)
    text = re.sub(r'©\s*\d{4}.*?reserved\.?', '', text, flags=re.IGNORECASE)
    return text.strip()


# =============================================================================
# PDF EXTRACTION
# =============================================================================

def extract_page_text(doc: fitz.Document, pdf_page: int) -> str:
    """Extract text from a single PDF page."""
    if pdf_page < 0 or pdf_page >= len(doc):
        return ""
    page = doc[pdf_page]
    text = page.get_text("text")
    return clean_text(text)


def get_pages_with_tables(tables_map: dict) -> dict:
    """Get mapping of PDF pages to table IDs."""
    pages = {}
    for table in tables_map.get("tables", []):
        pdf_page = table.get("definition_page", 0)
        if pdf_page > 0:
            if pdf_page not in pages:
                pages[pdf_page] = []
            pages[pdf_page].append(table["id"])
    return pages


def get_pages_with_figures(figures_map: dict) -> dict:
    """Get mapping of PDF pages to figure IDs."""
    pages = {}
    for figure in figures_map.get("figures", []):
        pdf_page = figure.get("definition_page", 0)
        if pdf_page > 0:
            if pdf_page not in pages:
                pages[pdf_page] = []
            pages[pdf_page].append(figure["id"])
    return pages


# =============================================================================
# SECTION HEADER DETECTION
# =============================================================================

# Pattern to match section headers like "1. Overview" or "2.1.3 Power Control Register"
# Format 1: "X. Title" (top-level with period)
# Format 2: "X.Y Title" or "X.Y.Z Title" (subsections)
SECTION_HEADER_PATTERN = re.compile(
    r'^([1-9]\d*(?:\.\d+)+)\s+([A-Z][a-zA-Z0-9][^\n]{3,80})$',  # X.Y or X.Y.Z format
    re.MULTILINE
)

# Pattern for top-level sections "1. Title" or "2. Title" (with period after number)
TOP_LEVEL_SECTION_PATTERN = re.compile(
    r'^([1-9])\.\s+([A-Z][^\n]{5,80})$',  # "1. Title" format (min 6 chars total)
    re.MULTILINE
)

# Pattern for appendix headers "Appendix A (Normative) : Title" or "Appendix A : Title"
APPENDIX_HEADER_PATTERN = re.compile(
    r'^Appendix\s+([A-Z])\s*(?:\([^)]+\))?\s*[:\-]?\s*(.*)$',  # "Appendix A : Title"
    re.MULTILINE
)

# Pattern for appendix subsections "A.1 Title", "C.3.2 Title"
APPENDIX_SUBSECTION_PATTERN = re.compile(
    r'^([A-Z](?:\.\d+)+)\s+([A-Z][^\n]{3,80})$',  # "A.1 Title" or "C.3.2 Title"
    re.MULTILINE
)


def detect_section_headers(text: str) -> list[tuple[str, str, int]]:
    """
    Detect section headers in text.
    Returns list of (section_number, title, char_position).
    """
    headers = []
    
    # Match subsection headers (X.Y, X.Y.Z, etc.)
    for match in SECTION_HEADER_PATTERN.finditer(text):
        section_num = match.group(1)
        title = match.group(2).strip()
        position = match.start()
        
        # Filter out likely false positives
        if len(title) < 5:
            continue
        if title.lower().startswith(('figure', 'table', 'note')):
            continue
        # Filter version numbers like "1.00", "2.00" (from revision history)
        if re.match(r'^\d+\.0+$', section_num):
            continue
        # Filter lines that look like revision history entries
        if 'release' in title.lower() or 'specification' in title.lower():
            continue
            
        headers.append((section_num, title, position))
    
    # Match top-level sections "1. Title" format
    for match in TOP_LEVEL_SECTION_PATTERN.finditer(text):
        section_num = match.group(1)
        title = match.group(2).strip()
        position = match.start()
        
        # Filter revision history
        if 'release' in title.lower() or 'specification' in title.lower():
            continue
            
        headers.append((section_num, title, position))
    
    # Match appendix headers "Appendix A : Title"
    for match in APPENDIX_HEADER_PATTERN.finditer(text):
        section_num = match.group(1)  # Just the letter: "A", "B", etc.
        title = match.group(2).strip() if match.group(2) else ""
        position = match.start()
        
        # Filter ToC entries (contain dots like "....137")
        if '...' in title or re.search(r'\.{2,}', title):
            continue
        
        # Use full "Appendix X" format for the section number
        section_num = f"Appendix_{section_num}"
        if not title:
            title = f"Appendix {match.group(1)}"
            
        headers.append((section_num, title, position))
    
    # Match appendix subsections "A.1 Title", "C.3.2 Title"
    for match in APPENDIX_SUBSECTION_PATTERN.finditer(text):
        section_num = match.group(1)  # "A.1", "C.3.2", etc.
        title = match.group(2).strip()
        position = match.start()
        
        # Filter out likely false positives
        if len(title) < 5:
            continue
        if title.lower().startswith(('figure', 'table', 'note')):
            continue
            
        headers.append((section_num, title, position))
    
    return headers


# =============================================================================
# LLM INTERACTION
# =============================================================================

def get_anthropic_client():
    """Get Anthropic client with API key from environment."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        # Try loading from .env or config
        env_file = WORKSPACE_ROOT / ".env"
        if env_file.exists():
            with open(env_file) as f:
                for line in f:
                    if line.startswith("ANTHROPIC_API_KEY="):
                        api_key = line.split("=", 1)[1].strip().strip('"\'')
                        break
    
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY not found. Set it in environment or .env file."
        )
    
    return anthropic.Anthropic(api_key=api_key)


def build_chunk_extraction_prompt(
    page_text: str,
    pdf_page: int,
    spec_page: int,
    detected_sections: list[tuple[str, str, int]],
    tables_on_page: list[str],
    figures_on_page: list[str],
    previous_context: Optional[dict] = None
) -> str:
    """Build the prompt for chunk extraction."""
    
    sections_info = ""
    if detected_sections:
        sections_info = "Detected section headers on this page:\n"
        for sec_num, title, pos in detected_sections:
            sections_info += f"  - Section {sec_num}: {title}\n"
    else:
        sections_info = "No new section headers detected on this page.\n"
    
    tables_info = ""
    if tables_on_page:
        tables_info = f"Tables on this page (EXCLUDE from chunks): {', '.join(tables_on_page)}\n"
    
    figures_info = ""
    if figures_on_page:
        figures_info = f"Figures on this page (EXCLUDE from chunks): {', '.join(figures_on_page)}\n"
    
    context_info = ""
    if previous_context:
        context_info = f"""
Previous page context:
- Last section: {previous_context.get('last_section', 'unknown')}
- Incomplete chunk continues: {previous_context.get('continues', False)}
"""

    prompt = f"""You are extracting structured text chunks from a technical specification PDF.

TASK: Extract text chunks from page {pdf_page} (spec page {spec_page}) of the SD Host Controller specification.

{sections_info}
{tables_info}
{figures_info}
{context_info}

STRICT RULES - VIOLATION IS FAILURE:
1. VERBATIM EXTRACTION: Copy text EXACTLY as it appears - character for character
2. NO TRUNCATION: Extract ALL paragraphs of each section - missing even ONE sentence is FAILURE
3. NO SUMMARIZATION: Do NOT condense, paraphrase, or rewrite ANY content
4. NO HALLUCINATION: Do NOT add words that are not in the source text
5. COMPLETE SECTIONS: Every section on the page must have ALL its paragraphs extracted
6. EXCLUDE ONLY: Table data, figure captions, page headers/footers, page numbers
7. Section boundaries: A chunk must NEVER span across section boundaries
8. HARD WORD LIMIT: Maximum 250 words per chunk - NO EXCEPTIONS
   - If section content exceeds 250 words, SPLIT into multiple chunks
   - Split at paragraph boundaries (numbered items like (1), (2), (3) are good split points)
   - Each chunk gets the SAME section number
   - Example: Section 1.7.1 with 450 words = 2 chunks, both with section "1.7.1"

VALIDATION CHECK:
- Count the paragraphs in each section in PAGE TEXT
- Your extracted text MUST contain the same number of paragraphs across all chunks
- If section 1.4 has 4 paragraphs, your chunks for 1.4 MUST have 4 paragraphs total
- Count words in each chunk - if ANY chunk exceeds 250 words, SPLIT IT

PAGE TEXT:
---
{page_text}
---

Respond with ONLY valid JSON in this exact format:
{{
  "chunks": [
    {{
      "section": "2.1.3",
      "text": "The actual extracted text content...",
      "is_complete": true,
      "notes": "optional notes about this chunk"
    }}
  ],
  "page_has_content": true,
  "continues_to_next_page": false,
  "last_section": "2.1.3"
}}

If page has no extractable text content (only tables/figures):
{{
  "chunks": [],
  "page_has_content": false,
  "continues_to_next_page": false,
  "last_section": null
}}

CRITICAL REMINDERS:
- "is_complete": false means the chunk continues on the next page
- "section" must be a valid section number like "1", "2.1", "2.1.3"
- Do NOT include table content even if it appears as text
- Do NOT include figure labels/captions in chunk text
- EVERY PARAGRAPH from the source MUST appear in output - NO EXCEPTIONS
- If you truncate or summarize, the extraction is INVALID
- HARD LIMIT 250 WORDS: Count words BEFORE outputting each chunk. If >250, SPLIT IT.
- Split long paragraphs at sentence boundaries if needed to stay under 250 words

Respond with JSON only, no additional text:"""

    return prompt


def build_abstract_generation_prompt(chunk_text: str, section_title: str) -> str:
    """Build prompt for abstract generation."""
    return f"""Generate a concise 1-2 sentence abstract for this technical specification text.

Section: {section_title}

Text:
{chunk_text}

Requirements:
- Maximum 50 words
- Capture the key technical information
- Be specific, not generic
- Use technical terminology appropriately

Respond with ONLY the abstract text, nothing else:"""


def build_keywords_prompt(section_text: str, section_title: str) -> str:
    """Build prompt for keywords extraction."""
    return f"""Extract keywords and technical terms from this specification section.

Section: {section_title}

Text:
{section_text[:2000]}  # Limit context

Respond with ONLY valid JSON:
{{
  "keywords": ["general", "searchable", "terms"],
  "technical_terms": ["Register Name", "offset 029h", "specific acronyms"]
}}

Guidelines:
- keywords: General concepts, actions, topics (lowercase)
- technical_terms: Exact terms from spec - register names, offsets, bit fields, acronyms (preserve case)

JSON only:"""


def call_llm(client, prompt: str, model: str = None, max_retries: int = MAX_RETRIES) -> str:
    """Call LLM with retry logic and rate limit handling."""
    model_name = model or LLM_MODEL
    for attempt in range(max_retries + 1):
        try:
            response = client.messages.create(
                model=model_name,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text.strip()
        except anthropic.RateLimitError as e:
            # Rate limit - use longer backoff
            wait_time = min(60, (2 ** attempt) * 5)  # 5s, 10s, 20s, 40s, max 60s
            if attempt < max_retries:
                print(f"  Rate limit hit (attempt {attempt + 1}), waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise
        except Exception as e:
            if attempt < max_retries:
                print(f"  LLM call failed (attempt {attempt + 1}): {e}")
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                raise


def parse_chunk_response(response: str, pdf_page: int) -> Optional[dict]:
    """Parse and validate LLM chunk extraction response."""
    # Try to extract JSON from response
    try:
        # Handle potential markdown code blocks
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            response = response.split("```")[1].split("```")[0]
        
        data = json.loads(response.strip())
        
        # Validate structure
        if "chunks" not in data:
            return None
        
        if not isinstance(data["chunks"], list):
            return None
        
        # Validate each chunk
        for chunk in data["chunks"]:
            if "section" not in chunk or "text" not in chunk:
                return None
            # Validate section format (numeric or appendix)
            if not re.match(r'^(\d+(\.\d+)*|Appendix_[A-Z]|[A-Z](\.\d+)*)$', chunk["section"]):
                print(f"  Invalid section format: {chunk['section']}")
                return None
            # Check word count - warn but don't reject
            word_count = count_words(chunk["text"])
            if word_count > CHUNK_MAX_WORDS:
                print(f"  WARNING: Chunk for section {chunk['section']} has {word_count} words (max {CHUNK_MAX_WORDS})")
        
        return data
        
    except json.JSONDecodeError as e:
        print(f"  JSON parse error on page {pdf_page}: {e}")
        return None


def extract_chunks_from_page(
    client,
    page_text: str,
    pdf_page: int,
    spec_page: int,
    detected_sections: list,
    tables_on_page: list,
    figures_on_page: list,
    previous_context: Optional[dict] = None
) -> Optional[dict]:
    """Extract chunks from a single page using LLM."""
    
    prompt = build_chunk_extraction_prompt(
        page_text, pdf_page, spec_page,
        detected_sections, tables_on_page, figures_on_page,
        previous_context
    )
    
    for attempt in range(MAX_RETRIES + 1):
        response = call_llm(client, prompt)
        result = parse_chunk_response(response, pdf_page)
        
        if result is not None:
            return result
        
        if attempt < MAX_RETRIES:
            # Add feedback for retry
            feedback = f"""
Your previous response was not valid JSON or had structural issues.

Expected format:
{{
  "chunks": [
    {{"section": "X.Y.Z", "text": "...", "is_complete": true/false, "notes": ""}}
  ],
  "page_has_content": true/false,
  "continues_to_next_page": true/false,
  "last_section": "X.Y.Z" or null
}}

Please try again with valid JSON only:"""
            prompt = prompt + feedback
            print(f"  Retrying page {pdf_page} (attempt {attempt + 2})...")
    
    return None


# =============================================================================
# MAIN EXTRACTION PIPELINE
# =============================================================================

def extract_toc_structure(doc: fitz.Document) -> dict:
    """
    Extract table of contents / section structure from PDF.
    Returns dict with section hierarchy.
    """
    print("Extracting ToC structure...")
    
    sections = {}
    all_headers = []
    
    # Scan all pages for section headers
    for pdf_page in range(len(doc)):
        text = extract_page_text(doc, pdf_page)
        headers = detect_section_headers(text)
        
        for sec_num, title, pos in headers:
            spec_page = pdf_page - PAGE_OFFSET + 1
            all_headers.append({
                "section_number": sec_num,
                "title": title,
                "pdf_page": pdf_page + 1,  # 1-indexed for display
                "spec_page": spec_page
            })
    
    # Remove duplicates (same section found on multiple pages = keep first)
    seen = set()
    unique_headers = []
    for h in all_headers:
        if h["section_number"] not in seen:
            seen.add(h["section_number"])
            unique_headers.append(h)
    
    # Sort by section number
    unique_headers.sort(key=lambda h: section_sort_key(h["section_number"]))
    
    # Build section objects
    for h in unique_headers:
        sec_num = h["section_number"]
        sec_id = section_number_to_id(sec_num)
        parent_num = get_parent_section(sec_num)
        parent_id = section_number_to_id(parent_num) if parent_num else None
        
        section = Section(
            id=sec_id,
            section_number=sec_num,
            title=h["title"],
            level=get_section_level(sec_num),
            hierarchy={"parent": parent_id, "children": []},
            source={
                "spec_page_start": h["spec_page"],
                "spec_page_end": h["spec_page"],  # Will be updated
                "pdf_page_start": h["pdf_page"],
                "pdf_page_end": h["pdf_page"]  # Will be updated
            }
        )
        sections[sec_num] = section
    
    # Build parent-child relationships
    for sec_num, section in sections.items():
        parent_num = get_parent_section(sec_num)
        if parent_num and parent_num in sections:
            sections[parent_num].hierarchy["children"].append(section.id)
    
    # Calculate page ranges (each section ends where next sibling/uncle starts)
    sorted_nums = sorted(sections.keys(), key=section_sort_key)
    for i, sec_num in enumerate(sorted_nums):
        if i + 1 < len(sorted_nums):
            next_sec = sorted_nums[i + 1]
            next_page = sections[next_sec].source["pdf_page_start"]
            sections[sec_num].source["pdf_page_end"] = next_page
            sections[sec_num].source["spec_page_end"] = next_page - PAGE_OFFSET
    
    print(f"  Found {len(sections)} sections")
    
    return {
        "headers": unique_headers,
        "sections": sections
    }


def process_single_page(
    client,
    doc: fitz.Document,
    pdf_page: int,
    tables_by_page: dict,
    figures_by_page: dict
) -> Optional[dict]:
    """
    Process a single PDF page to extract chunks.
    Returns dict with page info and chunks, or None if failed.
    """
    pdf_page_0idx = pdf_page - 1
    spec_page = pdf_page - PAGE_OFFSET
    
    # Skip cover pages, ToC, etc.
    if spec_page < 1:
        return {"pdf_page": pdf_page, "spec_page": spec_page, "skipped": True, "reason": "cover/toc"}
    
    # Get page text
    page_text = extract_page_text(doc, pdf_page_0idx)
    
    if not page_text or len(page_text.strip()) < 50:
        return {"pdf_page": pdf_page, "spec_page": spec_page, "skipped": True, "reason": "no content"}
    
    # Detect section headers on this page
    detected_sections = detect_section_headers(page_text)
    
    # Get tables/figures on this page
    tables_on_page = tables_by_page.get(pdf_page, [])
    figures_on_page = figures_by_page.get(pdf_page, [])
    
    # Extract chunks via LLM (no previous context in parallel mode)
    result = extract_chunks_from_page(
        client,
        page_text,
        pdf_page,
        spec_page,
        detected_sections,
        tables_on_page,
        figures_on_page,
        None  # No context in parallel mode
    )
    
    if result is None:
        return {"pdf_page": pdf_page, "spec_page": spec_page, "skipped": True, "reason": "LLM error"}
    
    if not result.get("page_has_content", True):
        return {"pdf_page": pdf_page, "spec_page": spec_page, "skipped": True, "reason": "only tables/figures"}
    
    return {
        "pdf_page": pdf_page,
        "spec_page": spec_page,
        "skipped": False,
        "chunks": result.get("chunks", []),
        "continues_to_next_page": result.get("continues_to_next_page", False),
        "last_section": result.get("last_section")
    }


def process_pages(
    client,
    doc: fitz.Document,
    toc_data: dict,
    tables_map: dict,
    figures_map: dict,
    start_page: int = 1,
    end_page: Optional[int] = None,
    num_workers: int = DEFAULT_WORKERS,
    specific_pages: Optional[list] = None
) -> dict:
    """
    Process PDF pages to extract chunks with parallel workers.
    
    Args:
        specific_pages: Optional list of specific PDF page numbers (1-indexed) to process.
                       If provided, start_page and end_page are ignored.
    """
    tables_by_page = get_pages_with_tables(tables_map)
    figures_by_page = get_pages_with_figures(figures_map)
    
    if end_page is None:
        end_page = len(doc)
    
    # Build list of pages to process
    if specific_pages is not None:
        # Use specific pages list (filter valid pages)
        pages_to_process = [p for p in specific_pages if PAGE_OFFSET < p <= len(doc)]
    else:
        # Use page range
        pages_to_process = []
        for pdf_page in range(start_page, min(end_page + 1, len(doc) + 1)):
            spec_page = pdf_page - PAGE_OFFSET
            if spec_page >= 1:  # Skip cover/ToC
                pages_to_process.append(pdf_page)
    
    total_pages = len(pages_to_process)
    if total_pages == 0:
        print("No pages to process.")
        return {}
    
    print(f"Processing {total_pages} pages with {num_workers} workers...")
    
    # Process pages in parallel
    page_results = {}  # pdf_page -> result
    
    if num_workers == 1:
        # Sequential processing (original behavior for debugging)
        for pdf_page in pages_to_process:
            result = process_single_page(client, doc, pdf_page, tables_by_page, figures_by_page)
            page_results[pdf_page] = result
            spec_page = pdf_page - PAGE_OFFSET
            if result.get("skipped"):
                print(f"  Page {pdf_page} (spec {spec_page})... skipped ({result.get('reason', 'unknown')})")
            else:
                print(f"  Page {pdf_page} (spec {spec_page})... {len(result.get('chunks', []))} chunk(s)")
            time.sleep(0.3)  # Rate limiting
    else:
        # Parallel processing with rate limiting
        # Process in batches to avoid hitting rate limits (50 req/min = ~0.83 req/sec)
        # With retries each page may need 2-3 requests, so limit to ~15-20 pages per minute
        batch_size = min(num_workers * 2, 16)  # Process in small batches
        completed = 0
        
        for batch_start in range(0, len(pages_to_process), batch_size):
            batch_pages = pages_to_process[batch_start:batch_start + batch_size]
            batch_start_time = time.time()
            
            with ThreadPoolExecutor(max_workers=num_workers) as executor:
                # Submit batch
                future_to_page = {
                    executor.submit(process_single_page, client, doc, pdf_page, tables_by_page, figures_by_page): pdf_page
                    for pdf_page in batch_pages
                }
                
                # Collect results as they complete
                for future in as_completed(future_to_page):
                    pdf_page = future_to_page[future]
                    completed += 1
                    try:
                        result = future.result()
                        page_results[pdf_page] = result
                        spec_page = pdf_page - PAGE_OFFSET
                        if result.get("skipped"):
                            print(f"  [{completed}/{total_pages}] Page {pdf_page} (spec {spec_page})... skipped ({result.get('reason', 'unknown')})")
                        else:
                            print(f"  [{completed}/{total_pages}] Page {pdf_page} (spec {spec_page})... {len(result.get('chunks', []))} chunk(s)")
                    except Exception as e:
                        print(f"  [{completed}/{total_pages}] Page {pdf_page}... ERROR: {e}")
                        page_results[pdf_page] = {"pdf_page": pdf_page, "skipped": True, "reason": str(e)}
            
            # Rate limit between batches - ensure at least 2 seconds per batch to stay under 50 req/min
            elapsed = time.time() - batch_start_time
            min_batch_time = len(batch_pages) * RATE_LIMIT_DELAY
            if elapsed < min_batch_time and batch_start + batch_size < len(pages_to_process):
                sleep_time = min_batch_time - elapsed
                print(f"  [Rate limiting: waiting {sleep_time:.1f}s before next batch]")
                time.sleep(sleep_time)
    
    # Merge results in page order
    all_chunks = {}  # section_number -> list of chunks
    
    for pdf_page in sorted(page_results.keys()):
        result = page_results[pdf_page]
        if result.get("skipped"):
            continue
        
        spec_page = result.get("spec_page", pdf_page - PAGE_OFFSET)
        
        for chunk_data in result.get("chunks", []):
            sec_num = chunk_data["section"]
            text = chunk_data["text"].strip()
            
            if not text:
                continue
            
            if sec_num not in all_chunks:
                all_chunks[sec_num] = []
            
            all_chunks[sec_num].append({
                "text": text,
                "is_complete": chunk_data.get("is_complete", True),
                "pdf_page": pdf_page,
                "spec_page": spec_page
            })
    
    return all_chunks


def _generate_abstract_for_chunk(client, chunk_data: dict, section_title: str) -> str:
    """Generate abstract for a single chunk."""
    try:
        abstract_prompt = build_abstract_generation_prompt(chunk_data["text"], section_title)
        abstract = call_llm(client, abstract_prompt)
        return abstract.strip()
    except Exception as e:
        return ""


def _generate_keywords_for_section(client, section, full_text: str) -> tuple:
    """Generate keywords for a section. Returns (keywords, technical_terms)."""
    try:
        keywords_prompt = build_keywords_prompt(full_text, section.title)
        keywords_response = call_llm(client, keywords_prompt)
        
        # Parse keywords JSON
        if "```" in keywords_response:
            keywords_response = keywords_response.split("```")[1]
            if keywords_response.startswith("json"):
                keywords_response = keywords_response[4:]
            keywords_response = keywords_response.split("```")[0]
        
        keywords_data = json.loads(keywords_response.strip())
        return (keywords_data.get("keywords", []), keywords_data.get("technical_terms", []))
    except Exception:
        return ([], [])


def generate_abstracts_and_keywords(
    client,
    sections: dict,
    all_chunks: dict,
    num_workers: int = DEFAULT_WORKERS
) -> None:
    """Generate abstracts and keywords for chunks using LLM with parallel workers."""
    
    print("\nGenerating abstracts and keywords...")
    
    # Build list of tasks: (sec_num, chunk_index, chunk_data, section_title)
    chunk_tasks = []
    for sec_num, chunks in all_chunks.items():
        section = sections.get(sec_num)
        section_title = section.title if section else sec_num
        for i, chunk_data in enumerate(chunks):
            chunk_tasks.append((sec_num, i, chunk_data, section_title))
    
    total_chunks = len(chunk_tasks)
    print(f"  Processing {total_chunks} chunk abstracts with {num_workers} workers...")
    
    if num_workers == 1:
        # Sequential
        for idx, (sec_num, i, chunk_data, section_title) in enumerate(chunk_tasks):
            print(f"  [{idx+1}/{total_chunks}] {sec_num} chunk {i}...", end=" ")
            chunk_data["abstract"] = _generate_abstract_for_chunk(client, chunk_data, section_title)
            print("done" if chunk_data["abstract"] else "failed")
            time.sleep(0.2)
    else:
        # Parallel with batching to avoid rate limits
        batch_size = min(num_workers * 2, 16)
        completed = 0
        
        for batch_start in range(0, len(chunk_tasks), batch_size):
            batch = chunk_tasks[batch_start:batch_start + batch_size]
            batch_start_time = time.time()
            
            with ThreadPoolExecutor(max_workers=num_workers) as executor:
                future_to_task = {
                    executor.submit(_generate_abstract_for_chunk, client, chunk_data, section_title): (sec_num, i, chunk_data)
                    for sec_num, i, chunk_data, section_title in batch
                }
                
                for future in as_completed(future_to_task):
                    sec_num, i, chunk_data = future_to_task[future]
                    completed += 1
                    try:
                        chunk_data["abstract"] = future.result()
                        print(f"  [{completed}/{total_chunks}] {sec_num} chunk {i}... done")
                    except Exception as e:
                        chunk_data["abstract"] = ""
                        print(f"  [{completed}/{total_chunks}] {sec_num} chunk {i}... failed: {e}")
            
            # Rate limit between batches
            elapsed = time.time() - batch_start_time
            min_batch_time = len(batch) * RATE_LIMIT_DELAY
            if elapsed < min_batch_time and batch_start + batch_size < len(chunk_tasks):
                sleep_time = min_batch_time - elapsed
                print(f"  [Rate limiting: waiting {sleep_time:.1f}s before next batch]")
                time.sleep(sleep_time)
    
    # Generate section-level keywords (parallel)
    section_tasks = []
    for sec_num, chunks in all_chunks.items():
        section = sections.get(sec_num)
        if section:
            full_section_text = " ".join(c["text"] for c in chunks)
            if full_section_text:
                section_tasks.append((sec_num, section, full_section_text))
    
    print(f"  Processing {len(section_tasks)} section keywords with {num_workers} workers...")
    
    if num_workers == 1:
        for sec_num, section, full_text in section_tasks:
            keywords, terms = _generate_keywords_for_section(client, section, full_text)
            section.index["keywords"] = keywords
            section.index["technical_terms"] = terms
            time.sleep(0.2)
    else:
        # Parallel with batching
        batch_size = min(num_workers * 2, 16)
        completed = 0
        
        for batch_start in range(0, len(section_tasks), batch_size):
            batch = section_tasks[batch_start:batch_start + batch_size]
            batch_start_time = time.time()
            
            with ThreadPoolExecutor(max_workers=num_workers) as executor:
                future_to_section = {
                    executor.submit(_generate_keywords_for_section, client, section, full_text): (sec_num, section)
                    for sec_num, section, full_text in batch
                }
                
                for future in as_completed(future_to_section):
                    sec_num, section = future_to_section[future]
                    completed += 1
                    try:
                        keywords, terms = future.result()
                        section.index["keywords"] = keywords
                        section.index["technical_terms"] = terms
                    except Exception as e:
                        print(f"  Keywords failed for {sec_num}: {e}")
            
            # Rate limit between batches
            elapsed = time.time() - batch_start_time
            min_batch_time = len(batch) * RATE_LIMIT_DELAY
            if elapsed < min_batch_time and batch_start + batch_size < len(section_tasks):
                time.sleep(min_batch_time - elapsed)


def build_sections_json(
    toc_data: dict,
    all_chunks: dict,
    tables_map: dict,
    figures_map: dict
) -> dict:
    """Build the final sections.json structure."""
    
    print("\nBuilding sections.json...")
    
    sections = toc_data["sections"]
    tables_by_page = get_pages_with_tables(tables_map)
    figures_by_page = get_pages_with_figures(figures_map)
    
    # Convert chunks to final format and assign to sections
    total_chunks = 0
    
    for sec_num, section in sections.items():
        chunks_data = all_chunks.get(sec_num, [])
        
        section.chunks = []
        full_text = ""
        
        for i, chunk_data in enumerate(chunks_data):
            chunk_text = chunk_data["text"]
            chunk = Chunk(
                chunk_id=f"{section.id}_C{i}",
                chunk_index=i,
                spec_page=chunk_data.get("spec_page", 0),
                word_count=count_words(chunk_text),
                abstract=chunk_data.get("abstract", ""),
                raw=chunk_text
            )
            section.chunks.append(asdict(chunk))
            full_text += " " + chunk_text
            total_chunks += 1
        
        # Calculate word count
        section.word_count = count_words(full_text)
        
        # Generate section-level abstract (from first chunk or combined)
        if section.chunks:
            # Use first chunk's text for section abstract if not set
            if not section.abstract and section.chunks[0].get("abstract"):
                section.abstract = section.chunks[0]["abstract"]
        
        # Find table/figure references based on page range
        start_page = section.source.get("pdf_page_start", 0)
        end_page = section.source.get("pdf_page_end", start_page)
        
        for page in range(start_page, end_page + 1):
            section.references["tables"].extend(tables_by_page.get(page, []))
            section.references["figures"].extend(figures_by_page.get(page, []))
        
        # Remove duplicates
        section.references["tables"] = list(set(section.references["tables"]))
        section.references["figures"] = list(set(section.references["figures"]))
        
        # Update extraction status
        if section.chunks:
            section.extraction["status"] = "COMPLETED"
            section.extraction["confidence"] = 0.9
        else:
            section.extraction["status"] = "COMPLETED"
            section.extraction["confidence"] = 1.0  # Empty is valid for container sections
    
    # Build final output
    output = {
        "_metadata": {
            "source_pdf": "sd_host_3_00.pdf",
            "extraction_date": time.strftime("%Y-%m-%d"),
            "total_sections": len(sections),
            "total_chunks": total_chunks,
            "toc_source": "extracted_from_text",
            "page_offset": PAGE_OFFSET,
            "chunk_target_words": CHUNK_TARGET_WORDS,
            "chunk_max_words": CHUNK_MAX_WORDS,
            "abstract_generator": "haiku",
            "validation_attempts": MAX_RETRIES
        },
        "sections": {
            sec_num: asdict(section) for sec_num, section in sections.items()
        }
    }
    
    print(f"  Total sections: {len(sections)}")
    print(f"  Total chunks: {total_chunks}")
    
    return output


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Extract sections from PDF")
    parser.add_argument("--start-page", type=int, default=1, help="Start page (PDF page number)")
    parser.add_argument("--end-page", type=int, default=None, help="End page (PDF page number)")
    parser.add_argument("--pages", type=str, default=None, 
                        help="Specific pages to process (comma-separated PDF page numbers, e.g., '86,108,113')")
    parser.add_argument("--fill-missing", action="store_true",
                        help="Only process pages that don't have chunks in existing sections.json")
    parser.add_argument("--skip-toc", action="store_true", help="Skip ToC extraction, use existing toc_raw.json")
    parser.add_argument("--skip-chunks", action="store_true", help="Skip chunk extraction, use existing data")
    parser.add_argument("--toc-only", action="store_true", help="Only extract ToC, don't process chunks")
    parser.add_argument("--dry-run", action="store_true", help="Don't call LLM, just show what would be done")
    parser.add_argument("--model", choices=["haiku", "sonnet", "opus"], default=DEFAULT_MODEL,
                        help=f"LLM model to use (default: {DEFAULT_MODEL})")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS,
                        help=f"Number of parallel workers (default: {DEFAULT_WORKERS})")
    args = parser.parse_args()
    
    # Set global model based on argument
    global LLM_MODEL
    LLM_MODEL = MODELS[args.model]
    
    print("=" * 60)
    print("SD Host 3.0 Section Extraction")
    print("=" * 60)
    print(f"Model: {args.model} ({LLM_MODEL})")
    
    # Check PDF exists
    if not PDF_PATH.exists():
        print(f"ERROR: PDF not found at {PDF_PATH}")
        sys.exit(1)
    
    # Load table/figure maps
    print("\nLoading resource maps...")
    tables_map = load_json(TABLES_MAP_PATH) if TABLES_MAP_PATH.exists() else {"tables": []}
    figures_map = load_json(FIGURES_MAP_PATH) if FIGURES_MAP_PATH.exists() else {"figures": []}
    print(f"  Tables: {len(tables_map.get('tables', []))}")
    print(f"  Figures: {len(figures_map.get('figures', []))}")
    
    # Open PDF
    print(f"\nOpening PDF: {PDF_PATH}")
    doc = fitz.open(PDF_PATH)
    print(f"  Total pages: {len(doc)}")
    
    # Phase 1: Extract ToC
    if args.skip_toc and TOC_RAW_PATH.exists():
        print("\nLoading existing ToC...")
        toc_data = load_json(TOC_RAW_PATH)
        # Reconstruct Section objects
        sections = {}
        for sec_num, sec_dict in toc_data.get("sections", {}).items():
            section = Section(**{k: v for k, v in sec_dict.items() if k in Section.__dataclass_fields__})
            sections[sec_num] = section
        toc_data["sections"] = sections
    else:
        toc_data = extract_toc_structure(doc)
        # Save ToC
        toc_output = {
            "headers": toc_data["headers"],
            "sections": {k: asdict(v) for k, v in toc_data["sections"].items()}
        }
        save_json(toc_output, TOC_RAW_PATH)
    
    if args.toc_only:
        print("\nToC extraction complete. Exiting (--toc-only).")
        doc.close()
        return
    
    if args.dry_run:
        print("\nDry run mode - skipping LLM calls")
        doc.close()
        return
    
    # Determine which pages to process
    specific_pages = None
    existing_chunks = {}
    
    if args.fill_missing:
        # Load existing sections.json to find pages without chunks
        if OUTPUT_PATH.exists():
            print("\nChecking for missing pages in existing sections.json...")
            existing_data = load_json(OUTPUT_PATH)
            existing_chunks = _load_existing_chunks(existing_data)
            pages_with_chunks = get_pages_with_chunks(existing_data)
            total_spec_pages = len(doc) - PAGE_OFFSET
            specific_pages = get_missing_pages(total_spec_pages, pages_with_chunks, PAGE_OFFSET)
            if not specific_pages:
                print("  All pages have chunks - nothing to fill!")
                doc.close()
                return
            print(f"  Found {len(specific_pages)} pages without chunks: {specific_pages}")
        else:
            print("  No existing sections.json found - will process all pages")
    
    if args.pages:
        # Parse comma-separated page numbers
        specific_pages = [int(p.strip()) for p in args.pages.split(",")]
        print(f"\nProcessing specific pages: {specific_pages}")
    
    # Initialize LLM client
    print(f"\nInitializing LLM client (workers: {args.workers})...")
    client = get_anthropic_client()
    
    # Phase 2: Extract chunks
    if not args.skip_chunks:
        all_chunks = process_pages(
            client, doc, toc_data, tables_map, figures_map,
            start_page=args.start_page,
            end_page=args.end_page,
            num_workers=args.workers,
            specific_pages=specific_pages
        )
        
        # Merge with existing chunks if filling missing
        if args.fill_missing and existing_chunks:
            print("\nMerging with existing chunks...")
            for sec_num, chunks in existing_chunks.items():
                if sec_num not in all_chunks:
                    all_chunks[sec_num] = chunks
                else:
                    # Merge by spec_page (avoid duplicates)
                    existing_pages = {c.get("spec_page") for c in all_chunks[sec_num]}
                    for chunk in chunks:
                        if chunk.get("spec_page") not in existing_pages:
                            all_chunks[sec_num].append(chunk)
        
        # Phase 3: Generate abstracts and keywords
        generate_abstracts_and_keywords(client, toc_data["sections"], all_chunks, num_workers=args.workers)
    else:
        print("\nSkipping chunk extraction (--skip-chunks)")
        all_chunks = {}
    
    # Build final output
    output = build_sections_json(toc_data, all_chunks, tables_map, figures_map)
    
    # Save output
    save_json(output, OUTPUT_PATH)
    
    doc.close()
    print("\nDone!")


if __name__ == "__main__":
    main()
