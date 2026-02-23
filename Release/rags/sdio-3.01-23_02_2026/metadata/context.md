# RAG V2 Metadata Context

## Overview

The `sdio_rag/_rag_v2/metadata/metadata.json` is the unified knowledge graph produced by the config-driven RAG V2 pipeline. Generated through a clean, reproducible 3-phase pipeline driven by `spec_config.yaml`.

Configured for **SDIO Simplified Specification Version 3.00** (SD Card Association, 90 PDF pages, 89 spec pages).

## Pipeline

```
Phase 1: Discovery (free)
  analyze_pdf.py  → intermediates/discovery.json

Phase 2: Extraction (LLM)
  extract_sections.py → intermediates/sections.json
  extract_tables.py   → intermediates/tables_page_map.json + tables_csv/*.csv
  extract_figures.py  → intermediates/figures_page_map.json + figures_plantuml/*.puml
  extract_domain.py   → intermediates/registers.json + intermediates/features.json

Phase 3: Assembly (deterministic)
  merge_metadata.py   → metadata/metadata.json
```

### Running

```powershell
cd sdio_rag/_rag_v2
python run_pipeline.py all            # Run full pipeline
python run_pipeline.py discover       # Phase 1 only (free)
python run_pipeline.py extract-sections  # Just sections
python run_pipeline.py merge          # Merge intermediates → metadata.json
python run_pipeline.py status         # Check pipeline state
```

## Configuration

All domain-specific values are in `spec_config.yaml`:

| Section | Content |
|---------|---------|
| `spec` | Name, version, PDF path, page_offset=0 |
| `toc` | TOC page ranges + regex patterns for sections/tables/figures |
| `node_types` | 7 types with classification rules |
| `chunking` | target=200, max=250, overlap=20 words |
| `llm` | Model names (haiku/sonnet/opus), default=opus |
| `domain.registers` | 2 classes (CCCR, FBR), 2 register offsets, 15 exclude_tables |
| `domain.features` | 52 feature definitions, 8 HD sequences |
| `relation_types` | 11 relation types with descriptions |

## Output Structure

```json
{
  "metadata_version": "2.0.0",
  "spec_info": {
    "name": "SDIO Simplified Specification",
    "version": "3.00",
    "page_offset": 0
  },
  "extraction_info": {
    "extracted_date": "ISO-8601",
    "pipeline_version": "2.0.0",
    "config_file": "spec_config.yaml",
    "statistics": {
      "total_nodes": 200,
      "by_type": {
        "TABLE": 35, "FIGURE": 21, "SPEC_CHUNK": 80,
        "REGISTER": 2, "REG_CLASS": 2,
        "FEATURE": 52, "HD_SEQUENCE": 8
      }
    }
  },
  "nodes": [ /* ... */ ],
  "relations": [ /* ... */ ]
}
```

## Node Types

### TABLE
| Field | Description |
|-------|-------------|
| `id` | TABLE_C_S (chapter-seq, e.g., TABLE_6_1, TABLE_C_1) |
| `type` | "TABLE" |
| `name` | Table title from spec |
| `description` | Table abstract |
| `source.page` | Spec page number |
| `source.pdf_page` | PDF page (same as spec_page, offset=0) |
| `extras.table_type` | REGISTER_FIELDS, COMMAND_TABLE, STATUS_TABLE, etc. |
| `extras.csv_file` | Path to CSV |

### FIGURE
| Field | Description |
|-------|-------------|
| `id` | FIG_C_S (chapter-seq, e.g., FIG_1_1, FIG_3_1) |
| `name` | Figure title |
| `extras.figure_type` | STATE_DIAGRAM, TIMING_DIAGRAM, BLOCK_DIAGRAM, FORMAT_DIAGRAM, etc. |
| `extras.text_diagram_file` | Path to PlantUML |

### SPEC_CHUNK
| Field | Description |
|-------|-------------|
| `id` | CHUNK_X_Y_Z (section_chunkindex) |
| `name` | Section title + chunk index |
| `description` | LLM chunk abstract |
| `extras.section_number` | e.g., "6.9" |
| `extras.full_text` | Complete raw text |
| `extras.word_count` | Token count |

