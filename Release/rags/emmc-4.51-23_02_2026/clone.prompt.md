# clone.prompt.md — How to Clone This RAG Pipeline for a New Spec

> **A step-by-step guide for adapting the generic `_rag_v2` RAG pipeline to any new PDF specification.**
> Based on lessons learned from cloning SD Host Controller 3.00 → SD Physical Layer 3.01 → eMMC 4.51.

---

## Overview

The `_rag_v2` pipeline is a config-driven, 3-phase extraction system that turns a PDF specification into a structured knowledge graph (`metadata.json`). The scripts are **generic** — all spec-specific values live in a single `spec_config.yaml` file.

To process a new spec, you:
1. Copy the pipeline scripts
2. Analyze the new PDF manually (offset, TOC pages)
3. Create a tailored `spec_config.yaml`
4. Run the pipeline
5. Fix any issues and re-run

---

## Prerequisites

### Software
- Python 3.10+
- `anthropic` SDK (`pip install anthropic`)
- `PyMuPDF` (`pip install pymupdf`)
- `Pillow` (`pip install Pillow`)
- `PyYAML` (`pip install pyyaml`)
- `ANTHROPIC_API_KEY` environment variable set

### Source Material
- The PDF specification you want to process
- Read access to an existing `_rag_v2` pipeline (to copy scripts from)

---

## Step-by-Step Process

### Step 1: Create Directory Structure

```powershell
mkdir <your_rag>/_rag_v2
mkdir <your_rag>/_rag_v2/shared
mkdir <your_rag>/_rag_v2/phase1_discovery
mkdir <your_rag>/_rag_v2/phase2_extraction
mkdir <your_rag>/_rag_v2/phase3_assembly
mkdir <your_rag>/_rag_v2/intermediates
mkdir <your_rag>/_rag_v2/metadata
```

### Step 2: Copy All Pipeline Scripts

Copy from an existing `_rag_v2/` — the scripts are generic:

```
run_pipeline.py
shared/config.py, llm_client.py, pdf_utils.py, data_classes.py, utils.py, __init__.py
phase1_discovery/analyze_pdf.py, extract_toc.py, __init__.py
phase2_extraction/extract_sections.py, extract_tables.py, extract_figures.py, extract_domain.py, validate.py, __init__.py
phase3_assembly/merge_metadata.py, __init__.py
metadata/metadata_api.py
```

> **Tip**: Copy from `emmc_rag/_rag_v2/` as it has the most up-to-date scripts with support for both single-number IDs (`Table 1`) and chapter-seq IDs (`Table 4-29`).

### Step 3: Analyze the New PDF

This is the most critical step. Open the PDF and determine:

#### 3a. Page Offset
```
page_offset = pdf_page_number − spec_page_number
```

| Example | Spec Page | PDF Page | Offset |
|---------|-----------|----------|--------|
| SD Host Controller 3.00 | 1 | 12 | 11 |
| SD Physical Layer 3.01 | 1 | 13 | 12 |
| eMMC 4.51 | 1 | 23 | 22 |

#### 3b. TOC Page Locations (0-indexed PDF pages)

#### 3c. TOC Regex Patterns — Check the ID format!
```yaml
# Chapter-seq IDs (SD Host, SD Physical Layer):
# "Table 4-29: Card State Transition Table ......... 45"
pattern: "Table\\s+(\\d+)[-.](\\d+)\\s*:?\\s*(.+?)\\.{3,}\\s*(\\d+)"

# Single-number IDs (eMMC):
# "Table 1 — e•MMC overview ..... 5"
pattern: "Table\\s+(\\d+)\\s*[—–]\\s*(.+?)\\n\\s*\\n?\\s*\\.{3,}\\s*(\\d+)"
```
> **Key**: Count the regex capture groups. 4 groups = chapter-seq, 3 groups = single-number. The `extract_toc.py` auto-detects this.

#### 3d. Domain: Registers, Features, HD Sequences
(Same as before — see detailed guide in existing clone.prompt.md)

### Step 4: Create `spec_config.yaml`

Use existing config as template. Key sections:

```yaml
spec:
  name: "Your Spec Name"
  version: "X.YZ"
  pdf_file: "your_spec.pdf"
  page_offset: NN
  total_spec_pages: NNN

toc:
  sections/tables/figures:
    pages: [...]
    pattern: "..."
```

### Step 5: Run the Pipeline

```powershell
python run_pipeline.py discover              # Phase 1 (~1s)
python run_pipeline.py extract-sections --model opus   # Phase 2a
python run_pipeline.py extract-tables --model opus     # Phase 2b
python run_pipeline.py extract-figures --model opus    # Phase 2c
python run_pipeline.py extract-domain --model opus     # Phase 2d
python run_pipeline.py validate --model haiku          # Phase 2e
python run_pipeline.py merge                           # Phase 3
```

### Step 6: Verify API

```powershell
python <your_rag>/_rag_v2/metadata/metadata_api.py get_spec_info
python <your_rag>/_rag_v2/metadata/metadata_api.py search_nodes "some keyword"
python <your_rag>/_rag_v2/metadata/metadata_api.py get_coverage_summary
```

### Step 7: Create Documentation

- `metadata/agent_instructions.md`
- `context.md` in each subdirectory
- This `clone.prompt.md`

---

## Performance Reference

| Phase | SD Phy (153pp) | eMMC (264pp) | Notes |
|-------|----------------|--------------|-------|
| Phase 1 Discovery | ~0.3s | ~0.9s | Free |
| Phase 2a Sections (opus) | ~3 min | ~5 min | |
| Phase 2b Tables (opus) | ~12.5 min | ~26 min | More tables in eMMC |
| Phase 2c Figures (opus) | ~10 min | ~18 min | |
| Phase 2d Domain (opus) | ~7 min | ~7.5 min | |
| Phase 2e Validation (haiku) | ~1s | ~2s | |
| Phase 3 Merge | instant | instant | |
| **Total** | **~33 min** | **~57 min** | |

---

## Lessons Learned

### Single-Number vs Chapter-Seq IDs
- SD specs use `Table 4-29` → ID `TABLE_4_29`
- eMMC uses `Table 1` → ID `TABLE_1`
- The pipeline auto-detects based on regex capture group count (3 vs 4)
- `utils.py` tries chapter-seq format first, falls back to single-number

### Multiline TOC Entries
- Some specs have TOC entries spanning multiple lines (title on one line, dots+page on next)
- Use `re.DOTALL` flag and explicit `\n` in regex patterns

### Large Tables
- eMMC Extended CSD spans many pages — set `max_pages_after: 4` or higher
- Some tables may produce single-row CSVs (header only) — check validation warnings

---

*When in doubt, run `python run_pipeline.py status` to check pipeline state.*
