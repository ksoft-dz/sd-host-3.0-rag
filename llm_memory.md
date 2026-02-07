# SD Host 3.0 RAG System - LLM Memory

> **Purpose**: Quick context recovery for LLM sessions working on this project.
> **Last Updated**: 2026-02-01

---

## Project Status: ✅ EXTRACTION COMPLETE

All extraction phases are complete. The unified metadata graph is ready.

### Quick Stats
| Resource | Count | Location |
|----------|-------|----------|
| Tables | 60 | `tables/tables_page_map.json` |
| Figures | 83 | `figures/figures_page_map.json` |
| Sections | 112 | `spec/sections.json` |
| Chunks | 287 | `spec/sections.json` |
| **Total Nodes** | 464 | `metadata/metadata.json` |
| **Total Relations** | 570 | `metadata/metadata.json` |

---

## Key Files to Know

### Extracted Resources
| Path | Description |
|------|-------------|
| `tables/tables_page_map.json` | Table inventory (60 tables) |
| `tables/csv/*.csv` | Converted table CSVs |
| `figures/figures_page_map.json` | Figure inventory (83 figures) |
| `figures/plantuml/*.puml` | PlantUML transcriptions |
| `spec/sections.json` | Sections + chunks (112 sections, 287 chunks) |
| `metadata/metadata.json` | **Final unified graph** |

### Documentation
| Path | Description |
|------|-------------|
| `docs/process.md` | Full process definition (LOCKED) |
| `merge.md` | Merge process context & recovery notes |
| `tables/README.md` | Table extraction quick start |
| `figures/README.md` | Figure extraction quick start |
| `spec/README.md` | Section extraction quick start |
| `scripts/README.md` | Merge script documentation |

### Scripts
| Path | Description |
|------|-------------|
| `tables/extract_tables_map.py` | Build table inventory |
| `tables/convert_tables_to_csv.py` | Convert tables to CSV |
| `figures/extract_figures_map.py` | Build figure inventory |
| `figures/convert_figures_to_plantuml.py` | Convert to PlantUML |
| `spec/extract_sections.py` | Extract sections + chunks |
| `scripts/merge_metadata.py` | **Merge all → metadata.json** |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        INPUT: PDF                                   │
│                    source/sd_host_3_00.pdf                          │
└─────────────────────────────────────────────────────────────────────┘
                                 │
     ┌───────────────────────────┼───────────────────────────┐
     ▼                           ▼                           ▼
┌─────────────┐          ┌─────────────┐          ┌─────────────┐
│   TABLES    │          │   FIGURES   │          │   SECTIONS  │
│   60 items  │          │   83 items  │          │ 112 sections│
│             │          │             │          │ 287 chunks  │
└─────────────┘          └─────────────┘          └─────────────┘
     │                           │                           │
     └───────────────────────────┼───────────────────────────┘
                                 ▼
                    ┌────────────────────────┐
                    │   scripts/merge_       │
                    │   metadata.py          │
                    └────────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │  metadata/metadata.json│
                    │  464 nodes             │
                    │  570 relations         │
                    └────────────────────────┘
```

---

## Node Types in Metadata

| Type | Count | Description |
|------|-------|-------------|
| `TABLE` | 60 | Tables with CSV data |
| `FIGURE` | 83 | Figures with PlantUML |
| `SPEC_CHUNK` | 287 | Text chunks (~200 words each) |
| `REGISTER` | 34 | Registers with offset, fields |

---

## Relation Types in Metadata

| Type | Description |
|------|-------------|
| `REFERENCES` | Chunk references Table/Figure |
| `CHILD_OF` | Section hierarchy |
| `DEFINED_BY` | Register → Table (fields) |
| `VISUALIZED_BY` | Register → Figure (layout) |
| `DESCRIBES` | Chunk → Register |

---

## Key Constants

```python
PAGE_OFFSET = 11        # pdf_page = spec_page + 11
CHUNK_MAX_WORDS = 250   # Hard limit per chunk
CHUNK_TARGET = 200      # Target words per chunk
```

---

## Next Steps (Phase 4+)

1. **Create `metadata_access.py`** - Python interface to query metadata
2. **Build validation scripts** - Completeness, coherence checks
3. **Design agent prompts** - For orchestration agent (Phase 5)
4. **Coverage tracking** - Implementation status per node

See `docs/process.md` for full phase definitions.
