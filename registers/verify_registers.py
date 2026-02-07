#!/usr/bin/env python3
"""
Interactive register verification tool.
Shows one register at a time with all field details.
Press Enter to advance to the next register, 'q' to quit.
"""

import json
import sys
from pathlib import Path

REGISTERS_FILE = Path(__file__).parent / "registers.json"


def clear_screen():
    print("\033[2J\033[H", end="")


def format_field(field: dict, show_values: bool = True) -> str:
    """Format a single field for display."""
    bits = field.get("bits", "?")
    name = field.get("name", "Unknown")
    width = field.get("width", "?")
    access = field.get("access", "?")
    read_eff = field.get("read_effect", "none")
    write_eff = field.get("write_effect", "none")
    abstract = field.get("abstract", "")
    values = field.get("values", [])
    original = field.get("original_attrib", "")
    
    # Format access info
    access_parts = [access]
    if read_eff and read_eff != "none":
        access_parts.append(f"read:{read_eff}")
    if write_eff and write_eff != "none":
        access_parts.append(f"write:{write_eff}")
    access_str = ", ".join(access_parts)
    
    lines = []
    lines.append(f"  [{bits:>5}] {name}")
    lines.append(f"          Width: {width} bit(s)  |  Access: {access_str}")
    if original and original != access:
        lines.append(f"          Original: {original}")
    if abstract:
        # Wrap abstract at ~70 chars
        words = abstract.split()
        line = "          "
        for word in words:
            if len(line) + len(word) + 1 > 78:
                lines.append(line)
                line = "          " + word
            else:
                line += " " + word if line.strip() else word
        if line.strip():
            lines.append(line)
    
    if show_values and values:
        lines.append("          Values:")
        for v in values:
            code = v.get("code", "?")
            meaning = v.get("meaning", "?")
            lines.append(f"            {code:>8} = {meaning}")
    
    return "\n".join(lines)


def show_register(reg: dict, index: int, total: int):
    """Display a single register with all details."""
    clear_screen()
    
    offset = reg.get("offset", "???")
    name = reg.get("name", "Unknown")
    reg_id = reg.get("id", "?")
    section = reg.get("spec_section", "")
    table = reg.get("spec_table", "")
    merged_from = reg.get("merged_from")
    class_id = reg.get("class_id", "")
    fields = reg.get("fields", [])
    
    print("=" * 80)
    print(f"  REGISTER {index + 1} of {total}")
    print("=" * 80)
    print(f"  Offset:   {offset}")
    print(f"  Name:     {name}")
    print(f"  ID:       {reg_id}")
    print(f"  Section:  {section}")
    print(f"  Table:    {table}", end="")
    if merged_from:
        print(f"  (merged from: {', '.join(merged_from)})")
    else:
        print()
    if class_id:
        print(f"  Class:    {class_id}")
    print("-" * 80)
    print(f"  FIELDS ({len(fields)} total)")
    print("-" * 80)
    
    # Sort fields by bit position (high to low)
    sorted_fields = sorted(
        fields,
        key=lambda f: f.get("bit_high", 0) if f.get("bit_high") is not None else 0,
        reverse=True
    )
    
    for field in sorted_fields:
        print(format_field(field, show_values=True))
        print()
    
    print("=" * 80)
    print(f"  [{index + 1}/{total}] Press ENTER for next, 'b' for back, 'q' to quit, or number to jump")
    print("=" * 80)


def main():
    if not REGISTERS_FILE.exists():
        print(f"Error: {REGISTERS_FILE} not found. Run extract_registers.py first.")
        sys.exit(1)
    
    with open(REGISTERS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    registers = data.get("registers", [])
    
    # Sort by offset
    registers = sorted(
        registers,
        key=lambda r: int(r.get("offset", "0").replace("h", ""), 16) if r.get("offset") else 0
    )
    
    if not registers:
        print("No registers found.")
        sys.exit(1)
    
    total = len(registers)
    index = 0
    
    while True:
        show_register(registers[index], index, total)
        
        try:
            user_input = input().strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break
        
        if user_input == 'q':
            print("Exiting.")
            break
        elif user_input == 'b':
            index = max(0, index - 1)
        elif user_input == '':
            index = min(total - 1, index + 1)
            if index == total - 1 and user_input == '':
                # Already at last, ask if done
                pass
        elif user_input.isdigit():
            jump_to = int(user_input) - 1
            if 0 <= jump_to < total:
                index = jump_to
            else:
                print(f"Invalid index. Enter 1-{total}")
                input("Press Enter to continue...")
        else:
            # Any other key goes to next
            index = min(total - 1, index + 1)


if __name__ == "__main__":
    main()
