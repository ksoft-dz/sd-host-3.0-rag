# RAG V2 — Initial Discussion & Proposal Summary

## Problem Statement

The current SD Host 3.0 RAG extraction pipeline (`sdhost-3.0/`) works well but has **hardcoded** values everywhere:
- TOC page indices (`[9, 10]` for tables, `[7, 8]` for figures)
- `PAGE_OFFSET = 11`
- Register classes hardcoded as Python lists
- Feature hierarchies hardcoded in `generate_features.py`
- Table/figure regex patterns assume `Table X-Y` / `Figure X-Y` formatting

This means every new spec would require **rewriting** these scripts. The goal of `_rag_v2` is to build a **config-driven**, reusable pipeline that works on any PDF specification.

## Architecture — 3-Phase Pipeline

### Phase 1: Discovery (cheap, deterministic)
- **`analyze_pdf_structure.py`** — Scans PDF to detect page count, TOC location, page offset, naming conventions
- **`extract_toc.py`** — Extracts hierarchical ToC, auto-detects table/figure listings
- Output: `discovery.json` (structural skeleton)

### Phase 2: Extraction (expensive, LLM-dependent)
- **`extract_sections.py`** — Chunks spec text, LLM abstracts/keywords
- **`extract_tables.py`** — Table inventory → image → CSV conversion
- **`extract_figures.py`** — Figure inventory → image → PlantUML/description
- **`extract_domain_nodes.py`** — Config-driven domain extraction (registers, features, etc.)
- Output: `sections.json`, `tables_page_map.json`, `figures_page_map.json`, domain JSONs

### Phase 3: Assembly (deterministic)
- **`merge_metadata.py`** — Combines all Phase 2 outputs into unified `metadata.json`
- **`metadata_api.py`** — Query/coverage API (same interface as current v1)

## Config-Driven Design — `spec_config.yaml`

A single config file per project replaces all hardcoded values:

```yaml
spec:
  name: "SD Host Controller Simplified Specification"
  version: "3.00"
  pdf_file: "source/sd_host_3_00.pdf"
  page_offset: 11

toc:
  sections_pages: [3, 4, 5, 6]      # PDF pages (0-indexed) for ToC
  tables_pages: [9, 10]              # PDF pages for Table of Tables
  figures_pages: [7, 8]              # PDF pages for Table of Figures
  section_pattern: "^(\\d+(?:\\.\\d+)*)\\s+(.+?)\\s*\\.{3,}\\s*(\\d+)"
  table_pattern: "Table\\s+(\\d+)[-.](\\d+)\\s*:\\s*(.+?)\\.{3,}\\s*(\\d+)"
  figure_pattern: "Figure\\s+(\\d+)[-.](\\d+)\\s*:\\s*(.+?)\\.{3,}\\s*(\\d+)"

node_types:
  TABLE:
    id_format: "TABLE_{chapter}_{seq}"
    enabled: true
  FIGURE:
    id_format: "FIG_{chapter}_{seq}"
    enabled: true
  SPEC_CHUNK:
    id_format: "CHUNK_{section}_{idx}"
    enabled: true
  REGISTER:
    id_format: "REG_{offset}"
    enabled: true
  REG_CLASS:
    id_format: "REGCLASS_{name}"
    enabled: true
  FEATURE:
    id_format: "F_{name}"
    enabled: true
  HD_SEQUENCE:
    id_format: "HD_{name}"
    enabled: true

domain:
  registers:
    enabled: true
    classes: [...]  # Config-driven register classes
    exclude_tables: [...]
  features:
    enabled: true
    # Feature definitions or LLM-driven feature discovery

chunking:
  target_words: 200
  max_words: 250
  overlap_words: 20

llm:
  default_model: "sonnet"
  models:
    haiku: "claude-haiku-4-5-20251001"
    sonnet: "claude-sonnet-4-5-20250929"
    opus: "claude-opus-4-5-20251101"
  rate_limit_delay: 1.5
  max_retries: 3
```

## Node Types (Same as SD Host v1)

The metadata graph uses the same 7 node types:

| Type | ID Format | Description |
|------|-----------|-------------|
| `TABLE` | TABLE_X_Y | Tables from spec PDF |
| `FIGURE` | FIG_X_Y | Figures/diagrams from spec |
| `SPEC_CHUNK` | CHUNK_X_Y_Z | Text chunks (200-word target) |
| `REGISTER` | REG_XXX | Hardware registers |
| `REG_CLASS` | REGCLASS_NAME | Register classification groups |
| `FEATURE` | F_NAME | Capabilities/protocol features |
| `HD_SEQUENCE` | HD_NAME | Host driver operational sequences |

## Relation Types (Same as SD Host v1)

| Type | Source → Target | Description |
|------|-----------------|-------------|
| `REFERENCES` | CHUNK/FEATURE/HD_SEQ → TABLE/FIGURE | Cross-references |
| `CHILD_OF` | SPEC_CHUNK → SPEC_CHUNK | Section hierarchy |
| `DEFINED_BY` | REGISTER → TABLE | Register fields from table |
| `VISUALIZED_BY` | REGISTER → FIGURE | Register in figure |
| `DESCRIBES` | TABLE/CHUNK → REGISTER | Describes a register |
| `BELONGS_TO` | REGISTER → REG_CLASS | Functional group |
| `DEFINED_IN` | REGISTER → TABLE | Primary definition |
| `PART_OF` | FEATURE → FEATURE | Sub-feature hierarchy |
| `USES_FEATURE` | HD_SEQUENCE → FEATURE | Sequence→feature dependency |
| `HIGHLY_RELATED_TO` | FEATURE → FEATURE | Strong relation |
| `SLIGHTLY_RELATED_TO` | FEATURE → FEATURE | Weak relation |

## Execution Order & Cost Estimate

### Execution Order
1. `python run_pipeline.py discover` — Phase 1 (~5 sec, no LLM, free)
2. `python run_pipeline.py extract-sections` — Phase 2a (~$2-3 for 150 pages)
3. `python run_pipeline.py extract-tables` — Phase 2b (~$4-5 for 60 tables)
4. `python run_pipeline.py extract-figures` — Phase 2c (~$3-4 for 80 figures)
5. `python run_pipeline.py extract-domain` — Phase 2d (~$2-3 for registers/features)
6. `python run_pipeline.py merge` — Phase 3 (~1 sec, no LLM, free)

**Total estimated cost**: ~$12-15 for a 150-page spec (same as v1)

### Cost Breakdown by Model
| Phase | Model | Calls | Est. Cost |
|-------|-------|-------|-----------|
| Discovery | None | 0 | Free |
| Sections | Sonnet | ~300 | $2-3 |
| Tables→CSV | Sonnet+Vision | ~60 | $4-5 |
| Figures→PUML | Sonnet+Vision | ~80 | $3-4 |
| Domain (reg+feat) | Sonnet | ~100 | $2-3 |
| Merge | None | 0 | Free |

## Key Design Decisions

1. **Regex-first TOC** — Cheaper and more reliable than LLM for structured TOC pages
2. **Split discovery from extraction** — Discovery is free, extraction is expensive; allows dry-run validation
3. **Config-driven domain nodes** — Register classes, features defined in YAML, not hardcoded in Python
4. **Same metadata.json schema** — 100% backward compatible with existing metadata_api.py
5. **Same metadata_api.py interface** — Existing RAG agents work without changes
6. **Incremental extraction** — Skip already-processed items (--skip-existing flag)

## Goal of This Experiment

Create `_rag_v2/metadata/metadata.json` for the SD Host spec using the new pipeline and compare RAG retrieval quality with the existing `metadata/metadata.json` from v1.
