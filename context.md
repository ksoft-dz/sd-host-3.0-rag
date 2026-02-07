# SD Host 3.0 RAG System - Quick Context Guide

**Purpose**: Minimal-token guide for agents to quickly understand the workspace structure and get started.

---

## 🎯 What This Is

A structured RAG (Retrieval-Augmented Generation) system for extracting and querying the SD Host Controller 3.0 specification. The goal is to create a comprehensive metadata file that serves as the single source of truth for an agent answering questions about the IP specification.

---

## 📚 Main Documentation

**READ THIS FIRST**: [docs/process.md](docs/process.md)
- Complete process definition (1400+ lines)
- All phases, schemas, and workflows
- Decision log and rationale
- Implementation roadmap

**Summary of process.md**:
- **Phase -1**: Figure pre-processing (convert figures to text diagrams)
- **Phase 0**: PDF analysis & setup (create llm_context.json)
- **Phase 1**: Metadata schema definition (JSON structure)
- **Phase 2**: Extraction pipeline (registers, features, tables, figures)
- **Phase 3**: Validation & QA
- **Phase 4**: Access script (metadata_access.py)
- **Phase 5**: Agent prompts (extraction & query agents)

---

## 📂 Critical Resources

### Configuration & Hints

| Resource | Location | Description |
|----------|----------|-------------|
| **llm_context.json** | `llm_context.json` | Pre-metadata hints guiding extraction |

### Already Extracted & Indexed

| Resource | Location | Description |
|----------|----------|-------------|
| **Tables** | `tables/tables_page_map.json` | Index of 60 tables with schema |
| | `tables/csv/*.csv` | Converted CSV files |
| | `tables/context.md` | Schema documentation |
| **Figures** | `figures/figures_page_map.json` | Index of 83 figures with schema |
| | `figures/plantuml/*.puml` | PlantUML diagram files |
| | `figures/context.md` | Schema documentation |
| **Sections** | `spec/sections.json` | Hierarchical sections with chunks |
| | `spec/context.md` | Schema documentation |

### To Be Created

| Resource | Location | Purpose |
|----------|----------|---------|
| **Metadata** | `metadata/metadata.json` | The final structured metadata file |
| **Access Script** | `scripts/metadata_access.py` | Query interface for agents |
| **Extraction Scripts** | `scripts/*.py` | Various extraction utilities |

---

## 🚀 Quick Start for Agents

### 1. First Time Here?
```bash
# Read the extraction hints first
Load: llm_context.json (understand PDF structure & priorities)

# Read the main process document
Read: docs/process.md (sections 1-3 for overview)

# Understand the resources
Read: tables/context.md
Read: figures/context.md

# Check what's available
Load: tables/tables_page_map.json
Load: figures/figures_page_map.json
```

### 2. Building Metadata?
```bash
# Start with Phase 0 (docs/process.md section 5)
1. Analyze PDF structure
2. Create/update llm_context.json
3. Verify tables/figures resources

# Proceed to Phase 2 (docs/process.md section 7)
1. Extract registers (custom parser + LLM)
2. Extract features
3. Import state machines from figures
4. Create spec chunks
5. Generate relations
```

### 3. Querying Existing Metadata?
```bash
# Use metadata_access.py (when implemented)
python scripts/metadata_access.py get_register "Power Control"
python scripts/metadata_access.py search "DMA,transfer"
python scripts/metadata_access.py get_related REG_029
```

---

## 📋 Key Schemas (Quick Reference)

### llm_context.json (Extraction Hints)
```json
{
  "spec_info": { "name": "...", "version": "3.00", "total_pages": 157 },
  "section_hints": {
    "register_map": { "pages": [5, 11], "description": "..." },
    "register_definitions": { "pages": [29, 90], "description": "..." },
    "programming_sequences": { "pages": [100, 130], "chunk_granularity": "per_paragraph" }
  },
  "figures_folder": "figures/",
  "figures_index": "figures/figures_page_map.json",
  "extraction_patterns": { "register_header": { "pattern": "..." } },
  "known_issues": [{ "description": "...", "solution": "..." }],
  "extraction_priorities": { "1_critical": [...], "2_important": [...] },
  "validation_checkpoints": { "after_register_map": "..." }
}
```

