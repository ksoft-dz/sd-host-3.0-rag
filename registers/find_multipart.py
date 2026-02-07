#!/usr/bin/env python3
"""Find multi-part tables that need to be merged."""
import json
from pathlib import Path

tables_file = Path(__file__).parent.parent / "tables" / "tables_page_map.json"
registers_file = Path(__file__).parent / "registers.json"

with open(tables_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

print("=== Multi-part tables (from tables_page_map) ===")
for t in data['tables']:
    title = t.get('title', '')
    if 'Part' in title or '(' in title:
        print(f"{t['id']}: {title}")

print("\n=== All TABLE_2_* tables (potential register tables) ===")
for t in data['tables']:
    tid = t['id']
    title = t.get('title', '')
    if tid.startswith('TABLE_2_') and 'Register' in title:
        print(f'    "{tid}": {{"offset": "???h", "name": "{title}"}},  # {title}')
