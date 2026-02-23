# phase3_assembly — Deterministic Merge

## Purpose

Phase 3 of the pipeline. Combines all Phase 2 intermediates into the final unified `metadata/metadata.json` knowledge graph. Purely deterministic — no LLM calls.

## Scripts

| Script | What It Does | Output |
|--------|-------------|--------|
| `merge_metadata.py` | Reads all intermediate JSON files, builds nodes + relations, validates cross-references, writes unified metadata | `metadata/metadata.json` |

## What It Merges

| Source | Node Types | Count |
|--------|-----------|-------|
| `intermediates/tables_page_map.json` | TABLE | 177 |
| `intermediates/figures_page_map.json` | FIGURE | 88 |
| `intermediates/sections.json` | SPEC_CHUNK | 241 |
| `intermediates/registers.json` | REGISTER (6) + REG_CLASS (5) | 11 |
| `intermediates/features.json` | FEATURE (59) + HD_SEQUENCE (11) | 70 |

## Relations Built

- `BELONGS_TO` — Register → REG_CLASS
- `DEFINED_BY` — Register → Table
- `CHILD_OF` — Section hierarchy
- `PART_OF` — Feature → parent Feature
- `REFERENCES` — Cross-references from keyword/ID matching

## Key Behaviors

- **Auto-backup**: Before overwriting, backs up existing `metadata.json` to `metadata/backups/metadata_YYYYMMDDTHHMMSS.json`
- **Validation pass**: Checks for dangling references, duplicate IDs
- **Idempotent**: Safe to re-run; always rebuilds from intermediates

## Run Command

```powershell
python run_pipeline.py merge
```

## Notes

- Fixed hardcoded `TABLE_1_1` reference from original SD Host Controller pipeline — now reads `source_table` from register config dynamically
- Fixed hardcoded `version_support` — now uses `rc.get("version_support", {})` for specs that may not have version support fields
