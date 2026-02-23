# phase2_extraction — LLM-Powered Content Extraction

## Purpose

Phase 2 of the pipeline. Uses Claude (Anthropic) to extract structured content from the PDF. Each sub-phase is independent and can be run/re-run separately.

## Scripts

| Script | Phase | What It Does | Output |
|--------|-------|-------------|--------|
| `extract_sections.py` | 2a | Reads PDF page-by-page, chunks text at ~200 words, uses LLM for abstracts/keywords | `intermediates/sections.json` |
| `extract_tables.py` | 2b | Renders table pages as images, sends to LLM vision for CSV extraction. Handles multi-page tables (config-driven stitching) and extraction hints. | `intermediates/tables_page_map.json` + `tables_csv/*.csv` |
| `extract_figures.py` | 2c | Renders figure pages, sends to LLM vision for PlantUML transcription + abstract | `intermediates/figures_page_map.json` + `figures_plantuml/*.puml` |
| `extract_domain.py` | 2d | Parses table CSVs to extract register fields (with LLM abstracts). Builds feature/HD-sequence skeletons from config, enriches with LLM descriptions. | `intermediates/registers.json`, `intermediates/features.json` |
| `validate.py` | 2e | Rule-based sanity checks on extracted data (no LLM). Reports zero-field registers, suspicious field names, empty CSVs, etc. | `intermediates/validation_report.json` |

## Current Output

| Sub-phase | Result |
|-----------|--------|
| 2a Sections | 324 sections → 241 chunks |
| 2b Tables | 177 tables CSV (42 multi-page detected, 33 with hints) |
| 2c Figures | 88 figures PlantUML |
| 2d Domain | 5 registers (113 fields), 59 features, 11 HD sequences |
| 2e Validation | 0 errors, 10 warnings (missing access types, single-row tables) |

## Config-Driven Features

- **Multi-page table detection**: `extraction.tables.multi_page` — auto-detects tables spanning multiple PDF pages, stitches images. `max_pages_after: 4` for Extended CSD.
- **Extraction hints**: `extraction.tables.hints` — injects LLM prompt instructions for specific table patterns (e.g., register field format, ext_csd_table, command tables)
- **Table overrides**: `domain.registers.register_offsets[].table` — explicit table-to-register mapping (used for all 6 card registers)
- **Validation rules**: `validation.checks` — configurable severity/thresholds for each check type

## Dependencies

- Phase 1 must complete first (`discovery.json` required)
- 2a–2c are independent of each other (can run in parallel)
- 2d depends on 2b (needs table CSVs)
- 2e depends on 2b–2d (validates their outputs)

## Run Commands

```powershell
python run_pipeline.py extract-sections    # 2a
python run_pipeline.py extract-tables      # 2b
python run_pipeline.py extract-figures     # 2c
python run_pipeline.py extract-domain      # 2d
python run_pipeline.py validate            # 2e
```

Options: `--model haiku|sonnet|opus`, `--skip-existing`, `--workers N`

## LLM Model Guidance

- **Sections (2a)**: Use opus for high-quality abstracts
- **Tables (2b)**: Use opus for accurate CSV extraction (especially multi-page)
- **Figures (2c)**: Use opus for PlantUML fidelity
- **Domain (2d)**: Use opus for register field parsing and feature descriptions
- **Validation (2e)**: Use haiku (rule-based, no semantic work)

## Notes on eMMC Card Registers

The eMMC spec defines card registers (OCR, CID, CSD, Extended CSD, DSR) that are NOT memory-mapped host controller registers. They use pseudo-offsets (001h–006h) in `spec_config.yaml` for pipeline compatibility. Some registers (CID, CSD Fields, Extended CSD, DSR) have zero extracted fields due to complex table formats — this is expected and reported as validation errors.
