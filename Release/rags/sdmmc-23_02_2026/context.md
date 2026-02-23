# SDMMC RAG — Context

## Overview

This RAG covers the **SDMMC (3MCR) controller** from the **SPC58 H-Line Reference Manual** (RM0452 Rev 4, June 2021). The SDMMC is a multi-card reader controller implementing the **SD Host Controller 3.0** standard with **MMC 4.51** support.

## Source Material

- **Full RM**: `rm0452-spc58-h-line--32-bit-power-architecture-automotive-mcu-triple-z4-cores-200-mhz-10-mbytes-flash-hsm-asild-stmicroelectronics.pdf` (3897 pages)
- **Extracted chapter**: `sdmmc_chapter_57.pdf` (81 pages, Section 57, pages 2849-2929 of original)

## Pipeline

Built using the RAG V2 config-driven pipeline (`_rag_v2/`), cloned from `sd_phy_rag/_rag_v2/`. Discovery phase was custom (no TOC pages in extracted PDF) — see `scripts/discover_sdmmc.py`.

### Pipeline phases run:
1. **Discovery** — custom script scanning page content (82 sections, 59 tables, 57 figures)
2. **Extract Sections** — LLM (opus), 81 chunks, ~2 min
3. **Extract Tables** — LLM vision (opus), 59/59 tables → CSV, ~12 min
4. **Extract Figures** — LLM vision (opus), 57/57 figures → PlantUML, ~13 min
5. **Extract Domain** — LLM (opus), 43 registers (91 fields), 40 features, 7 HD sequences, ~13 min
6. **Validate** — 14 errors (zero-field registers), 98 warnings (missing access types)
7. **Merge** — 294 nodes, 101 relations → `metadata/metadata.json`
8. **rm_raw_content** — 149 chunks from full 3897-page RM (per-chapter, ~889K words)

### Total pipeline time: ~43 minutes (extraction phases)

## Known Limitations

1. **10 registers with 0 fields**: Some register tables had page-assignment issues (LLM got wrong page image due to multi-page detection) or unusual CSV format. Affected: REG_020 (Data Port), REG_02B (Wakeup Control), REG_02C (Clock Control), REG_02E (Timeout Control), REG_036 (Error Int Status Enable), REG_03A (Error Int Signal Enable), REG_040 (Capabilities [31:0]), REG_04C (MaxCurrentCap [63:32]), REG_050 (Force Event Auto CMD), REG_054 (ADMA Error Status).

2. **Missing access types**: The LLM-generated CSVs use a 2-column format (Field, Description) merging bit range + field name — access type column (R/W/RO/etc.) is absent.

3. **Page numbering**: The extracted PDF has relative page numbers (1-81) but the page text still shows original RM page numbers (2849/3897, etc.).

## File Structure

```
sdmmc_rag/
├── sdmmc_chapter_57.pdf          # Extracted 81-page PDF
├── rm0452-spc58-h-line-...pdf    # Full 3897-page RM
└── _rag_v2/
    ├── spec_config.yaml          # Pipeline configuration
    ├── run_pipeline.py           # Pipeline orchestrator
    ├── agent_instructions.md     # Agent usage guide
    ├── context.md                # This file
    ├── metadata/
    │   └── metadata.json         # Final RAG output (294 nodes, 101 relations + rm_raw_content)
    ├── intermediates/
    │   ├── discovery.json        # TOC discovery results
    │   ├── sections.json         # Extracted section chunks
    │   ├── tables_page_map.json  # Table metadata
    │   ├── figures_page_map.json # Figure metadata
    │   ├── registers.json        # Register + field definitions
    │   ├── features.json         # Features + HD sequences
    │   ├── validation_report.json# Validation results
    │   ├── rm_raw_content.json   # Raw RM chunks
    │   ├── tables_csv/           # 59 CSV files
    │   ├── tables_images/        # Table page images
    │   ├── figures_plantuml/     # 57 PlantUML files
    │   └── figures_images/       # Figure page images
    ├── scripts/
    │   ├── discover_sdmmc.py     # Custom discovery (no TOC pages)
    │   ├── build_rm_raw_content.py # RM raw text chunk builder
    │   └── add_rm_raw_content.py # Merge rm_raw_content into metadata
    ├── phase1_discovery/         # Discovery phase code
    ├── phase2_extraction/        # Extraction phase code
    ├── phase3_assembly/          # Merge phase code
    └── shared/                   # Shared utilities
```

## Section Outline (Chapter 57)

| Section | Title | Pages |
|---------|-------|-------|
| 57.1 | Features | 1-2 |
| 57.2 | Architecture | 2-8 |
| 57.2.2 | Host controller core block description | 3-6 |
| 57.2.3 | Clocks | 6-7 |
| 57.3 | Registers | 8-65 |
| 57.3.1 | Registers memory map | 8-10 |
| 57.3.2 | Registers description (57.3.2.1–57.3.2.44) | 10-65 |
| 57.4 | Driver flow sequence | 66-78 |
| 57.4.1 | Non-DMA transaction | 66-69 |
| 57.4.2 | DMA transaction | 69-72 |
| 57.4.3 | ADMA transactions | 72-74 |
| 57.4.4 | Abort transaction | 74-76 |
| 57.4.5 | Boot operation | 76-78 |
| 57.5 | Timing | 79-81 |
