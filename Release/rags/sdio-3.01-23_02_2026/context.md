# sdio_rag/_rag_v2 — Config-Driven RAG Pipeline

## What Is This?

A 3-phase extraction pipeline that turns a PDF specification into a structured knowledge graph (`metadata/metadata.json`). Everything is driven by `spec_config.yaml` — the scripts are generic; all spec-specific values live in config.

Currently configured for the **SDIO Simplified Specification Version 3.00** (SD Card Association, 90 PDF pages, 89 spec pages).

## Directory Layout

```
sdio_rag/_rag_v2/
├── spec_config.yaml       ← Central config (all domain-specific values)
├── run_pipeline.py        ← Pipeline orchestrator (CLI entry point)
├── phase1_discovery/      ← Phase 1: deterministic PDF analysis (no LLM)
├── phase2_extraction/     ← Phase 2: LLM-powered extraction (sections, tables, figures, domain)
├── phase3_assembly/       ← Phase 3: deterministic merge → metadata.json
├── shared/                ← Common utilities (config, LLM client, PDF, helpers)
├── intermediates/         ← All intermediate outputs (JSON, CSV, images, PlantUML)
└── metadata/              ← Final output + API + agent instructions
```

Source PDF: `sdio_rag/PartE1_SDIO_Simplified_Specification_Ver3.00.pdf`

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
cd sdio_rag/_rag_v2
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
| Registers | 2 (52 fields) — CCCR (44 fields), FBR (8 fields) |
| Register Classes | 2 — REGCLASS_CCCR, REGCLASS_FBR |
| Tables | 35 (CSV, 18 multi-page) |
| Figures | 21 (PlantUML) |
| Spec Chunks | 80 |
| Features | 52 |
| HD Sequences | 8 |
| **Total Nodes** | **200** |
| **Total Relations** | **189** |

## Key Design Principles

1. **Config over code** — Instead of tailoring scripts, add config parameters (`spec_config.yaml`)
2. **Intermediates are first-class** — Every phase writes JSON/CSV; nothing is ephemeral
3. **Incremental re-runs** — `--skip-existing` avoids re-extracting unchanged items
4. **LLM-agnostic phases** — Phase 1 and 3 are deterministic; only Phase 2 calls LLMs

## Key SDIO-Specific Notes

- **Chapter-seq IDs**: SDIO uses `TABLE_6_1`, `FIG_1_1` (same as SD Host Controller)
- **Page offset = 0**: Spec page numbers match PDF page numbers (1-indexed)
- **CCCR/FBR registers**: TABLE_6_1–6_4 were manually re-created from PDF text because the LLM vision extraction failed on the complex multi-page bit-field maps
  - TABLE_6_1.csv: 22 rows (CCCR register map, page 43)
  - TABLE_6_2.csv: 44 rows (CCCR bit definitions, pages 44-52, parsed from text)
  - TABLE_6_3.csv: 11 rows (FBR register map, page 53)
  - TABLE_6_4.csv: 8 rows (FBR bit definitions, pages 53-55)
- **Address-based registers**: SDIO defines registers by address (00h-16h for CCCR, n00h-nFFh for FBR), not bit positions within a single register. The parser was modified to handle missing `bit_range` columns.
- **TOC**: Text-based (pages 4-10), no PDF bookmarks. Appendix tables use `Table C- 1` format.
- **Appendices**: A (SD Mode Commands), B (SPI Mode Commands), C (Command/Response Lists), D (Constants)

## Dependencies

- Python 3.10+
- `anthropic` SDK (Claude API; needs `ANTHROPIC_API_KEY` env var)
- `PyMuPDF` (fitz) for PDF rendering
- `Pillow` for image manipulation
- `PyYAML` for config

## Relationship to Other RAGs

This pipeline is a **clone** of `_rag_v2/` (SD Host Controller 3.00). The scripts are identical with one modification: `extract_domain.py` was updated to handle register tables without a `bit_range` column (treats every row as its own field group). All spec-specific differences are captured in `spec_config.yaml`.
