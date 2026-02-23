# phase1_discovery — Deterministic PDF Analysis

## Purpose

Phase 1 of the pipeline. Analyzes the PDF structure without any LLM calls — purely deterministic (regex + PyMuPDF). Produces discovery data that all Phase 2 extractors depend on.

## Scripts

| Script | What It Does | Output |
|--------|-------------|--------|
| `analyze_pdf.py` | Extracts PDF metadata: page count, page offset validation, detected TOC regions | `intermediates/discovery.json` |
| `extract_toc.py` | Parses TOC pages for sections, tables, and figures using config-driven regex patterns. Also scans body pages for cross-references. | `intermediates/toc_sections.json`, `toc_tables.json`, `toc_figures.json` |

## Config Dependencies

From `spec_config.yaml`:
- `spec.pdf_path`, `spec.page_offset` (=11)
- `toc.pages`, `toc.patterns.section`, `toc.patterns.table`, `toc.patterns.figure`

## Key Notes

- **No LLM cost** — safe to re-run freely
- **Must run before Phase 2** — all extractors read `discovery.json` for page mappings
- Run via: `python run_pipeline.py discover`
