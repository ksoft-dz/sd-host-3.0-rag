# sd_phy_rag/_rag_v2 — Config-Driven RAG Pipeline

## What Is This?

A 3-phase extraction pipeline that turns a PDF specification into a structured knowledge graph (`metadata/metadata.json`). Everything is driven by `spec_config.yaml` — the scripts are generic; all spec-specific values live in config.

Currently configured for the **SD Physical Layer Simplified Specification v3.01** (153 pages, 141 spec pages).

## Directory Layout

```
sd_phy_rag/_rag_v2/
├── spec_config.yaml       ← Central config (all domain-specific values)
├── run_pipeline.py        ← Pipeline orchestrator (CLI entry point)
├── phase1_discovery/      ← Phase 1: deterministic PDF analysis (no LLM)
├── phase2_extraction/     ← Phase 2: LLM-powered extraction (sections, tables, figures, domain)
├── phase3_assembly/       ← Phase 3: deterministic merge → metadata.json
├── shared/                ← Common utilities (config, LLM client, PDF, helpers)
├── intermediates/         ← All intermediate outputs (JSON, CSV, images, PlantUML)
└── metadata/              ← Final output + API + agent instructions
```

Source PDF: `sd_phy_rag/Part_1_Physical_Layer_Simplified_Specification_Ver_3.01_Final_100518.pdf`

## Pipeline Flow

```
Phase 1: Discovery (free, no LLM)
  analyze_pdf.py   → intermediates/discovery.json
  extract_toc.py   → intermediates/toc_sections.json, toc_tables.json, toc_figures.json

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
cd sd_phy_rag/_rag_v2
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
| Registers | 5 (35 fields) — CID, CSD structure, CSD v1.0, OCR, SCR |
| Register Classes | 5 |
| Tables | 81 (CSV) |
| Figures | 47 (PlantUML) |
| Spec Chunks | 141 |
| Features | 46 |
| HD Sequences | 9 |
| **Total Nodes** | **~334** |
| **Total Relations** | **~297** |

## Key Design Principles

1. **Config over code** — Instead of tailoring scripts, add config parameters (`spec_config.yaml`)
2. **Intermediates are first-class** — Every phase writes JSON/CSV; nothing is ephemeral
3. **Incremental re-runs** — `--skip-existing` avoids re-extracting unchanged items
4. **LLM-agnostic phases** — Phase 1 and 3 are deterministic; only Phase 2 calls LLMs

## Dependencies

- Python 3.10+
- `anthropic` SDK (Claude API; needs `ANTHROPIC_API_KEY` env var)
- `PyMuPDF` (fitz) for PDF rendering
- `Pillow` for image manipulation
- `PyYAML` for config

## Relationship to SD Host Controller RAG

This pipeline is a **clone** of `_rag_v2/` (SD Host Controller 3.00). The scripts are identical except for 3 hardcoded-reference fixes in `extract_domain.py` and `merge_metadata.py`. All spec-specific differences are captured in `spec_config.yaml`.
