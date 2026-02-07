#!/usr/bin/env python3
"""
Dump registers and fields in a human-readable format for manual verification.
"""

import json
import argparse
from pathlib import Path

REGISTERS_FILE = Path(__file__).parent / "registers.json"


def dump_registers(show_values: bool = False, show_raw: bool = False):
    """Dump all registers and fields."""
    
    if not REGISTERS_FILE.exists():
        print(f"Error: {REGISTERS_FILE} not found. Run extract_registers.py first.")
        return
    
    with open(REGISTERS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    meta = data.get("_metadata", {})
    print("=" * 80)
    print("SD Host Controller 3.0 - Register Summary")
    print("=" * 80)
    print(f"Total Registers: {meta.get('total_registers', 0)}")
    print(f"Total Fields:    {meta.get('total_fields', 0)}")
    print("=" * 80)
    
    # Sort registers by offset
    registers = sorted(data.get("registers", []), 
                       key=lambda r: int(r.get("offset", "0").replace("h", ""), 16) if r.get("offset") else 0)
    
    for reg in registers:
        reg_id = reg.get("id", "?")
        name = reg.get("name", "Unknown")
        offset = reg.get("offset", "???")
        section = reg.get("spec_section", "")
        table = reg.get("spec_table", "")
        merged_from = reg.get("merged_from")
        fields = reg.get("fields", [])
        
        print(f"\n{'─' * 80}")
        print(f"[{offset}] {name}")
        table_info = f"Table: {table}"
        if merged_from:
            table_info += f" (merged from {', '.join(merged_from)})"
        print(f"  ID: {reg_id}  |  Section: {section}  |  {table_info}")
        print(f"  Fields: {len(fields)}")
        print(f"{'─' * 80}")
        
        # Sort fields by bit position (high to low)
        sorted_fields = sorted(fields, 
                               key=lambda f: f.get("bit_high", 0) if f.get("bit_high") is not None else 0,
                               reverse=True)
        
        for field in sorted_fields:
            bits = field.get("bits", "?")
            fname = field.get("name", "?")
            width = field.get("width", "?")
            access = field.get("access", "?")
            read_eff = field.get("read_effect", "none")
            write_eff = field.get("write_effect", "none")
            abstract = field.get("abstract", "")
            values = field.get("values", [])
            
            # Format access info
            access_str = access
            if read_eff != "none":
                access_str += f", read:{read_eff}"
            if write_eff != "none":
                access_str += f", write:{write_eff}"
            
            print(f"  [{bits:>5}] {fname:<40} ({width}b, {access_str})")
            print(f"          {abstract}")
            
            if show_values and values:
                for v in values:
                    print(f"            {v.get('code', '?'):>10} = {v.get('meaning', '?')}")
            
            if show_raw:
                raw = field.get("raw", "")
                if raw and len(raw) > 100:
                    raw = raw[:100] + "..."
                print(f"          RAW: {raw}")
    
    print(f"\n{'=' * 80}")
    print(f"Total: {len(registers)} registers, {meta.get('total_fields', 0)} fields")
    print("=" * 80)


def dump_summary():
    """Dump just register names and field counts."""
    
    if not REGISTERS_FILE.exists():
        print(f"Error: {REGISTERS_FILE} not found.")
        return
    
    with open(REGISTERS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"{'Offset':<8} {'Fields':>6}  {'Register Name'}")
    print("-" * 70)
    
    registers = sorted(data.get("registers", []), 
                       key=lambda r: int((r.get("offset") or "0").replace("h", ""), 16))
    
    total_fields = 0
    for reg in registers:
        offset = reg.get("offset") or "???"
        name = reg.get("name") or "Unknown"
        fields = len(reg.get("fields", []))
        total_fields += fields
        print(f"{offset:<8} {fields:>6}  {name}")
    
    print("-" * 70)
    print(f"{'TOTAL':<8} {total_fields:>6}  {len(registers)} registers")


def main():
    parser = argparse.ArgumentParser(description="Dump registers for manual verification")
    parser.add_argument("--summary", "-s", action="store_true", help="Show only register names and field counts")
    parser.add_argument("--values", "-V", action="store_true", help="Show enumerated values")
    parser.add_argument("--raw", "-r", action="store_true", help="Show raw text (truncated)")
    args = parser.parse_args()
    
    if args.summary:
        dump_summary()
    else:
        dump_registers(show_values=args.values, show_raw=args.raw)


if __name__ == "__main__":
    main()
