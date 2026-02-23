# emmc_rag/_rag_v2 — Config-Driven RAG Pipeline

## What Is This?

A 3-phase extraction pipeline that turns a PDF specification into a structured knowledge graph (`metadata/metadata.json`). Everything is driven by `spec_config.yaml` — the scripts are generic; all spec-specific values live in config.

Currently configured for the **Embedded Multimedia Card (e•MMC) Electrical Standard v4.51** (JESD84-B451, 264 PDF pages, 240 spec pages).

## Directory Layout

```
emmc_rag/_rag_v2/
├── spec_config.yaml       ← Central config (all domain-specific values)
├── run_pipeline.py        ← Pipeline orchestrator (CLI entry point)
├── phase1_discovery/      ← Phase 1: deterministic PDF analysis (no LLM)
├── phase2_extraction/     ← Phase 2: LLM-powered extraction (sections, tables, figures, domain)
├── phase3_assembly/       ← Phase 3: deterministic merge → metadata.json
├── shared/                ← Common utilities (config, LLM client, PDF, helpers)
├── intermediates/         ← All intermediate outputs (JSON, CSV, images, PlantUML)
└── metadata/              ← Final output + API + agent instructions
```

Source PDF: `emmc_rag/JESD84-B451.pdf`

## Pipeline Flow

```
Phase 1: Discovery (free, no LLM)
  analyze_pdf.py   → intermediates/discovery.json

Phase 2: Extraction (LLM-powered, parallelized)
  2a  extract_sections.py → intermediates/sections.json
  2b  extract_tables.py   → intermediates/tables_page_map.json + tables_csv/*.csv
  2c  extract_figures.py  → intermediates/figures_page_map.json + figures_plantuml/*.puml
  2d  extract_domain.py   → intermediates/registers.json + features.json
  2e  validate.py         → intermediates/validation_report.json

Phase 3: Assembly (deterministic, no LLM)
  merge_metadata.py → metadata/metadata.json
```

## Quick Commands

```powershell
cd emmc_rag/_rag_v2
python run_pipeline.py all               # Full pipeline
python run_pipeline.py discover           # Phase 1 only
python run_pipeline.py extract-tables     # Just tables
python run_pipeline.py extract-domain     # Registers + features
python run_pipeline.py validate           # Sanity checks
python run_pipeline.py merge             # Assemble final metadata
python run_pipeline.py status            # Check pipeline state
```

Options: `--model haiku|sonnet|opus`, `--skip-existing`, `--workers N`

## Current Output

| Resource | Count |
|----------|-------|
| Registers | 5 (113 fields) — OCR, CID, CSD Structure, Extended CSD, DSR |
| Register Classes | 5 |
| Tables | 177 (CSV, 42 multi-page) |
| Figures | 88 (PlantUML) |
| Spec Chunks | 241 |
| Features | 59 |
| HD Sequences | 11 |
| **Total Nodes** | **586** |
| **Total Relations** | **518** |

## Key Design Principles

1. **Config over code** — Instead of tailoring scripts, add config parameters (`spec_config.yaml`)
2. **Intermediates are first-class** — Every phase writes JSON/CSV; nothing is ephemeral
3. **Incremental re-runs** — `--skip-existing` avoids re-extracting unchanged items
4. **LLM-agnostic phases** — Phase 1 and 3 are deterministic; only Phase 2 calls LLMs

## Key eMMC-Specific Notes

- **Single-number IDs**: eMMC uses `TABLE_1`, `FIG_1` (not chapter-seq `TABLE_4_29`)
- **Extended CSD**: Table 82 is exceptionally large (spans many pages), set `max_pages_after: 4`
- **Page offset = 22**: spec page 1 is PDF page 23 (1-indexed)
- **Card registers**: Use pseudo-offsets (001h–006h) for pipeline compatibility

## Dependencies

- Python 3.10+
- `anthropic` SDK (Claude API; needs `ANTHROPIC_API_KEY` env var)
- `PyMuPDF` (fitz) for PDF rendering
- `Pillow` for image manipulation
- `PyYAML` for config

## Relationship to Other RAGs

This pipeline is a **clone** of `sd_phy_rag/_rag_v2/` (SD Physical Layer 3.01), which was itself cloned from `_rag_v2/` (SD Host Controller 3.00). The scripts were adapted to support single-number table/figure IDs in `extract_toc.py`, `utils.py`, and `extract_tables.py`. All spec-specific differences are captured in `spec_config.yaml`.
