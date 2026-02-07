#!/usr/bin/env python3
"""
Register Extraction Script for SD Host Controller 3.0 Specification

This script extracts:
1. REG_CLASS nodes from FIG_1_2 (address ranges) + TABLE_1_1 (version support)
2. REGISTER nodes from tables ending with "Register" title
3. FIELD nodes with LLM-generated abstracts and values

Output: registers.json with full register hierarchy
"""

import json
import os
import sys
import re
import csv
import time
import argparse
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Any, Tuple

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import anthropic
except ImportError:
    print("Error: anthropic package required. Install with: pip install anthropic")
    sys.exit(1)

# Configuration
RATE_LIMIT_DELAY = 1.5  # seconds between API calls per worker
MAX_RETRIES = 3
MODEL = "claude-sonnet-4-20250514"
DEFAULT_WORKERS = 1
MAX_WORKERS = 4  # Conservative limit to avoid rate limits

# Paths
WORKSPACE = Path(__file__).parent.parent
TABLES_DIR = WORKSPACE / "tables"
TABLES_MAP = TABLES_DIR / "tables_page_map.json"
TABLES_CSV_DIR = TABLES_DIR / "csv"
FIGURES_DIR = WORKSPACE / "figures"
FIGURES_PLANTUML_DIR = FIGURES_DIR / "plantuml"
OUTPUT_FILE = Path(__file__).parent / "registers.json"

# Register class definitions from FIG_1_2
REGISTER_CLASSES = [
    {"id": "REGCLASS_CMD_GEN", "name": "SD Command Generation", "address_start": "000h", "address_end": "00Fh", "table_1_1_name": "SD command generation"},
    {"id": "REGCLASS_RESPONSE", "name": "Response", "address_start": "010h", "address_end": "01Fh", "table_1_1_name": "Response"},
    {"id": "REGCLASS_BUFFER", "name": "Buffer Data Port", "address_start": "020h", "address_end": "023h", "table_1_1_name": "Buffer Data port"},
    {"id": "REGCLASS_HOST_CTRL1", "name": "Host Control 1 and Others", "address_start": "024h", "address_end": "02Fh", "table_1_1_name": "Host control 1 and Others"},
    {"id": "REGCLASS_INTERRUPT", "name": "Interrupt Controls", "address_start": "030h", "address_end": "03Dh", "table_1_1_name": "Interrupt controls"},
    {"id": "REGCLASS_HOST_CTRL2", "name": "Host Control 2", "address_start": "03Eh", "address_end": "03Fh", "table_1_1_name": "Host Control 2"},
    {"id": "REGCLASS_CAPABILITIES", "name": "Capabilities", "address_start": "040h", "address_end": "04Fh", "table_1_1_name": "Capabilities"},
    {"id": "REGCLASS_FORCE_EVENT", "name": "Force Event", "address_start": "050h", "address_end": "053h", "table_1_1_name": "Force Event"},
    {"id": "REGCLASS_ADMA", "name": "ADMA", "address_start": "054h", "address_end": "05Fh", "table_1_1_name": "ADMA"},
    {"id": "REGCLASS_PRESET", "name": "Preset Value", "address_start": "060h", "address_end": "06Fh", "table_1_1_name": "Preset Value"},
    {"id": "REGCLASS_SHARED_BUS", "name": "Shared Bus", "address_start": "0E0h", "address_end": "0E3h", "table_1_1_name": "Shared Bus"},
    {"id": "REGCLASS_COMMON", "name": "Common Area", "address_start": "0F0h", "address_end": "0FFh", "table_1_1_name": "Common area"},
]

# Tables to exclude (not register field definitions)
EXCLUDE_TABLES = [
    # Chapter 1 tables - not register field definitions
    "TABLE_1_1",   # Supported Registers summary
    "TABLE_1_2",   # Registers to Generate SD Command (summary)
    "TABLE_1_3",   # Response Register content mapping
    "TABLE_1_4",   # Available Byte Enable Pattern  
    "TABLE_1_5",   # Host Control Registers summary
    "TABLE_1_6",   # Host Control Registers (cont)
    "TABLE_1_7",   # Summary of Register Status
    "TABLE_1_8",   # Summary for Data Transfer
    "TABLE_1_9",   # Data Line Active summary
    "TABLE_1_10",  # Auto CMD status
    "TABLE_1_11",  # Auto CMD fields
    "TABLE_1_13",  # PCI config registers
    "TABLE_1_14",  # PCI stuff
    # Chapter 2 non-field tables
    "TABLE_2_1",   # Register map layout
    "TABLE_2_2",   # Available Byte Enable Pattern
    "TABLE_2_8",   # Multi/Single Block function table
    "TABLE_2_10",  # Response Type mapping
    "TABLE_2_11",  # Response Register mapping
    "TABLE_2_12",  # Response Register mapping (duplicate)
    "TABLE_2_25",  # CMD CRC/Timeout error table
    "TABLE_2_31",  # Auto CMD error table
    "TABLE_2_36",  # Current value conversion
    "TABLE_2_41",  # Preset Value offset mapping
    "TABLE_2_42",  # Bus Speed Mode selection
    "TABLE_2_46",  # Host Controller Version values
]

