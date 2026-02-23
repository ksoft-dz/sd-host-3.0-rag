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
| `spec.page_offset` | `analyze_pdf.py` | 22 |
| `spec.total_spec_pages` | `analyze_pdf.py` | 240 |
| `toc.sections.pages` | `extract_toc.py` | [4, 5, 6, 7, 8, 9, 10, 11, 12, 13] (PDF pages 5–14, 0-indexed) |
| `toc.tables.pages` | `extract_toc.py` | [16, 17, 18, 19] (PDF pages 17–20) |
| `toc.figures.pages` | `extract_toc.py` | [14, 15] (PDF pages 15–16) |
| `toc.*.pattern` | `extract_toc.py` | Regex for section/table/figure entries |

## Current Output

- **324 sections** parsed from TOC
- **177 tables** parsed from TOC
- **88 figures** parsed from TOC

## Run Command

```powershell
python run_pipeline.py discover
```

## Notes

- eMMC uses single-number IDs (`Table 1`, `Figure 1`) unlike SD specs (`Table 4-29`)
- `extract_toc.py` was modified to auto-detect 3-group (single-number) vs 4-group (chapter-seq) regex patterns
- Page offset = 22 means spec page 1 is PDF page 23 (1-indexed)
- TOC pages are in the front matter (pages iv–xxi) before spec page 1
- TOC entries use em-dash `—` separator and multiline format (title + newline + dots + page)
