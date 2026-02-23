# phase1_discovery — Deterministic PDF Analysis

## Purpose

Phase 1 of the pipeline. Analyzes the PDF structure and extracts Table of Contents entries. No LLM calls — purely deterministic parsing.

## Scripts

| Script | What It Does | Output |
|--------|-------------|--------|
| `analyze_pdf.py` | Counts pages, identifies TOC regions, validates page offset | `intermediates/discovery.json` |
| `extract_toc.py` | Parses TOC pages using regex patterns from `spec_config.yaml` to extract section, table, and figure entries | `intermediates/toc_sections.json`, `toc_tables.json`, `toc_figures.json` |

## Config Dependencies

| Config Key | Used By | Value for This Spec |
|-----------|---------|---------------------|
| `spec.page_offset` | `analyze_pdf.py` | 12 |
| `spec.total_spec_pages` | `analyze_pdf.py` | 141 |
| `toc.sections.pages` | `extract_toc.py` | [4, 5, 6, 7, 8] (PDF pages 5–9, 0-indexed) |
| `toc.tables.pages` | `extract_toc.py` | [10, 11] (PDF pages 11–12) |
| `toc.figures.pages` | `extract_toc.py` | [9] (PDF page 10) |
| `toc.*.pattern` | `extract_toc.py` | Regex for section/table/figure entries |

## Current Output

- **194 sections** parsed from TOC
- **81 tables** parsed from TOC
- **47 figures** parsed from TOC

## Run Command

```powershell
python run_pipeline.py discover
```

## Notes

- The TOC regex patterns in `spec_config.yaml` are tuned for the Physical Layer PDF format (e.g., `Table 4-29` style IDs)
- Page offset = 12 means spec page 1 is PDF page 13 (1-indexed)
- TOC pages (iv–xi) are in the front matter before spec page 1