# Map register offsets to their section info (from ToC)
REGISTER_OFFSETS = {
    "000h": {"section": "2.2.1", "name": "SDMA System Address / Argument 2 Register"},
    "004h": {"section": "2.2.2", "name": "Block Size Register"},
    "006h": {"section": "2.2.3", "name": "Block Count Register"},
    "008h": {"section": "2.2.4", "name": "Argument 1 Register"},
    "00Ch": {"section": "2.2.5", "name": "Transfer Mode Register"},
    "00Eh": {"section": "2.2.6", "name": "Command Register"},
    "010h": {"section": "2.2.7", "name": "Response Register"},
    "020h": {"section": "2.2.8", "name": "Buffer Data Port Register"},
    "024h": {"section": "2.2.9", "name": "Present State Register"},
    "028h": {"section": "2.2.10", "name": "Host Control 1 Register"},
    "029h": {"section": "2.2.11", "name": "Power Control Register"},
    "02Ah": {"section": "2.2.12", "name": "Block Gap Control Register"},
    "02Bh": {"section": "2.2.13", "name": "Wakeup Control Register"},
    "02Ch": {"section": "2.2.14", "name": "Clock Control Register"},
    "02Eh": {"section": "2.2.15", "name": "Timeout Control Register"},
    "02Fh": {"section": "2.2.16", "name": "Software Reset Register"},
    "030h": {"section": "2.2.17", "name": "Normal Interrupt Status Register"},
    "032h": {"section": "2.2.18", "name": "Error Interrupt Status Register"},
    "034h": {"section": "2.2.19", "name": "Normal Interrupt Status Enable Register"},
    "036h": {"section": "2.2.20", "name": "Error Interrupt Status Enable Register"},
    "038h": {"section": "2.2.21", "name": "Normal Interrupt Signal Enable Register"},
    "03Ah": {"section": "2.2.22", "name": "Error Interrupt Signal Enable Register"},
    "03Ch": {"section": "2.2.23", "name": "Auto CMD Error Status Register"},
    "03Eh": {"section": "2.2.24", "name": "Host Control 2 Register"},
    "040h": {"section": "2.2.25", "name": "Capabilities Register"},
    "048h": {"section": "2.2.26", "name": "Maximum Current Capabilities Register"},
    "050h": {"section": "2.2.27", "name": "Force Event Register for Auto CMD Error Status"},
    "052h": {"section": "2.2.28", "name": "Force Event Register for Error Interrupt Status"},
    "054h": {"section": "2.2.29", "name": "ADMA Error Status Register"},
    "058h": {"section": "2.2.30", "name": "ADMA System Address Register"},
    "060h": {"section": "2.2.31", "name": "Preset Value Registers"},
    "0E0h": {"section": "2.2.32", "name": "Shared Bus Control Register"},
    "0FCh": {"section": "2.2.33", "name": "Slot Interrupt Status Register"},
    "0FEh": {"section": "2.2.34", "name": "Host Controller Version Register"},
}

# Direct mapping from TABLE ID to register offset
# This ensures precise mapping and supports merging multi-part tables
TABLE_TO_OFFSET = {
    "TABLE_2_3": "000h",   # SDMA System Address / Argument 2 Register
    "TABLE_2_4": "004h",   # Block Size Register
    "TABLE_2_5": "006h",   # Block Count Register
    "TABLE_2_6": "008h",   # Argument 1 Register
    "TABLE_2_7": "00Ch",   # Transfer Mode Register
    "TABLE_2_9": "00Eh",   # Command Register
    "TABLE_2_11": "010h",  # Response Register
    "TABLE_2_13": "020h",  # Buffer Data Port Register
    "TABLE_2_14": "024h",  # Present State Register (Part 1)
    "TABLE_2_15": "024h",  # Present State Register (Part 2) - same offset, will merge
    "TABLE_2_16": "028h",  # Host Control 1 Register
    "TABLE_2_17": "029h",  # Power Control Register
    "TABLE_2_18": "02Ah",  # Block Gap Control Register
    "TABLE_2_19": "02Bh",  # Wakeup Control Register
    "TABLE_2_20": "02Ch",  # Clock Control Register
    "TABLE_2_21": "02Eh",  # Timeout Control Register
    "TABLE_2_22": "02Fh",  # Software Reset Register
    "TABLE_2_23": "030h",  # Normal Interrupt Status Register
    "TABLE_2_24": "032h",  # Error Interrupt Status Register
    "TABLE_2_26": "034h",  # Normal Interrupt Status Enable Register
    "TABLE_2_27": "036h",  # Error Interrupt Status Enable Register
    "TABLE_2_28": "038h",  # Normal Interrupt Signal Enable Register
    "TABLE_2_29": "03Ah",  # Error Interrupt Signal Enable Register
    "TABLE_2_30": "03Ch",  # Auto CMD Error Status Register
    "TABLE_2_32": "03Eh",  # Host Control 2 Register
    "TABLE_2_33": "040h",  # Capabilities Register (Part 1)
    "TABLE_2_34": "040h",  # Capabilities Register (Part 2) - same offset, will merge
    "TABLE_2_35": "048h",  # Maximum Current Capabilities Register
    "TABLE_2_37": "050h",  # Force Event Register for Auto CMD Error Status
    "TABLE_2_38": "052h",  # Force Event for Error Interrupt Status Register
    "TABLE_2_39": "054h",  # ADMA Error Status Register
    "TABLE_2_40": "058h",  # ADMA System Address Register
    "TABLE_2_43": "060h",  # Fields of A Preset Value Register (generic)
    "TABLE_2_44": "0E0h",  # Shared Bus Control Register
    "TABLE_2_45": "0FCh",  # Slot Interrupt Status Register
}


