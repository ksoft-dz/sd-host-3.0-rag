# clone.prompt.md — How to Clone This RAG Pipeline for a New Spec

> **A step-by-step guide for adapting the generic `_rag_v2` RAG pipeline to any new PDF specification.**
> Based on lessons learned from cloning SD Host Controller 3.00 → SD Physical Layer 3.01.

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

> **Known hardcoded references to fix** (as of the SD Host Controller → Physical Layer clone):
> - `extract_domain.py`: had hardcoded `"SD Host Controller"` — should use `config["spec"]["name"]`
> - `extract_domain.py`: `_enrich_feature()` needed `config` parameter added
> - `merge_metadata.py`: had hardcoded `TABLE_1_1` and `version_support` — should use dynamic lookups
>
> **Tip**: Search the copied scripts for any references to the old spec (name, specific table IDs, etc.) and parametrize them through `spec_config.yaml`.

### Step 3: Analyze the New PDF

This is the most critical step. Open the PDF and determine:

#### 3a. Page Offset
The offset between spec page numbers and PDF page numbers:
```
page_offset = pdf_page_number − spec_page_number
```

**How to find it**: Go to a page where the spec page number is visible (e.g., "Page 1" or the first content page). Note the actual PDF page number. The difference is your offset.

| Example | Spec Page | PDF Page | Offset |
|---------|-----------|----------|--------|
| SD Host Controller 3.00 | 1 | 12 | 11 |
| SD Physical Layer 3.01 | 1 | 13 | 12 |

#### 3b. TOC Page Locations
Find the Table of Contents pages (0-indexed for PDF page numbers):

- **Sections TOC**: Which PDF pages list chapter/section entries?
- **Tables TOC**: Which PDF pages list "Table X-Y: Title" entries?
- **Figures TOC**: Which PDF pages list "Figure X-Y: Title" entries?

> **Tip**: TOC pages are usually in the front matter (Roman numeral pages). Count them from the start of the PDF.

#### 3c. TOC Regex Patterns
Look at the actual TOC text format and write regex patterns:
```yaml
# Section: "4.2.1  Card Identification Mode ..... 23"
pattern: "^(\\d+(?:\\.\\d+)*)\\.?\\s+(.+?)\\s*\\.{3,}\\s*(\\d+)"

# Table: "Table 4-29: Card State Transition Table ......... 45"
pattern: "Table\\s+(\\d+)[-.](\\d+)\\s*:?\\s*(.+?)\\.{3,}\\s*(\\d+)"

# Figure: "Figure 2-1: SD Memory Card Block Diagram ..... 12"
pattern: "Figure\\s+(\\d+)[-.](\\d+)\\s*:?\\s*(.+?)\\.{3,}\\s*(\\d+)"
```

#### 3d. Domain: Registers
Identify what registers the spec defines:

- **Memory-mapped registers** (like SD Host Controller): Use actual offsets (028h, 030h, etc.)
- **Card registers** (like SD Physical Layer): Use pseudo-offsets (001h, 002h, etc.) for pipeline compatibility
- For each register: which table defines its fields? (used in `register_offsets[].table`)

Also identify **register classes** (logical groupings) and **tables to exclude** from register auto-detection.

#### 3e. Domain: Features
List the key features/capabilities the spec defines. For each:
- Unique ID (`F_CARD_INIT`)
- Name
- Functional group(s)
- Priority (P0/P1/P2)
- Parent feature (for hierarchy)

#### 3f. Domain: HD Sequences
Identify host-driver sequences (step-by-step operational procedures):
- Unique ID (`HDS_CARD_INIT`)
- Name
- Primary spec section

### Step 4: Create `spec_config.yaml`

Use the existing config as a template. Key sections to customize:

```yaml
spec:
  name: "Your Spec Name"
  version: "X.YZ"
  pdf_file: "your_spec.pdf"           # Relative to the _rag_v2 parent directory
  page_offset: NN                      # From Step 3a
  total_spec_pages: NNN                # Last numbered spec page

toc:
  sections:
    pages: [N, N+1, ...]              # 0-indexed PDF pages (from Step 3b)
    pattern: "..."                     # From Step 3c
  tables:
    pages: [N, ...]
    pattern: "..."
    id_format: "TABLE_{chapter}_{seq}"
  figures:
    pages: [N, ...]
    pattern: "..."
    id_format: "FIG_{chapter}_{seq}"

domain:
  registers:
    classes: [...]                     # From Step 3d
    register_offsets: {...}
    exclude_tables: [...]

  features:
    definitions: [...]                 # From Step 3e
    hd_sequences: [...]               # From Step 3f
```