### Tables (tables/tables_page_map.json)
```json
{
  "_metadata": { "total_tables": 60, "conversion_progress": {...} },
  "tables": [
    {
      "id": "TABLE_X_Y",
      "title": "...",
      "definition_page": 123,
      "conversion": {
        "status": "COMPLETED",
        "file_name": "TABLE_X_Y.csv"
      }
    }
  ]
}
```

### Figures (figures/figures_page_map.json)
```json
{
  "_metadata": { "total_figures": 83, "transcription_progress": {...} },
  "figures": [
    {
      "id": "FIG_X_Y",
      "title": "...",
      "definition_page": 123,
      "transcription": {
        "status": "COMPLETED",
        "text_file": "plantuml/FIG_X_Y.puml",
        "format": "plantuml"
      },
      "abstract": "..."
    }
  ]
}
```

### Sections (spec/sections.json)
```json
{
  "_metadata": { "total_sections": 150, "total_chunks": 280, "chunk_target_words": 200 },
  "sections": {
    "2.1.3": {
      "id": "SEC_2_1_3",
      "title": "Power Control Register",
      "level": 3,
      "hierarchy": { "parent": "SEC_2_1", "children": [] },
      "references": { "tables": ["TABLE_2_17"], "figures": ["FIG_2_15"], "related": [] },
      "index": { "keywords": [...], "technical_terms": [...] },
      "abstract": "...",
      "chunks": [
        { "chunk_id": "SEC_2_1_3_C0", "chunk_index": 0, "abstract": "...", "raw": "..." }
      ]
    }
  }
}
```

### Metadata Node Types (from process.md)
- **REGISTER**: Hardware registers with fields and enum values
- **FEATURE**: IP features and capabilities
- **PORT**: Signal/port definitions
- **STATE_MACHINE**: State diagrams with transitions
- **SPEC_CHUNK**: Text sections (descriptions, procedures, etc.)
- **TABLE**: Reference to tables
- **FIGURE**: Reference to figures

---

## ⚠️ Critical Constraints

From [docs/process.md](docs/process.md):

1. **Metadata-Only**: Agent NEVER accesses PDF directly in production (only metadata.json via metadata_access.py)
2. **Validation Required**: Always validate STATE_MACHINE nodes and low-confidence extractions
3. **Traceability**: Every node must have source page/position
4. **No Hallucination**: Agent must not use training knowledge about SD Host (only metadata)
5. **Relations Matter**: Build comprehensive relations between nodes

---

## 🔍 Navigation Tips

- **Need schema details?** → `tables/context.md`, `figures/context.md`, or `spec/context.md`
- **Need process details?** → `docs/process.md` (specific sections)
- **Need to understand extraction?** → `docs/process.md` sections 7-8
- **Need to query metadata?** → `docs/process.md` section 9
- **Need agent prompts?** → `docs/process.md` section 10

---

## 📊 Current Status

| Phase | Status | Notes |
|-------|--------|-------|
| Phase -1 (Figures) | ✅ Partial | 83 figures indexed, PlantUML files available |
| Phase 0 (Setup) | ✅ Partial | tables_page_map.json & figures_page_map.json ready |
| Phase 1 (Schema) | ✅ Complete | Defined in docs/process.md section 6 |
| Phase 2 (Extraction) | ❌ Not Started | Awaiting implementation |
| Phase 3 (Validation) | ❌ Not Started | Scripts to be created |
| Phase 4 (Access) | ❌ Not Started | metadata_access.py to be created |
| Phase 5 (Prompts) | ✅ Complete | Defined in docs/process.md section 10 |

---

## 💡 Token-Efficient Context Loading

Instead of reading entire files:

1. **Load this file first** (you're reading it now) - ~50 tokens
2. **Load specific context.md** files as needed - ~200 tokens each
3. **Load relevant sections of process.md** - Section-by-section
4. **Query JSON files** - Only load metadata, not full content

**Example workflow (minimal tokens)**:
```
1. Read: context.md (this file)          →  50 tokens
2. Read: tables/context.md               → 200 tokens  
3. Load: tables/tables_page_map.json     → Parse specific table
4. Read: docs/process.md (section 7.2)   → Understand register extraction
```

---

**Last Updated**: 2026-02-01  
**Workspace**: e:\work\rag\sdhost-3.0  
**Main Doc**: [docs/process.md](docs/process.md)