class RegisterExtractor:
    """Extract register information from CSV tables using LLM."""
    
    def __init__(self, api_key: Optional[str] = None, num_workers: int = 1):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable required")
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.num_workers = num_workers
        
        # Thread-safe rate limiting
        self._rate_lock = threading.Lock()
        self._last_api_call = 0
        self._call_count = 0
        self._rate_limit_hits = 0
        
    def _rate_limit(self):
        """Ensure rate limiting between API calls (thread-safe)."""
        with self._rate_lock:
            # Adjust delay based on number of workers
            delay = RATE_LIMIT_DELAY * max(1, self.num_workers / 2)
            elapsed = time.time() - self._last_api_call
            if elapsed < delay:
                time.sleep(delay - elapsed)
            self._last_api_call = time.time()
            self._call_count += 1
    
    def get_stats(self) -> Dict:
        """Get extraction statistics."""
        return {
            "api_calls": self._call_count,
            "rate_limit_hits": self._rate_limit_hits
        }
    
    def _call_llm(self, prompt: str, max_tokens: int = 1024) -> str:
        """Call LLM with rate limiting and retry logic."""
        for attempt in range(MAX_RETRIES):
            try:
                self._rate_limit()
                response = self.client.messages.create(
                    model=MODEL,
                    max_tokens=max_tokens,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text
            except anthropic.RateLimitError:
                with self._rate_lock:
                    self._rate_limit_hits += 1
                wait_time = RATE_LIMIT_DELAY * (2 ** (attempt + 1)) * self.num_workers
                print(f"  ⚠ Rate limited, waiting {wait_time:.1f}s...")
                time.sleep(wait_time)
            except Exception as e:
                print(f"  API error (attempt {attempt + 1}): {e}")
                if attempt == MAX_RETRIES - 1:
                    raise
                time.sleep(RATE_LIMIT_DELAY)
        return ""
    
    def extract_field_info(self, location: str, attrib: str, raw_text: str, register_name: str) -> Dict:
        """Extract structured field info using LLM."""
        prompt = f"""You are extracting register field information from an SD Host Controller specification.

Register: {register_name}
Field Location (bits): {location}
Original Attribute: {attrib}
Raw Text:
{raw_text}

Extract the field information and return ONLY valid JSON (no markdown, no explanation):
{{
  "field_name": "The field name (concise, like 'SD Bus Power' or 'Reserved')",
  "width": 8,
  "access": "read-write",
  "read_effect": "none",
  "write_effect": "none",
  "abstract": "One clear sentence describing what this field does (max 120 chars)",
  "values": [
    {{"code": "value code like 1 or 111b or 0x0F", "meaning": "what this value means"}}
  ]
}}

STRICT RULES:

1. field_name: Extract the main field name from the text, not the bit range

2. width: Calculate from bit location. Examples:
   - "07-04" = 4 bits
   - "31-00" = 32 bits
   - "00" = 1 bit
   - "15" = 1 bit

3. access: MUST be exactly one of these values:
   - "read-write" (for RW, R/W fields)
   - "read-only" (for RO, ROC, HwInit fields)
   - "write-only" (for WO fields)
   - "reserved" (for Rsvd, Reserved fields)

4. read_effect: What happens when software reads this field:
   - "none" (normal read, value unchanged)
   - "clear" (field is cleared to 0 after read - for ROC type)
   - "undefined" (read value is undefined during certain operations)

5. write_effect: What happens when software writes this field:
   - "none" (normal write)
   - "write-1-clear" (writing 1 clears the bit - for RW1C type)
   - "auto-clear" (bit automatically clears after action - for RWAC type)
   - "ignored" (writes are ignored - for RO fields)
   - "set-by-hardware" (field set by hardware only - for HwInit)

6. abstract: Write a clear, concise summary (max 120 chars). If Reserved, use "Reserved for future use."

7. values: Extract ALL enumerated values. Look for patterns like:
   - "1 = xxx" or "0 = xxx"
   - "111b = xxx" or "00b = xxx"  
   - "1  Power on" (value followed by meaning)
   - If no values specified, return empty array []

Return ONLY the JSON object, nothing else."""

        for attempt in range(MAX_RETRIES):
            try:
                response = self._call_llm(prompt)
                # Clean response - remove markdown code blocks if present
                response = response.strip()
                if response.startswith("```"):
                    response = re.sub(r'^```(?:json)?\n?', '', response)
                    response = re.sub(r'\n?```$', '', response)
                
                result = json.loads(response)
                
                # Validate required fields
                required = ["field_name", "abstract", "width", "access", "read_effect", "write_effect"]
                missing = [f for f in required if f not in result]
                if missing:
                    raise ValueError(f"Missing required fields: {missing}")
                
                # Validate access value
                valid_access = ["read-write", "read-only", "write-only", "reserved"]
                if result["access"] not in valid_access:
                    raise ValueError(f"Invalid access '{result['access']}', must be one of {valid_access}")
                
                # Validate effects
                valid_read_effects = ["none", "clear", "undefined"]
                valid_write_effects = ["none", "write-1-clear", "auto-clear", "ignored", "set-by-hardware"]
                if result["read_effect"] not in valid_read_effects:
                    raise ValueError(f"Invalid read_effect '{result['read_effect']}'")
                if result["write_effect"] not in valid_write_effects:
                    raise ValueError(f"Invalid write_effect '{result['write_effect']}'")
                
                if "values" not in result:
                    result["values"] = []
                    
                return result
                
            except json.JSONDecodeError as e:
                print(f"    JSON parse error (attempt {attempt + 1}): {e}")
                if attempt < MAX_RETRIES - 1:
                    # Add feedback for retry
                    prompt += f"\n\nYour previous response was not valid JSON. Error: {e}\nPlease return ONLY a valid JSON object."
            except ValueError as e:
                print(f"    Validation error (attempt {attempt + 1}): {e}")
                if attempt < MAX_RETRIES - 1:
                    prompt += f"\n\nYour previous response had validation errors: {e}\nPlease fix and return valid JSON."
            except Exception as e:
                print(f"    Error (attempt {attempt + 1}): {e}")
                
        # Fallback if all retries fail - calculate width from location
        bit_high, bit_low = parse_bit_range(location)
        width = (bit_high - bit_low + 1) if bit_high is not None and bit_low is not None else 1
        
        # Determine access from original attrib
        attrib_lower = attrib.lower()
        if 'rsvd' in attrib_lower or 'reserved' in attrib_lower:
            access = "reserved"
        elif 'wo' in attrib_lower:
            access = "write-only"
        elif 'ro' in attrib_lower or 'hwinit' in attrib_lower:
            access = "read-only"
        else:
            access = "read-write"
        
        return {
            "field_name": self._extract_field_name_fallback(raw_text, location),
            "width": width,
            "access": access,
            "read_effect": "none",
            "write_effect": "none",
            "abstract": raw_text[:120] if len(raw_text) > 120 else raw_text,
            "values": []
        }
    
    def _extract_field_name_fallback(self, text: str, location: str) -> str:
        """Fallback field name extraction without LLM."""
        # Try to get first line or first sentence
        lines = text.strip().split('\n')
        first_line = lines[0].strip()
        
        # If it looks like a field name (short, no sentence structure)
        if len(first_line) < 50 and '.' not in first_line:
            return first_line
        
        # Otherwise use location as identifier
        return f"Field_{location.replace('-', '_')}"


def load_tables_map() -> Dict:
    """Load tables page map."""
    with open(TABLES_MAP, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_version_support() -> Dict[str, Dict]:
    """Load version support from TABLE_1_1."""
    version_support = {}
    table_path = TABLES_CSV_DIR / "TABLE_1_1.csv"
    
    if not table_path.exists():
        print(f"Warning: {table_path} not found")
        return version_support
    
    with open(table_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get('Register Name', '').strip()
            if name:
                version_support[name.lower()] = {
                    "1.00": row.get('Version 1.00', 'N/A').strip(),
                    "2.00": row.get('Version 2.00', 'N/A').strip(),
                    "3.00": row.get('Version 3.00', 'N/A').strip(),
                    "comment": row.get('Comment', '').strip()
                }
    
    return version_support


def build_register_classes(version_support: Dict) -> List[Dict]:
    """Build REG_CLASS nodes."""
    classes = []
    
    for rc in REGISTER_CLASSES:
        # Find version support by matching name
        vs = {"1.00": "N/A", "2.00": "N/A", "3.00": "N/A"}
        search_name = rc["table_1_1_name"].lower()
        
        for name, support in version_support.items():
            if search_name in name or name in search_name:
                vs = {
                    "1.00": support["1.00"],
                    "2.00": support["2.00"],
                    "3.00": support["3.00"]
                }
                break
        
        classes.append({
            "id": rc["id"],
            "type": "REG_CLASS",
            "name": rc["name"],
            "address_range": {
                "start": rc["address_start"],
                "end": rc["address_end"]
            },
            "version_support": vs,
            "source": {
                "figure": "FIG_1_2",
                "table": "TABLE_1_1"
            }
        })
    
    return classes


def get_register_class(offset: str) -> Optional[str]:
    """Determine which register class an offset belongs to."""
    try:
        # Parse offset to int (handle formats like "000h", "0x000", "000")
        offset_clean = offset.lower().replace('h', '').replace('0x', '')
        offset_int = int(offset_clean, 16)
        
        for rc in REGISTER_CLASSES:
            start = int(rc["address_start"].lower().replace('h', ''), 16)
            end = int(rc["address_end"].lower().replace('h', ''), 16)
            if start <= offset_int <= end:
                return rc["id"]
    except ValueError:
        pass
    return None


def find_register_tables(tables_map: Dict) -> List[Dict]:
    """Find all tables that define register fields."""
    register_tables = []
    
    for table in tables_map.get("tables", []):
        table_id = table.get("id", "")
        title = table.get("title", "")
        
        # Skip excluded tables
        if table_id in EXCLUDE_TABLES:
            continue
        
        # Check if title ends with "Register" (case-insensitive)
        if title.lower().endswith("register") or "register" in title.lower():
            csv_file = TABLES_CSV_DIR / f"{table_id}.csv"
            if csv_file.exists():
                register_tables.append({
                    "id": table_id,
                    "title": title,
                    "csv_file": csv_file,
                    "spec_page": table.get("spec_page"),
                    "definition_page": table.get("definition_page")
                })
    
    return register_tables


def detect_csv_format(csv_file: Path) -> Dict:
    """Detect the column format of a CSV file."""
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader, [])
    
    headers_lower = [h.lower().strip() for h in headers]
    
    # Detect format based on headers
    if 'location' in headers_lower and 'attrib' in headers_lower:
        if len(headers) >= 5 and ('value' in headers_lower or 'meaning' in headers_lower):
            return {"format": "5col", "location": 0, "attrib": 1, "text": 2, "value": 3, "meaning": 4}
        else:
            return {"format": "3col", "location": 0, "attrib": 1, "text": 2}
    elif 'address' in headers_lower and 'access' in headers_lower:
        return {"format": "4col_alt", "location": 0, "attrib": 1, "name": 2, "text": 3}
    
    # Default fallback
    return {"format": "3col", "location": 0, "attrib": 1, "text": 2}


def parse_csv_fields(csv_file: Path) -> List[Dict]:
    """Parse fields from a register CSV file."""
    fields = []
    fmt = detect_csv_format(csv_file)
    
    # Read file with proper newline handling
    with open(csv_file, 'r', encoding='utf-8', newline='') as f:
        content = f.read()
    
    # Normalize line endings
    content = content.replace('\r\n', '\n').replace('\r', '\n')
    
    # Manual CSV parsing to handle complex multi-line quoted fields
    rows = []
    current_row = []
    current_cell = ""
    in_quotes = False
    i = 0
    
    while i < len(content):
        char = content[i]
        
        if char == '"':
            if in_quotes and i + 1 < len(content) and content[i + 1] == '"':
                # Escaped quote
                current_cell += '"'
                i += 2
                continue
            else:
                in_quotes = not in_quotes
                i += 1
                continue
        
        if not in_quotes:
            if char == ',':
                current_row.append(current_cell.strip())
                current_cell = ""
                i += 1
                continue
            elif char == '\n':
                current_row.append(current_cell.strip())
                if any(cell for cell in current_row):  # Skip empty rows
                    rows.append(current_row)
                current_row = []
                current_cell = ""
                i += 1
                continue
        
        current_cell += char
        i += 1
    
    # Don't forget last cell/row
    if current_cell or current_row:
        current_row.append(current_cell.strip())
        if any(cell for cell in current_row):
            rows.append(current_row)
    
    if not rows:
        return fields
    
    # Skip header row
    rows = rows[1:]
    
    current_field = None
    
    for row in rows:
        if not row or all(not cell for cell in row):
            continue
        
        # Get location (first column usually)
        location = row[0] if len(row) > 0 else ""
        attrib = row[1] if len(row) > 1 else ""
        
        # Check if this is a main field row (has bit location pattern like "07-04" or "15")
        is_main_field = bool(location and re.match(r'^[\d][\d\-]*$', location.strip()))
        
        if is_main_field:
            # This is a main field
            if fmt["format"] == "3col":
                text = row[2] if len(row) > 2 else ""
            elif fmt["format"] == "5col":
                text = row[2] if len(row) > 2 else ""
                # Append value/meaning if present
                if len(row) > 3 and row[3]:
                    text += f"\n{row[3]}"
                if len(row) > 4 and row[4]:
                    text += f"  {row[4]}"
            elif fmt["format"] == "4col_alt":
                name = row[2] if len(row) > 2 else ""
                desc = row[3] if len(row) > 3 else ""
                text = f"{name}\n{desc}" if name else desc
            else:
                text = row[2] if len(row) > 2 else ""
            
            current_field = {
                "location": location,
                "attrib": attrib,
                "raw_text": text
            }
            fields.append(current_field)
        elif current_field:
            # This is a sub-value row or continuation - append to current field
            sub_parts = [cell for cell in row if cell]
            if sub_parts:
                sub_text = "  ".join(sub_parts)
                current_field["raw_text"] += f"\n{sub_text}"
    
    return fields


def table_to_register_offset(table_id: str, table_title: str) -> Optional[str]:
    """Map a table to its register offset.
    
    Uses direct TABLE_TO_OFFSET mapping first, then falls back to title matching.
    """
    # Direct mapping takes priority
    if table_id in TABLE_TO_OFFSET:
        return TABLE_TO_OFFSET[table_id]
    
    # Fallback: fuzzy title matching
    title_lower = table_title.lower()
    
    for offset, info in REGISTER_OFFSETS.items():
        reg_name = info["name"].lower()
        # Check if titles match (removing "Register" suffix for comparison)
        title_clean = title_lower.replace(" register", "").replace("(part 1)", "").replace("(part 2)", "").strip()
        name_clean = reg_name.replace(" register", "").strip()
        
        # Exact match required for safety
        if title_clean == name_clean:
            return offset
    
    return None


def process_register_table(extractor: RegisterExtractor, table_info: Dict, verbose: bool = False) -> Optional[Dict]:
    """Process a single register table and extract all fields."""
    table_id = table_info["id"]
    title = table_info["title"]
    csv_file = table_info["csv_file"]
    
    if verbose:
        print(f"Processing {table_id}: {title}")
    
    # Parse CSV fields
    try:
        raw_fields = parse_csv_fields(csv_file)
    except Exception as e:
        print(f"  Error parsing {csv_file}: {e}")
        return None
    
    if not raw_fields:
        if verbose:
            print(f"  No fields found in {table_id}")
        return None
    
    # Determine register offset from table ID and title
    offset = table_to_register_offset(table_id, title)
    if not offset:
        # Try to extract offset from title pattern like "(Offset 029h)"
        match = re.search(r'\(?\s*offset\s+([0-9a-fA-F]+)h?\s*\)?', title, re.IGNORECASE)
        if match:
            offset = f"{match.group(1).upper()}h"
    
    # Get register info
    reg_info = REGISTER_OFFSETS.get(offset, {})
    reg_name = reg_info.get("name", title)
    reg_section = reg_info.get("section", "")
    reg_class = get_register_class(offset) if offset else None
    
    # Process each field with LLM
    fields = []
    for i, raw_field in enumerate(raw_fields):
        if verbose:
            print(f"  Field {i+1}/{len(raw_fields)}: {raw_field['location']}")
        
        # Extract field info using LLM
        field_info = extractor.extract_field_info(
            location=raw_field["location"],
            attrib=raw_field["attrib"],
            raw_text=raw_field["raw_text"],
            register_name=reg_name
        )
        
        # Build field node
        field_id = f"REG_{offset.replace('h', '') if offset else table_id}_F{i}"
        
        # Parse bit range
        bit_high, bit_low = parse_bit_range(raw_field["location"])
        
        fields.append({
            "id": field_id,
            "name": field_info["field_name"],
            "bits": raw_field["location"],
            "bit_high": bit_high,
            "bit_low": bit_low,
            "width": field_info["width"],
            "access": field_info["access"],
            "read_effect": field_info["read_effect"],
            "write_effect": field_info["write_effect"],
            "original_attrib": raw_field["attrib"],
            "raw": raw_field["raw_text"],
            "abstract": field_info["abstract"],
            "values": field_info["values"]
        })
    
    # Build register node
    reg_id = f"REG_{offset.replace('h', '').upper()}" if offset else f"REG_{table_id}"
    
    return {
        "id": reg_id,
        "type": "REGISTER",
        "name": reg_name,
        "offset": offset,
        "spec_section": reg_section,
        "spec_table": table_id,
        "class_id": reg_class,
        "source": {
            "table": table_id,
            "page": table_info.get("spec_page"),
            "definition_page": table_info.get("definition_page")
        },
        "fields": fields
    }


def parse_bit_range(location: str) -> Tuple[Optional[int], Optional[int]]:
    """Parse bit range like '07-04' or '15' into high and low bits."""
    try:
        location = location.strip()
        if '-' in location:
            parts = location.split('-')
            high = int(parts[0].strip())
            low = int(parts[1].strip())
            return high, low
        else:
            bit = int(location)
            return bit, bit
    except (ValueError, IndexError):
        return None, None


def merge_registers_by_offset(registers: List[Dict]) -> List[Dict]:
    """Merge registers that have the same offset (multi-part tables).
    
    When multiple tables define fields for the same register offset,
    merge them into a single register node with all fields combined.
    """
    from collections import defaultdict
    
    # Group by offset
    by_offset = defaultdict(list)
    no_offset = []
    
    for reg in registers:
        offset = reg.get("offset")
        if offset:
            by_offset[offset].append(reg)
        else:
            no_offset.append(reg)
    
    merged = []
    
    for offset, regs in sorted(by_offset.items(), key=lambda x: int(x[0].replace('h', ''), 16)):
        if len(regs) == 1:
            # No merge needed
            merged.append(regs[0])
        else:
            # Merge multiple registers
            base = regs[0].copy()
            all_fields = list(base.get("fields", []))
            all_tables = [base.get("spec_table")]
            
            for reg in regs[1:]:
                # Add fields from other parts
                for field in reg.get("fields", []):
                    # Check for duplicates by bit range (use 'bits' or 'location' key)
                    bits = field.get("bits") or field.get("location")
                    if not any((f.get("bits") or f.get("location")) == bits for f in all_fields):
                        all_fields.append(field)
                
                # Track source tables
                table = reg.get("spec_table")
                if table and table not in all_tables:
                    all_tables.append(table)
            
            # Sort fields by bit position (high to low)
            def get_bit_high(f):
                # Try 'bit_high' first (from LLM extraction)
                if f.get("bit_high") is not None:
                    return f["bit_high"]
                # Fall back to parsing 'location' (raw field)
                loc = f.get("location", "")
                if '-' in loc:
                    try:
                        return int(loc.split('-')[0])
                    except ValueError:
                        return 0
                try:
                    return int(loc)
                except ValueError:
                    return 0
            
            all_fields.sort(key=get_bit_high, reverse=True)
            
            # Update the merged register
            base["fields"] = all_fields
            base["spec_table"] = all_tables[0]  # Primary table
            base["merged_from"] = all_tables if len(all_tables) > 1 else None
            
            merged.append(base)
    
    # Add registers with no offset (keep as-is)
    merged.extend(no_offset)
    
    return merged


def build_relations(registers: List[Dict], reg_classes: List[Dict]) -> List[Dict]:
    """Build relations between registers, classes, and tables."""
    relations = []
    
    for reg in registers:
        reg_id = reg["id"]
        
        # REGISTER -> REG_CLASS (BELONGS_TO)
        if reg.get("class_id"):
            relations.append({
                "source": reg_id,
                "target": reg["class_id"],
                "type": "BELONGS_TO"
            })
        
        # REGISTER <-> TABLE (bidirectional DESCRIBES)
        # Handle merged registers (multiple source tables)
        tables = reg.get("merged_from") or ([reg.get("spec_table")] if reg.get("spec_table") else [])
        for table in tables:
            if table:
                relations.append({
                    "source": reg_id,
                    "target": table,
                    "type": "DEFINED_IN"
                })
                relations.append({
                    "source": table,
                    "target": reg_id,
                    "type": "DESCRIBES"
                })
    
    return relations


def main():
    parser = argparse.ArgumentParser(description="Extract registers from SD Host Controller spec")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--limit", "-l", type=int, help="Limit number of tables to process")
    parser.add_argument("--table", "-t", type=str, help="Process specific table ID only")
    parser.add_argument("--dry-run", action="store_true", help="Parse tables without LLM calls")
    parser.add_argument("--workers", "-w", type=int, default=DEFAULT_WORKERS, 
                        help=f"Number of parallel workers (default: {DEFAULT_WORKERS}, max: {MAX_WORKERS})")
    args = parser.parse_args()
    
    # Validate workers
    num_workers = min(args.workers, MAX_WORKERS)
    if args.workers > MAX_WORKERS:
        print(f"Warning: Limiting workers to {MAX_WORKERS} to avoid rate limits")
    
    print("=" * 60)
    print("SD Host Controller Register Extraction")
    print("=" * 60)
    
    # Load data
    print("\n[1/5] Loading tables map...")
    tables_map = load_tables_map()
    print(f"  Loaded {len(tables_map.get('tables', []))} tables")
    
    print("\n[2/5] Loading version support from TABLE_1_1...")
    version_support = load_version_support()
    print(f"  Found {len(version_support)} register class entries")
    
    print("\n[3/5] Building register classes...")
    reg_classes = build_register_classes(version_support)
    print(f"  Built {len(reg_classes)} REG_CLASS nodes")
    
    print("\n[4/5] Finding register tables...")
    register_tables = find_register_tables(tables_map)
    print(f"  Found {len(register_tables)} register definition tables")
    
    if args.table:
        register_tables = [t for t in register_tables if t["id"] == args.table]
        print(f"  Filtered to table: {args.table}")
    
    if args.limit:
        register_tables = register_tables[:args.limit]
        print(f"  Limited to {args.limit} tables")
    
    print("\n[5/5] Extracting register fields...")
    
    if args.dry_run:
        print("  DRY RUN - Parsing without LLM calls")
        registers = []
        for table_info in register_tables:
            table_id = table_info['id']
            title = table_info['title']
            offset = table_to_register_offset(table_id, title)
            print(f"  {table_id}: {title}")
            print(f"    → Offset: {offset or 'None'}")
            fields = parse_csv_fields(table_info["csv_file"])
            print(f"    → Found {len(fields)} fields")
            
            # Build minimal register entry for merge testing
            registers.append({
                "id": f"REG_{offset.replace('h', '').upper()}" if offset else f"REG_{table_id}",
                "name": REGISTER_OFFSETS.get(offset, {}).get("name", title) if offset else title,
                "offset": offset,
                "spec_table": table_id,
                "fields": fields
            })
        
        # Test merge
        print("\n  Testing merge...")
        pre_merge = len(registers)
        merged = merge_registers_by_offset(registers)
        print(f"  Before merge: {pre_merge} entries")
        print(f"  After merge:  {len(merged)} entries")
        
        # Show merged registers
        for reg in merged:
            if reg.get("merged_from"):
                print(f"    {reg['offset']}: {reg['name']} (merged from {reg['merged_from']})")
        
        print("\n  Summary by offset:")
        for reg in sorted(merged, key=lambda r: int(r.get("offset", "0").replace("h", ""), 16) if r.get("offset") else 0):
            print(f"    {reg.get('offset') or '???':>5} → {len(reg.get('fields', [])):>3} fields → {reg['name']}")
        return  # Exit dry-run
    else:
        # Initialize extractor
        try:
            extractor = RegisterExtractor(num_workers=num_workers)
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
        
        registers = []
        completed = 0
        failed = 0
        start_time = time.time()
        
        if num_workers > 1:
            print(f"  Using {num_workers} workers")
            
            # Process tables in parallel
            with ThreadPoolExecutor(max_workers=num_workers) as executor:
                # Submit all tasks
                future_to_table = {
                    executor.submit(process_register_table, extractor, table_info, args.verbose): table_info
                    for table_info in register_tables
                }
                
                # Collect results as they complete
                for future in as_completed(future_to_table):
                    table_info = future_to_table[future]
                    try:
                        reg = future.result()
                        if reg:
                            registers.append(reg)
                            completed += 1
                            print(f"  ✓ [{completed + failed}/{len(register_tables)}] {table_info['id']}: {len(reg['fields'])} fields")
                        else:
                            failed += 1
                            print(f"  ✗ [{completed + failed}/{len(register_tables)}] {table_info['id']}: Failed")
                    except Exception as e:
                        failed += 1
                        print(f"  ✗ [{completed + failed}/{len(register_tables)}] {table_info['id']}: Error - {e}")
        else:
            # Sequential processing
            for i, table_info in enumerate(register_tables):
                print(f"\n  [{i+1}/{len(register_tables)}] {table_info['id']}: {table_info['title']}")
                
                try:
                    reg = process_register_table(extractor, table_info, verbose=args.verbose)
                    if reg:
                        registers.append(reg)
                        completed += 1
                        print(f"    ✓ Extracted {len(reg['fields'])} fields")
                    else:
                        failed += 1
                        print(f"    ✗ Failed to process")
                except Exception as e:
                    failed += 1
                    print(f"    ✗ Error: {e}")
        
        elapsed = time.time() - start_time
        stats = extractor.get_stats()
        
        # Merge multi-part registers (same offset from different tables)
        print("\n[6/7] Merging multi-part registers...")
        pre_merge_count = len(registers)
        registers = merge_registers_by_offset(registers)
        merged_count = pre_merge_count - len(registers)
        if merged_count > 0:
            print(f"  Merged {merged_count} duplicate entries → {len(registers)} unique registers")
        else:
            print(f"  No merging needed")
        
        # Build relations
        print("\n[7/7] Building relations...")
        relations = build_relations(registers, reg_classes)
        print(f"  Built {len(relations)} relations")
        
        # Output
        output = {
            "_metadata": {
                "source": "SD Host Controller Simplified Specification Version 3.00",
                "extraction_date": time.strftime("%Y-%m-%d"),
                "total_reg_classes": len(reg_classes),
                "total_registers": len(registers),
                "total_fields": sum(len(r["fields"]) for r in registers),
                "total_relations": len(relations),
                "extraction_stats": {
                    "workers": num_workers,
                    "elapsed_seconds": round(elapsed, 1),
                    "api_calls": stats["api_calls"],
                    "rate_limit_hits": stats["rate_limit_hits"],
                    "tables_completed": completed,
                    "tables_failed": failed
                }
            },
            "reg_classes": reg_classes,
            "registers": registers,
            "relations": relations
        }
        
        # Write output
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"\n{'=' * 60}")
        print(f"Output written to: {OUTPUT_FILE}")
        print(f"  REG_CLASS nodes: {len(reg_classes)}")
        print(f"  REGISTER nodes:  {len(registers)}")
        print(f"  Total fields:    {output['_metadata']['total_fields']}")
        print(f"  Relations:       {len(relations)}")
        print(f"  Time elapsed:    {elapsed:.1f}s")
        print(f"  API calls:       {stats['api_calls']}")
        if stats["rate_limit_hits"] > 0:
            print(f"  Rate limit hits: {stats['rate_limit_hits']}")
        print("=" * 60)


if __name__ == "__main__":
    main()