### REGISTER
| Field | Description |
|-------|-------------|
| `id` | REG_XXX (pseudo-offset) |
| `name` | Register name (CCCR Registers, FBR Registers) |
| `extras.offset_hex` | e.g., "001h" (pseudo-offset) |
| `extras.class_id` | REG_CLASS reference |
| `extras.fields` | Array of field defs |

### REG_CLASS
| Field | Description |
|-------|-------------|
| `id` | REGCLASS_NAME |
| `name` | Class name (CCCR, FBR) |
| `extras.address_range` | start/end pseudo-offsets |

### FEATURE
| Field | Description |
|-------|-------------|
| `id` | F_NAME (e.g., F_INIT, F_CCCR, F_INTERRUPT) |
| `name` | Feature name |
| `extras.groups` | Feature groups (initialization, bus, command, registers, interrupt, etc.) |
| `extras.priority` | P0/P1/P2 |
| `extras.parent_id` | Parent feature ID |
| `extras.figures/tables/registers/spec_sections` | References |

### HD_SEQUENCE
| Field | Description |
|-------|-------------|
| `id` | HDS_NAME (e.g., HDS_CARD_INIT_SD, HDS_IO_RW_DIRECT) |
| `name` | Sequence name |
| `extras.uses_features` | Feature dependencies |
| `extras.figures/tables/spec_sections` | References |

## Relation Types

| Type | Source → Target | Description |
|------|-----------------|-------------|
| `REFERENCES` | CHUNK/FEATURE/HD_SEQ → TABLE/FIGURE | Cross-reference |
| `CHILD_OF` | SPEC_CHUNK → SPEC_CHUNK | Section hierarchy |
| `DEFINED_BY` | REGISTER → TABLE | Register fields from table |
| `BELONGS_TO` | REGISTER → REG_CLASS | Register classification |
| `PART_OF` | FEATURE → FEATURE | Sub-feature hierarchy |

## PAGE_OFFSET

```python
PAGE_OFFSET = 0  # PDF page = spec_page (1-indexed, pages match directly)
```

## Metadata API

**Script**: `sdio_rag/_rag_v2/metadata/metadata_api.py`

```powershell
python sdio_rag/_rag_v2/metadata/metadata_api.py <function> [args...]
```

### API Categories

| Category | Functions |
|----------|-----------|
| Generic Nodes | `get_node_by_id`, `get_nodes_by_type`, `search_nodes`, `list_all_types` |
| Relations | `get_relations_from`, `get_relations_to`, `get_chunks_referencing` |
| Registers | `get_register_by_offset`, `get_register_by_id`, `get_register_by_name`, `list_registers`, `get_register_class_by_id`, `list_register_classes` |
| Fields | `get_field_by_id`, `list_fields_in_register`, `search_fields_by_name` |
| Tables | `get_table_by_id`, `list_tables`, `get_table_csv` |
| Figures | `get_figure_by_id`, `list_figures`, `get_figure_plantuml` |
| Features | `get_feature_by_id`, `list_features`, `get_feature_tree`, `get_feature_groups`, `list_hd_sequences`, `get_hd_sequence_by_id` |
| Spec Content | `get_chunk_by_id`, `list_sections`, `get_page_content`, `search_chunks_by_text` |
| Coverage | `set_node_coverage_status`, `get_node_coverage_status`, `list_nodes_by_coverage`, `get_coverage_summary` |
| Metadata | `get_spec_info`, `get_register_map` |

### Response Format

All functions return:
```json
{
  "success": true,
  "function": "get_register_by_offset",
  "params": {"offset": "001h"},
  "count": 1,
  "truncated": false,
  "results": { ... },
  "error": null
}
```

### Coverage Status

```python
api.set_node_coverage_status("F_INIT", "IMPLEMENTED", notes="Done", implemented_in="src/sdio.cpp")
api.get_coverage_summary()
```

Valid: `NOT_IMPLEMENTED`, `PARTIAL`, `IMPLEMENTED`, `NOT_APPLICABLE`

**IMPORTANT**: `set_node_coverage_status` writes back to `metadata.json` on disk.
**IMPORTANT**: Agents should NEVER directly read `metadata.json`. Always use the metadata API.

## Backup Policy

- Before each merge, existing `metadata.json` → `metadata/backups/metadata_YYYYMMDDTHHMMSS.json`
- Coverage updates also trigger backups
