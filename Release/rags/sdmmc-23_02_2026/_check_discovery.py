import json

with open('intermediates/discovery.json') as f:
    d = json.load(f)

print('=== ALL SECTIONS ===')
for s in d['toc']['sections']:
    print(f"  {s['section_number']:16s} p{s['spec_page']:3d}  {s.get('title','')[:60]}")
print(f"--- total: {len(d['toc']['sections'])}")

print('\n=== TABLES ===')
for t in d['toc']['tables']:
    print(f"  {t['id']:16s} p{t['definition_page']:3d}  {t['spec_reference']:12s} {t['title'][:55]}")
print(f"--- total: {len(d['toc']['tables'])}")

print('\n=== FIGURES (last 10) ===')
for fg in d['toc']['figures'][-10:]:
    print(f"  {fg['id']:16s} p{fg['definition_page']:3d}  {fg['spec_reference']:14s} {fg['title'][:55]}")
print(f"--- total: {len(d['toc']['figures'])}")