> **Copy the rest of the config** (node_types, chunking, llm, extraction, validation, relation_types) from the existing config — these are generic and rarely need changes.

### Step 5: Run the Pipeline

Run each phase sequentially and verify output:

```powershell
cd <your_rag>/_rag_v2

# Phase 1: Free, fast (~1s)
python run_pipeline.py discover
# Check: intermediates/discovery.json — verify page count, offset
# Check: toc_sections.json — verify section count looks right

# Phase 2a: Sections (opus recommended)
python run_pipeline.py extract-sections --model opus
# Check: intermediates/sections.json — verify chunk count

# Phase 2b: Tables (opus recommended, takes ~10-15 min)
python run_pipeline.py extract-tables --model opus
# Check: intermediates/tables_csv/ — spot-check a few CSVs

# Phase 2c: Figures (opus recommended, takes ~10-15 min)
python run_pipeline.py extract-figures --model opus
# Check: intermediates/figures_plantuml/ — spot-check a few .puml files

# Phase 2d: Domain (opus for semantic enrichment)
python run_pipeline.py extract-domain --model opus
# Check: intermediates/registers.json — verify field counts
# Check: intermediates/features.json — verify feature descriptions

# Phase 2e: Validation (haiku is fine — rule-based)
python run_pipeline.py validate --model haiku
# Check: intermediates/validation_report.json — review errors/warnings

# Phase 3: Merge (free, instant)
python run_pipeline.py merge
# Check: metadata/metadata.json — verify total node/relation counts
```

### Step 6: Verify the API

```powershell
python <your_rag>/_rag_v2/metadata/metadata_api.py get_spec_info
python <your_rag>/_rag_v2/metadata/metadata_api.py search_nodes "some keyword"
python <your_rag>/_rag_v2/metadata/metadata_api.py get_coverage_summary
```

### Step 7: Create Documentation

Create these files for agent discoverability:
- `metadata/agent_instructions.md` — API reference (adapt from existing)
- `context.md` in each subdirectory — brief directory purpose + contents
- This `clone.prompt.md` — if you want future clonability

---

## Lessons Learned (SD Host → Physical Layer Clone)

### LLM Model Selection
| Task Type | Recommended Model | Why |
|-----------|-------------------|-----|
| Semantic extraction (abstracts, descriptions) | **opus** | Higher quality, fewer errors |
| CSV extraction from table images | **opus** | Complex multi-page tables need best vision |
| Figure → PlantUML transcription | **opus** | Fidelity matters for diagrams |
| Rule-based validation | **haiku** | No semantic work, just checks |
| Pure static/sequential tasks | **haiku** | Cost-effective for simple processing |
| Middle reasoning tasks | **sonnet** | Good balance for moderate complexity |

> **Key rule**: Never use haiku for tasks requiring understanding of spec content. Use opus for anything that generates human-readable text or parses visual content.

### Common Pitfalls

1. **Hardcoded spec references in pipeline scripts**
   - Before running, search copied scripts for any references to the old spec name, specific table IDs, or magic numbers
   - Parametrize them through `spec_config.yaml` instead

2. **Card registers vs. memory-mapped registers**
   - Not all specs have memory-mapped registers with hex offsets
   - Use pseudo-offsets for non-addressable registers (e.g., card register CID → 001h)
   - Expect some validation errors for unusual register table formats

3. **TOC regex patterns**
   - Different specs format their TOC entries differently (dash vs. period separators, with/without colon, etc.)
   - Test the regex against actual PDF text before running the pipeline
   - Use `python -c "import fitz; doc=fitz.open('spec.pdf'); print(doc[PAGE].get_text())"` to inspect raw page text

4. **Multi-page tables**
   - The pipeline auto-detects multi-page tables by checking for table content continuation
   - For specs with very long tables, you may need to increase `max_pages_before`/`max_pages_after` in config
   - The SD Physical Layer spec had 29 out of 81 tables spanning multiple pages

