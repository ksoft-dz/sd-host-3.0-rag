#!/usr/bin/env python3
"""
Shared utility functions for the RAG V2 pipeline.
"""

import json
import re
import time
from pathlib import Path
from typing import List, Dict, Any, Optional


# =============================================================================
# IO
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
    print(f"  Saved: {path}")


# =============================================================================
# TEXT PROCESSING
# =============================================================================

STOP_WORDS = frozenset({
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'to', 'of',
    'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into', 'through',
    'during', 'before', 'after', 'above', 'below', 'between', 'under',
    'and', 'or', 'but', 'if', 'then', 'else', 'when', 'where', 'why', 'how',
    'this', 'that', 'these', 'those', 'it', 'its', 'they', 'them', 'their',
    'which', 'who', 'whom', 'what', 'each', 'all', 'both', 'any', 'some'
})


def extract_keywords(text: str, max_count: int = 20) -> List[str]:
    """Extract keywords from text, filtering stop words."""
    words = re.findall(r'\b[a-zA-Z][a-zA-Z0-9_]{2,}\b', text.lower())
    seen = set()
    keywords = []
    for w in words:
        if w not in STOP_WORDS and w not in seen:
            seen.add(w)
            keywords.append(w)
    return keywords[:max_count]


def extract_technical_terms(text: str, max_count: int = 15) -> List[str]:
    """Extract technical terms (acronyms, hex values, register names)."""
    terms = []
    
    # Acronyms (2+ uppercase letters)
    acronyms = re.findall(r'\b[A-Z]{2,}[0-9]*\b', text)
    terms.extend(acronyms)
    
    # Hex offsets (e.g., "029h", "0x29")
    hex_vals = re.findall(r'\b(?:0x)?[0-9A-Fa-f]+h?\b', text)
    terms.extend([h for h in hex_vals if len(h) >= 2])
    
    # Bit ranges (e.g., "D07-D04", "bits 31:24")
    bit_ranges = re.findall(r'\b(?:D\d+-D\d+|bits?\s*\d+(?::\d+)?)\b', text, re.IGNORECASE)
    terms.extend(bit_ranges)
    
    return list(set(terms))[:max_count]


# =============================================================================
# REFERENCE FINDERS
# =============================================================================

def find_table_references(text: str) -> List[str]:
    """Find Table references in text → TABLE ids.
    Supports both 'Table X-Y' → TABLE_X_Y and 'Table N' → TABLE_N formats.
    """
    # Try chapter-seq format first (Table X-Y)
    matches_cs = re.findall(r'Table\s+(\d+)-(\d+)', text, re.IGNORECASE)
    if matches_cs:
        return [f"TABLE_{m[0]}_{m[1]}" for m in matches_cs]
    # Fall back to single-number format (Table N)
    matches_sn = re.findall(r'Table\s+(\d+)(?!\d)', text, re.IGNORECASE)
    return [f"TABLE_{m}" for m in matches_sn]


def find_figure_references(text: str) -> List[str]:
    """Find Figure references in text → FIG ids.
    Supports both 'Figure X-Y' → FIG_X_Y and 'Figure N' → FIG_N formats.
    """
    # Try chapter-seq format first (Figure X-Y)
    matches_cs = re.findall(r'Figure\s+(\d+)-(\d+)', text, re.IGNORECASE)
    if matches_cs:
        return [f"FIG_{m[0]}_{m[1]}" for m in matches_cs]
    # Fall back to single-number format (Figure N)
    matches_sn = re.findall(r'Figure\s+(\d+)(?!\d)', text, re.IGNORECASE)
    return [f"FIG_{m}" for m in matches_sn]


def find_section_references(text: str) -> List[str]:
    """Find Section X.Y.Z references in text."""
    matches = re.findall(r'Section\s+(\d+(?:\.\d+)*)', text, re.IGNORECASE)
    return matches


# =============================================================================
# CLASSIFIERS
# =============================================================================

def classify_by_rules(text: str, rules: List[dict]) -> str:
    """Classify text using config-driven rules.
    
    Each rule: {"pattern": "regex", "type": "RESULT_TYPE"}
    Returns the type of the first matching rule.
    """
    text_lower = text.lower()
    for rule in rules:
        if re.search(rule["pattern"], text_lower):
            return rule["type"]
    return "OTHER"


# =============================================================================
# REGISTER HELPERS
# =============================================================================

def normalize_offset(offset: str) -> str:
    """Normalize offset string to uppercase without prefix/suffix."""
    offset = offset.strip().upper()
    if offset.startswith("0X"):
        offset = offset[2:]
    if offset.endswith("H"):
        offset = offset[:-1]
    return offset.zfill(3)


def format_offset(offset: str) -> str:
    """Format offset for display (e.g., '028h')."""
    return f"{normalize_offset(offset)}h"


def parse_register_from_title(title: str) -> Optional[dict]:
    """Parse register info from section title like 'Power Control Register (Offset 029h)'."""
    match = re.search(r'(.+?)\s+Register\s*\(Offset\s*([0-9A-Fa-f]+)h?\)', title, re.IGNORECASE)
    if match:
        return {
            "name": match.group(1).strip(),
            "offset": match.group(2).upper()
        }
    return None


# =============================================================================
# PRINTING
# =============================================================================

def print_banner(title: str):
    """Print a phase banner."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def print_step(step: str, message: str):
    """Print a step indicator."""
    print(f"  [{step}] {message}")


def print_done(message: str):
    """Print completion message."""
    print(f"\n  ✓ {message}\n")


def format_duration(seconds: float) -> str:
    """Format seconds into human-readable duration."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:.1f}s"
