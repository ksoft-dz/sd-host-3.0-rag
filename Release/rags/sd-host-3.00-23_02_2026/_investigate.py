"""Investigate unmatched registers: find candidate tables for each."""
import json, sys
sys.path.insert(0, '_rag_v2')
from shared.utils import load_json

tables_map = load_json('intermediates/tables_page_map.json')
regs = load_json('intermediates/registers.json')

# The 4 unmatched registers
unmatched = [r for r in regs['registers'] if len(r.get('fields', [])) == 0]

# All register tables (title contains "register")
reg_tables = [t for t in tables_map['tables'] 
              if 'register' in t.get('title', '').lower()]

print("=== UNMATCHED REGISTERS ===")
for r in unmatched:
    name = r['name']
    main = name.lower().replace(' register', '').replace(' registers', '').strip()
    print(f"\n{r['id']} ({r['offset']}): {name}")
    print(f"  Search key: '{main}'")
    
    # Find candidates
    candidates = []
    for t in reg_tables:
        title = t['title'].lower()
        if main in title:
            candidates.append((t['id'], t['title'], 'exact'))
        else:
            main_words = set(main.split())
            title_words = set(title.lower().split())
            overlap = main_words & title_words
            if len(overlap) >= 2:
                candidates.append((t['id'], t['title'], f'overlap({overlap})'))
    
    if candidates:
        for tid, ttitle, method in candidates:
            print(f"  CANDIDATE: {tid} -- {ttitle} [{method}]")
    else:
        print(f"  NO CANDIDATES found")
        words = [w for w in main.split() if len(w) > 3]
        for w in words:
            matches = [(t['id'], t['title']) for t in reg_tables if w in t['title'].lower()]
            if matches:
                print(f"  Tables containing '{w}':")
                for tid, ttitle in matches:
                    print(f"    {tid}: {ttitle}")

print("\n\n=== ALL REGISTER TABLES ===")
for t in reg_tables:
    print(f"  {t['id']:16s} {t['title']}")