5. **Page offset verification**
   - Always double-check by looking up a known table/figure in the PDF
   - A wrong offset means ALL extracted page references will be incorrect
   - Verify: `pdf_page = spec_page + page_offset` (1-indexed)

6. **Feature catalog design**
   - The feature list is the hardest part to design well
   - Start by reading the spec's TOC to identify major functional areas
   - Group features by chapter/topic
   - Use P0 for must-have features, P1 for important, P2 for nice-to-have
   - Create parent-child hierarchies for related features

7. **Background terminal CWD**
   - When running pipeline from background terminals, always use full paths
   - Background shells may lose their working directory

### Performance Reference (SD Physical Layer 3.01)

| Phase | Duration | Notes |
|-------|----------|-------|
| Phase 1 Discovery | ~0.3s | Free, no LLM |
| Phase 2a Sections (opus) | ~3 min | 194 sections → 141 chunks |
| Phase 2b Tables (opus) | ~12.5 min | 81 tables, 29 multi-page |
| Phase 2c Figures (opus) | ~10 min | 47 figures |
| Phase 2d Domain (opus) | ~7 min | 5 registers, 46 features, 9 HD sequences |
| Phase 2e Validation (haiku) | ~1s | Rule-based checks |
| Phase 3 Merge | instant | Deterministic assembly |
| **Total** | **~33 min** | Mostly API wait time |

### Cost Estimate
- Opus API calls for a ~150-page spec with ~80 tables and ~50 figures: approximately $5–15 USD depending on table complexity and multi-page stitching.

---

## Quick Reference: Config Sections

| Section | What to Customize | How to Figure It Out |
|---------|-------------------|----------------------|
| `spec.name` | Spec title | Read the PDF title page |
| `spec.version` | Spec version | Read the PDF title page |
| `spec.pdf_file` | Relative path to PDF | Place PDF next to `_rag_v2/` folder |
| `spec.page_offset` | Page numbering offset | Compare spec page 1 with PDF page number |
| `spec.total_spec_pages` | Last page number | Look at last numbered page in spec |
| `toc.*.pages` | 0-indexed PDF pages | Count from start of PDF to TOC sections |
| `toc.*.pattern` | Regex for TOC lines | Inspect raw text of TOC pages |
| `domain.registers.classes` | Logical register groups | Read spec register overview chapter |
| `domain.registers.register_offsets` | Per-register definitions | Read spec register detail chapters |
| `domain.registers.exclude_tables` | Non-register tables | Identify tables that look like registers but aren't |
| `domain.features.definitions` | Feature catalog | Read spec TOC + major sections |
| `domain.features.hd_sequences` | Host driver sequences | Find step-by-step procedures in spec |

---

## File Checklist

After a successful clone, your directory should contain:

```
<your_rag>/_rag_v2/
├── spec_config.yaml                ← Your customized config
├── run_pipeline.py                 ← Copied (generic)
├── shared/                         ← Copied (generic)
│   ├── config.py, llm_client.py, pdf_utils.py, data_classes.py, utils.py
│   └── context.md                  ← Create for agent discoverability
├── phase1_discovery/               ← Copied (generic)
│   ├── analyze_pdf.py, extract_toc.py
│   └── context.md
├── phase2_extraction/              ← Copied (may need hardcode fixes)
│   ├── extract_sections.py, extract_tables.py, extract_figures.py
│   ├── extract_domain.py, validate.py
│   └── context.md
├── phase3_assembly/                ← Copied (may need hardcode fixes)
│   ├── merge_metadata.py
│   └── context.md
├── intermediates/                  ← Generated by pipeline
│   ├── discovery.json, sections.json, registers.json, features.json
│   ├── tables_page_map.json, figures_page_map.json, validation_report.json
│   ├── tables_csv/, tables_images/, figures_plantuml/, figures_images/
│   └── context.md
├── metadata/                       ← Final output
│   ├── metadata.json               ← The knowledge graph
│   ├── metadata_api.py             ← Copied (generic)
│   ├── agent_instructions.md       ← Create for agents
│   └── context.md
├── context.md                      ← Root context
└── clone.prompt.md                 ← This file (optional)
```

Place the source PDF at `<your_rag>/your_spec.pdf` (sibling to `_rag_v2/`).
