# SD Host RAG System - Process Definition Document

> **Status**: 🔒 LOCKED - Ready for Implementation  
> **Goal**: Define a clear, reproducible, testable, and validable plan for building a structured RAG system for embedded IP specifications.  
> **Last Updated**: 2026-01-31  
> **Schema Version**: 1.0.0

---

## Table of Contents

1. [Overview](#1-overview)
2. [Decisions Log](#2-decisions-log)
3. [PDF Analysis Results](#3-pdf-analysis-results)
4. [Phase -1: Figure Pre-Processing (User-Controlled)](#4-phase--1-figure-pre-processing-user-controlled)
5. [Phase 0: PDF Pre-Analysis & Preparation](#5-phase-0-pdf-pre-analysis--preparation)
6. [Phase 1: Metadata Structure Definition](#6-phase-1-metadata-structure-definition)
7. [Phase 2: Extraction Pipeline Design](#7-phase-2-extraction-pipeline-design)
8. [Phase 3: Validation & Quality Assurance](#8-phase-3-validation--quality-assurance)
9. [Phase 4: Access Script Design](#9-phase-4-access-script-design)
10. [Phase 5: Orchestration Agent & Prompts](#10-phase-5-orchestration-agent--prompts)
11. [Open Questions & Next Steps](#11-open-questions--next-steps)

---

## 1. Overview

### 1.1 Problem Statement

We need to extract structured information from IP specification PDFs (e.g., SD Host 3.0) into a queryable graph-based metadata structure. This metadata will serve as the **single source of truth** for an agent that answers questions about the IP.

**Critical Use Case**: Simulating hardware component behavior from spec — accuracy is paramount.

### 1.2 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER / AGENT                                │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    QUERY ORCHESTRATION AGENT                        │
│  (Constrained to use ONLY metadata_access.py primitives)            │
│  ⚠️  MANDATORY: Never access metadata.json directly                 │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     metadata_access.py                              │
│  (Python script - SOLE interface to metadata.json)                  │
│  Primitives: get_register, get_node, search_by_keywords, ...        │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       metadata.json                                 │
│  (Structured graph: nodes + relations)                              │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.3 Constraints (LOCKED)

- [x] Agent must **NEVER** access `metadata.json` directly — **MANDATORY**
- [x] Agent answers based on metadata **ONLY** (no hallucination from training data)
- [x] Exception: Common knowledge (units like V=Volts, standard acronyms)
- [x] Working within GitHub Copilot context — scripts only, no vision APIs inline
- [x] Coverage tracking must be built-in for future implementation tracking
- [x] Process must be iterative and allow user validation

---

## 2. Decisions Log

### 2.1 Answered Questions

| # | Question | Decision | Rationale |
|---|----------|----------|-----------|
| Q1 | PDF available? | ✅ Yes - `sd_host_3_00.pdf` in workspace | 157 pages |
| Q2 | PDF tools | ✅ PyMuPDF, pdfplumber, tabula-py | No LLM vision inline (Copilot constraint) |
| Q3 | Diagrams handling | ✅ Libraries preferred; LLM vision **outside** workflow, user-controlled | User prepares figures separately, feeds back to agent |
| Q9 | Validation intensity | ✅ Samples + always validate complex types + low confidence | Balance automation vs accuracy |
| Q10 | Register extraction | ✅ Hybrid (custom parser first + LLM for failures) | Consistent format detected, llm_context hints help |
| Q4 | Schema completeness | ✅ Keep generic, categories in SPEC_CHUNK | Don't overengineer, Interrupt/Error/Timing are categories not types |
| Q5 | Enum values | ✅ Always extract, keep raw values | Traceability back to spec is critical |
| Q6 | SEQUENCE_NEXT auto-gen | ✅ Yes, from programming_sequence_order | Reduces manual relation creation |
| Q7 | Parser approach | ✅ Custom parser FIRST, LLM only for failures | Faster, deterministic, cheaper; LLM handles edge cases |
| Q8 | Chunk granularity | ✅ Per subsection default, per paragraph for critical | Balance detail vs noise |

### 2.2 Key Design Decisions

| Decision | Description |
|----------|-------------|
| `llm_context.json` | Pre-metadata hints file created by user to guide extraction (register map section, register descriptions section) |
| Figure Pre-Processing | Separate phase (-1), **ALL figures** must be transcribed consistently with page number + figure ID for traceability |
| Strict Metadata Access | Agent uses ONLY `metadata_access.py` — simulating real hardware requires spec accuracy |
| Generic Node Types | Keep node types generic (applicable to other IPs); specific categories go in SPEC_CHUNK description |
| Raw Value Preservation | Always keep raw spec values (e.g., "111b") alongside interpreted values for traceability |

---

## 3. PDF Analysis Results

### 3.1 Document Overview

| Property | Value |
|----------|-------|
| File | `sd_host_3_00.pdf` |
| Total Pages | 157 |
| Embedded ToC | ❌ None (must extract from text) |
| Text Extractable | ✅ Yes - full text extraction works |
| Tables | ✅ Text-based (parseable) |
| Images | Only 2 pages (cover + last page) |
| Figures | 83 unique figure references |
| Tables | 61 unique table references |

### 3.2 Key Findings

#### ✅ Good News
1. **Text is fully extractable** — no OCR needed
2. **Tables are text-based** — can be parsed with regex/structured parsing
3. **Register format is consistent**:
   - Figure showing bit layout (e.g., "Figure 2-15 : Power Control Register")
   - Table with columns: Location | Attrib | Register Field | Explanation
   - Offset in header (e.g., "Offset 029h")

#### ⚠️ Challenges
1. **Figures are vector graphics** — extracted as fragmented text elements
   - Example: Figure 1-4 "Suspend and Resume Mechanism" extracts as disconnected words
   - Solution: Phase -1 (user pre-processes figures)
2. **No embedded ToC** — must reconstruct from text patterns
3. **Some tables span multiple pages** — need merging logic

### 3.3 Section Map (Preliminary)

| Section | Pages (Approx) | Content |
|---------|----------------|---------|
| Introduction/Features | 1-20 | Feature overview, block diagrams |
| Register Map Overview | 5-11 | Register address map |
| Register Definitions | 29-90+ | Detailed register descriptions |
| Programming Sequences | Various | How to use the controller |
| State Diagrams | Various | State machines (as figures) |

### 3.4 Register Definition Format (Detected Pattern)

```
Page 53 Example:
═══════════════════════════════════════════════════════════════════════

2.2.11 Power Control Register (Offset 029h)

┌───────────────────────────────────┬───────────────────┬─────┐
│ D07                          D04 │ D03          D01  │ D00 │
├───────────────────────────────────┼───────────────────┼─────┤
│           Rsvd                    │ SD Bus Voltage    │ SD  │
│                                   │ Select            │ Bus │
│                                   │                   │Power│
└───────────────────────────────────┴───────────────────┴─────┘
Figure 2-15 : Power Control Register

┌──────────┬────────┬────────────────────────┬─────────────────────────┐
│ Location │ Attrib │ Register Field         │ Explanation             │
├──────────┼────────┼────────────────────────┼─────────────────────────┤
│ 07-04    │ Rsvd   │ Reserved               │                         │
│ 03-01    │ RW     │ SD Bus Voltage Select  │ By setting these bits...│
│ 00       │ RW     │ SD Bus Power           │ Before setting this...  │
└──────────┴────────┴────────────────────────┴─────────────────────────┘
Table 2-17 : Power Control Register
═══════════════════════════════════════════════════════════════════════
```

**Extraction Strategy**: Custom regex parser for this consistent format + LLM for edge cases.

---

## 4. Phase -1: Figure Pre-Processing (User-Controlled)

### 4.1 Objective

Extract figures from PDF and convert them to text-based diagram formats **before** the main extraction pipeline runs. This is done **outside GitHub Copilot** using LLM vision APIs or manual transcription.

### 4.2 Why Separate Phase?

1. GitHub Copilot cannot use vision APIs directly
2. Figures in the PDF are vector graphics, extracting as fragmented text
3. Quality of figure interpretation benefits from human validation
4. One-time effort that can be reused

### 4.3 Workflow

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PHASE -1: FIGURE PRE-PROCESSING                  │
│                    (Outside GitHub Copilot)                         │
└─────────────────────────────────────────────────────────────────────┘
                                 │
     ┌───────────────────────────┼───────────────────────────┐
     ▼                           ▼                           ▼
┌─────────────┐          ┌─────────────┐          ┌─────────────┐
│   Step 1    │          │   Step 2    │          │   Step 3    │
│   Extract   │          │   Convert   │          │   Validate  │
│   Figures   │          │   to Text   │          │   & Store   │
└─────────────┘          └─────────────┘          └─────────────┘
     │                           │                           │
     ▼                           ▼                           ▼
- Screenshot/export      - LLM Vision API          - User reviews
  each figure              (GPT-4V, Claude)        - Corrects errors  
- Store as PNG           - Convert to Mermaid,    - Stores in figures/
- Log page numbers         PlantUML, or ASCII       with metadata
```

### 4.4 Figure Output Structure

```
figures/
├── figures_page_map.json             # Index of all figures (ACTUAL FILE IN USE)
├── plantuml/                         # PlantUML diagram files
│   ├── FIG_1_1.puml
│   ├── FIG_1_2.puml
│   └── ...
├── images/                           # Original/extracted images
│   ├── FIG_1_1.puml (or .png)
│   └── ...
└── context.md                        # Schema documentation for agents
```

#### figures_page_map.json Format (ACTUAL SCHEMA IN USE)

**⚠️ CRITICAL**: The actual file in use is `figures/figures_page_map.json` with the following schema:

```json
{
  "_metadata": {
    "source_pdf": "sd_host_3_00.pdf",
    "total_pages": 157,
    "extraction_date": "2026-01-31",
    "total_figures": 83,
    "page_offset": 11,
    "page_offset_note": "Real PDF page = spec_page + page_offset",
    "transcription_progress": {
      "not_started": 83,
      "in_progress": 0,
      "completed": 0,
      "skipped": 0
    }
  },
  "figures": [
    {
      "id": "FIG_1_1",
      "spec_reference": "Figure 1-1",
      "title": "Host Hardware and Driver Architecture",
      "spec_page": 1,
      "definition_page": 12,
      "referenced_on_pages": [12],
      "reference_count": 1,
      "content": [],
      "transcription": {
        "status": "NOT_STARTED | IN_PROGRESS | COMPLETED | SKIPPED",
        "text_file": "plantuml/FIG_1_1.puml",
        "image_file": "images/FIG_1_1.png",
        "format": "plantuml | mermaid | ascii",
        "validated": false,
        "validation_notes": ""
      },
      "abstract": "Brief description of figure content"
    }
  ]
}
```

**Resources**:
- `figures/plantuml/` - PlantUML transcriptions of figures
- `figures/images/` - Original/extracted figure images
- See `figures/context.md` for detailed schema documentation

### 4.5 Supported Diagram Formats

| Format | Use Case | Example |
|--------|----------|---------|
| Mermaid | State machines, flowcharts, sequence diagrams | `stateDiagram-v2` |
| PlantUML | Complex state machines, class diagrams | `@startuml` |
| ASCII | Simple block diagrams, register layouts | Box drawing chars |
| Markdown Table | Tabular data, simple mappings | `| Col1 | Col2 |` |

### 4.6 Mandatory Rules for Phase -1

> ⚠️ **ALL figures must be transcribed** using the same process for consistency and traceability.

#### Traceability Requirements
Every transcribed figure MUST include:
1. **PDF Page Number** — exact page where the figure appears
2. **Figure ID** — spec reference (e.g., "Figure 1-4")
3. **Validation Status** — user-validated flag

#### User Checklist

- [ ] Run `list_figures_tables.py` to get complete figure inventory
- [ ] For **EACH** figure (not just critical ones):
  - [ ] Export/screenshot from PDF
  - [ ] Record exact page number
  - [ ] Use LLM vision to generate text representation
  - [ ] Review and correct the output
  - [ ] Save to `figures/` folder with naming convention: `figure_X-Y_description.md`
  - [ ] Add entry to `figures_index.json` with page + figure ID
  - [ ] Mark as validated
- [ ] Verify all 83 figures are in `figures_index.json`
- [ ] Mark Phase -1 complete only when ALL figures are processed

---

## 5. Phase 0: PDF Pre-Analysis & Preparation

### 5.1 Objective

Analyze PDF structure and create `llm_context.json` — the pre-metadata hints file.

### 5.2 The `llm_context.json` File

This file is created by the user (with script assistance) to guide the extraction agent. It contains hints about where to find different types of content.

#### 5.2.1 Structure

```json
{
  "spec_info": {
    "name": "SD Host Controller Simplified Specification",
    "version": "3.00",
    "source_file": "sd_host_3_00.pdf",
    "total_pages": 157
  },
  
  "section_hints": {
    "features_summary": {
      "pages": [1, 20],
      "description": "High-level features and introduction"
    },
    "register_map": {
      "pages": [5, 11],
      "description": "Register address overview tables - CRITICAL for extraction",
      "tables": ["Table 2-1", "Table 2-2"],
      "note": "Use this to get the complete list of registers (name + offset) before detailed extraction"
    },
    "register_definitions": {
      "pages": [29, 90],
      "description": "Detailed register definitions - CRITICAL for extraction",
      "format_hint": "Each register has: section header with offset, bit layout figure, field table",
      "extraction_order": "Use register_map to identify all registers, then extract each from this section"
    },
    "programming_sequences": {
      "pages": [100, 130],
      "description": "How to program the controller"
    },
    "state_machines": {
      "pages": [15, 25, 45],
      "description": "State diagram figures",
      "note": "See figures/ folder for text versions"
    }
  },
  
  "figures_folder": "figures/",
  "figures_index": "figures/figures_page_map.json",
  "figures_resources": {
    "page_map": "figures/figures_page_map.json",
    "plantuml": "figures/plantuml/",
    "images": "figures/images/",
    "note": "See figures/context.md for schema documentation"
  },
  
  "tables_folder": "tables/",
  "tables_index": "tables/tables_page_map.json",
  "tables_resources": {
    "page_map": "tables/tables_page_map.json",
    "csv": "tables/csv/",
    "images": "tables/images/",
    "note": "See tables/context.md for schema documentation"
  },
  
  "extraction_hints": {
    "register_pattern": "Section header contains 'Register (Offset XXXh)'",
    "table_pattern": "Tables are labeled 'Table X-Y : Description'",
    "figure_pattern": "Figures are labeled 'Figure X-Y : Description'"
  },
  
  "known_issues": [
    "Pages 45-47 have complex multi-page tables",
    "Figure 2-5 is low quality, manually transcribed"
  ]
}
```

### 5.3 Phase 0 Steps

| Step | Action | Output |
|------|--------|--------|
| 0.1 | Run PDF structure analysis script | Page count, image count, text extractability |
| 0.2 | Extract and review ToC (from text patterns) | Section list with page ranges |
| 0.3 | Identify all figures and tables | Lists with page numbers |
| 0.4 | User fills in `llm_context.json` | Populated hints file |
| 0.5 | Verify figure pre-processing complete | Check `figures/` folder |

### 5.4 Scripts for Phase 0

```
scripts/
├── analyze_pdf_structure.py    # Basic PDF stats
├── extract_toc_from_text.py    # Find section headers
├── list_figures_tables.py      # Find all Figure X-Y and Table X-Y references
└── generate_llm_context_template.py  # Create template llm_context.json
```

### 5.5 Output of Phase 0

- [x] `pdf_analysis_report.md` — PDF structure analysis
- [x] `llm_context.json` — Populated hints file
- [x] `figures/` folder — All figures converted to text format
- [x] `figures/figures_page_map.json` — Figure index with transcription tracking
- [x] `tables/tables_page_map.json` — Table index with conversion tracking
- [x] `figures/plantuml/` — PlantUML diagram files
- [x] `tables/csv/` — CSV converted table files
- [x] `spec/sections.json` — Hierarchical sections with embedded chunks

**⚠️ CRITICAL Resources for Metadata Building**:
- `tables/tables_page_map.json` — Complete table inventory with schema (60 tables)
- `tables/csv/` — Converted CSV files for tabular data
- `tables/images/` — Original table images/extractions
- `figures/figures_page_map.json` — Complete figure inventory with schema (83 figures)
- `figures/plantuml/` — PlantUML text representations of diagrams
- `figures/images/` — Original figure images
- `spec/sections.json` — Hierarchical spec sections with chunked content

See `tables/context.md`, `figures/context.md`, and `spec/context.md` for detailed schema documentation.

---

## 6. Phase 1: Metadata Structure Definition

### 6.1 Objective

Define the complete JSON schema for the metadata file.

### 6.2 Node Types & Schemas

#### 6.2.1 Common Fields (All Nodes)

```json
{
  "id": "string (prefix_uniqueid, e.g., REG_001, PORT_001)",
  "type": "enum: FEATURE | REGISTER | PORT | STATE_MACHINE | SPEC_CHUNK | TABLE | FIGURE",
  "name": "string (human readable name)",
  "description": "string (extracted or summarized description)",
  "index_keywords": ["array", "of", "searchable", "terms"],
  "source": {
    "page": "integer",
    "page_end": "integer (optional, for multi-page content)",
    "bbox": {
      "x0": "float (left)",
      "y0": "float (top)", 
      "x1": "float (right)",
      "y1": "float (bottom)"
    },
    "raw_text": "string (optional, original extracted text)"
  },
  "coverage": {
    "status": "enum: NOT_IMPLEMENTED | PARTIAL | IMPLEMENTED | NOT_APPLICABLE",
    "notes": "string (optional)",
    "implemented_in": "string (optional, file/module reference)"
  },
  "confidence": "float 0-1 (extraction confidence, for validation)",
  "validation_status": "enum: AUTO | USER_VALIDATED | NEEDS_REVIEW"
}
```

#### 6.2.2 FEATURE Node

```json
{
  "...common_fields",
  "type": "FEATURE",
  "category": "string (e.g., 'DMA', 'Interrupt', 'Power Management')",
  "spec_section": "string (e.g., '2.1.3')",
  "is_optional": "boolean (per spec, is this feature optional?)"
}
```

#### 6.2.3 REGISTER Node

```json
{
  "...common_fields",
  "type": "REGISTER",
  "offset": "string (hex, e.g., '0x029')",
  "size_bits": "integer (8, 16, 32, 64)",
  "reset_value": "string (hex, e.g., '0x00000000')",
  "access": "string (overall access if uniform, e.g., 'RW')",
  "spec_table": "string (e.g., 'Table 2-17')",
  "spec_figure": "string (e.g., 'Figure 2-15')",
  "fields": [
    {
      "name": "string",
      "bits": "string (e.g., '31:24' or '7' for single bit)",
      "bit_high": "integer (for easier processing)",
      "bit_low": "integer",
      "access": "string (RO, RW, WO, RW1C, Rsvd, etc.)",
      "reset": "string (hex or binary)",
      "description": "string",
      "enum_values": [
        {
          "raw_value": "string (exact spec text, e.g., '111b')",
          "numeric_value": "integer (optional, e.g., 7)",
          "meaning": "string (e.g., '3.3V (Typ.)')"
        }
      ]
    }
  ]
}
```

#### 6.2.4 PORT Node

```json
{
  "...common_fields",
  "type": "PORT",
  "direction": "enum: INPUT | OUTPUT | INOUT",
  "width_bits": "integer",
  "signal_type": "string (clock, reset, data, control, interrupt, etc.)",
  "active_level": "string (active_low, active_high, edge_rising, edge_falling)",
  "connected_to": "string (optional, what it typically connects to)",
  "timing_constraints": "string (optional)"
}
```

#### 6.2.5 STATE_MACHINE Node

```json
{
  "...common_fields",
  "type": "STATE_MACHINE",
  "spec_figure": "string (e.g., 'Figure 1-4')",
  "text_diagram_file": "string (path to mermaid/plantuml file)",
  "states": [
    {
      "id": "string (unique within this SM)",
      "name": "string",
      "description": "string",
      "is_initial": "boolean",
      "is_final": "boolean"
    }
  ],
  "transitions": [
    {
      "id": "string",
      "from_state": "string (state id)",
      "to_state": "string (state id)",
      "trigger": "string (event/condition that causes transition)",
      "guard": "string (optional, condition that must be true)",
      "action": "string (optional, action performed during transition)"
    }
  ]
}
```

#### 6.2.6 SPEC_CHUNK Node

> **⚠️ NOTE**: SPEC_CHUNK nodes are derived from `spec/sections.json` chunks during metadata merge.
> See `spec/context.md` for the detailed sections.json schema.

```json
{
  "...common_fields",
  "type": "SPEC_CHUNK",
  "section_number": "string (e.g., '1.5.2')",
  "section_title": "string",
  "chunk_index": "integer (position within section, 0-based)",
  "full_text": "string (the actual extracted text, ≤200 words)",
  "abstract": "string (Haiku-generated summary)",
  "programming_sequence_order": "integer (optional, if part of a sequence)"
}
```

#### 6.2.6.1 Source: spec/sections.json Schema

The `spec/sections.json` file stores hierarchical sections with embedded chunks:

```json
{
  "_metadata": {
    "total_sections": 150,
    "total_chunks": 280,
    "chunk_target_words": 200,
    "abstract_generator": "haiku",
    "validation_attempts": 2
  },
  "sections": {
    "<section_number>": {
      "id": "SEC_X_Y_Z",
      "section_number": "2.1.3",
      "title": "Power Control Register",
      "level": 3,
      
      "hierarchy": {
        "parent": "SEC_2_1",
        "children": []
      },
      
      "source": {
        "spec_page_start": 53,
        "spec_page_end": 54,
        "pdf_page_start": 64,
        "pdf_page_end": 65
      },
      
      "references": {
        "tables": ["TABLE_2_17"],
        "figures": ["FIG_2_15"],
        "related": ["SEC_3_2_4"]
      },
      
      "index": {
        "keywords": ["power", "voltage", "bus power"],
        "technical_terms": ["offset 029h", "RW", "3.3V"]
      },
      
      "abstract": "Section-level summary (Haiku generated)",
      "word_count": 342,
      
      "chunks": [
        {
          "chunk_id": "SEC_2_1_3_C0",
          "chunk_index": 0,
          "abstract": "Chunk-level summary",
          "raw": "Actual spec text (≤200 words)"
        }
      ],
      
      "extraction": {
        "status": "COMPLETED",
        "confidence": 0.95,
        "validated": false
      }
    }
  }
}
```

**Key Design Decisions**:
- **Hierarchy**: Tree structure with parent/children links (root sections have `parent: null`)
- **Chunking**: Sections >200 words split into multiple chunks, never mid-paragraph
- **Embedded content**: No separate MD files, raw text directly in JSON
- **Abstracts**: Haiku-generated at both section and chunk level
- **References**: Tables/figures/cross-sections detected and linked

#### 6.2.7 TABLE Node

```json
{
  "...common_fields",
  "type": "TABLE",
  "table_number": "string (e.g., 'Table 2-1')",
  "title": "string",
  "columns": ["array", "of", "column", "headers"],
  "row_count": "integer",
  "table_type": "enum: REGISTER_MAP | REGISTER_FIELDS | SIGNAL_LIST | TIMING | OTHER",
  "data": [
    ["row1_col1", "row1_col2", "..."],
    ["row2_col1", "row2_col2", "..."]
  ]
}
```

#### 6.2.8 FIGURE Node

```json
{
  "...common_fields",
  "type": "FIGURE",
  "figure_number": "string (e.g., 'Figure 1-1')",
  "title": "string",
  "figure_type": "enum: BLOCK_DIAGRAM | STATE_DIAGRAM | TIMING_DIAGRAM | REGISTER_LAYOUT | FLOWCHART | OTHER",
  "text_diagram_file": "string (path to converted text diagram, if available)",
  "text_diagram_format": "enum: MERMAID | PLANTUML | ASCII | MARKDOWN | NONE"
}
```

### 6.3 Relation Types

```json
{
  "relations": [
    {
      "id": "REL_001",
      "type": "string (see table below)",
      "source_node": "node_id",
      "target_node": "node_id",
      "description": "string (optional context)",
      "bidirectional": "boolean (default false)"
    }
  ]
}
```

| Relation Type | Description | Example |
|---------------|-------------|---------|
| `DESCRIBES` | Spec chunk describes a node | SPEC_001 → REG_005 |
| `CONTAINS` | Parent contains child | FEATURE_001 → REG_002 |
| `CONTROLS` | Register/field controls a feature | REG_003.DMA_EN → FEATURE_002 |
| `TRIGGERS` | Event triggers state transition | REG_004 → SM_001.TRANS_003 |
| `DEPENDS_ON` | Feature depends on another | FEATURE_002 → FEATURE_001 |
| `REFERENCES` | Node references another | SPEC_005 → TABLE_001 |
| `VISUALIZED_BY` | Concept visualized by figure | SM_001 → FIG_003 |
| `CONNECTED_TO` | Port/signal connection | PORT_001 → PORT_002 |
| `SEQUENCE_NEXT` | Programming sequence order | SPEC_010 → SPEC_011 |
| `ENABLES` | One thing enables another | REG_005.bit3 → REG_010 |
| `STATUS_OF` | Register shows status of feature | REG_020 → FEATURE_005 |

### 6.4 Complete Metadata File Structure

```json
{
  "metadata_version": "1.0.0",
  "spec_info": {
    "name": "SD Host Controller Simplified Specification",
    "version": "3.00",
    "date": "February 2011",
    "source_file": "sd_host_3_00.pdf",
    "total_pages": 157
  },
  "extraction_info": {
    "extracted_date": "2026-01-31T10:00:00Z",
    "extractor_version": "1.0.0",
    "llm_context_file": "llm_context.json",
    "validation_status": "DRAFT | VALIDATED | APPROVED",
    "statistics": {
      "total_nodes": 0,
      "by_type": {
        "FEATURE": 0,
        "REGISTER": 0,
        "PORT": 0,
        "STATE_MACHINE": 0,
        "SPEC_CHUNK": 0,
        "TABLE": 0,
        "FIGURE": 0
      },
      "total_relations": 0,
      "validation_coverage": "0%"
    }
  },
  "nodes": [],
  "relations": []
}
```

### 6.5 Schema Design Principles (LOCKED)

> ✅ **Q4 RESOLVED**: Schema is complete. Keep node types **generic** (applicable to other IPs). Categories like Interrupt, Error, Timing go in SPEC_CHUNK `content_type` or `description`, not as separate node types.

> ✅ **Q5 RESOLVED**: **Always extract enum values**, but preserve raw spec format (e.g., `"111b"`) alongside interpreted meaning for traceability.

> ✅ **Q6 RESOLVED**: **Yes**, auto-generate `SEQUENCE_NEXT` relations from `programming_sequence_order` field during Pass 3.

---

## 7. Phase 2: Extraction Pipeline Design

### 7.1 Objective

Define the step-by-step process to extract and populate the metadata from the PDF.

### 7.2 Extraction Strategy Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    EXTRACTION PIPELINE                              │
│              (Uses llm_context.json for guidance)                   │
└─────────────────────────────────────────────────────────────────────┘
                                 │
     ┌───────────────────────────┼───────────────────────────┐
     ▼                           ▼                           ▼
┌─────────────┐          ┌─────────────┐          ┌─────────────┐
│  PASS 1     │          │  PASS 2     │          │  PASS 3     │
│  Structural │          │  Semantic   │          │  Relations  │
│  Extraction │          │  Extraction │          │  & Index    │
└─────────────┘          └─────────────┘          └─────────────┘
     │                           │                           │
     ▼                           ▼                           ▼
- Section headers        - Register parsing        - Link nodes
- Table detection        - Feature extraction      - Generate keywords
- Figure linking         - State machine import    - Cross-reference
                         - Spec chunks             - Validate
```

### 7.3 Pass 1: Structural Extraction

#### 7.3.1 Steps

| Step | Input | Process | Output | Method |
|------|-------|---------|--------|--------|
| 1.1 | PDF + llm_context.json | Extract section headers from text | Section tree | Regex + patterns |
| 1.2 | PDF | Detect all "Table X-Y" references | Table inventory | Regex |
| 1.3 | PDF | Detect all "Figure X-Y" references | Figure inventory | Regex |
| 1.4 | figures_index.json | Link figures to their text diagrams | Figure nodes (draft) | Script |
| 1.5 | llm_context.json | Mark page ranges for each content type | Extraction plan | Script |

#### 7.3.2 Output: Extraction Plan

```json
{
  "extraction_plan": {
    "registers_to_extract": [
      {"name": "SDMA System Address", "offset": "000h", "page": 29},
      {"name": "Block Size", "offset": "004h", "page": 30}
    ],
    "figures_to_link": [
      {"ref": "Figure 1-1", "page": 12, "text_file": "figures/figure_1-1.md"}
    ],
    "sections_to_chunk": [
      {"section": "1.5", "title": "SD Command Generation", "pages": [14, 16]}
    ]
  }
}
```

### 7.4 Pass 2: Semantic Extraction

#### 7.4.1 Register Extraction (HYBRID: Custom Parser FIRST)

> ✅ **Q7 RESOLVED**: Custom parser runs FIRST. LLM only used for failures/edge cases.

**Strategy**:
1. **Step A**: Parse register map table to get complete register list (name + offset)
2. **Step B**: For each register, use custom parser on definition section
3. **Step C**: LLM validates/fixes only low-confidence or failed extractions
4. **Step D**: User validates samples + all low-confidence results

```
┌─────────────────────────────────────────────────────────────────────┐
│           REGISTER EXTRACTION PIPELINE (Custom Parser First)        │
└─────────────────────────────────────────────────────────────────────┘

Step A: Build Register Inventory from Register Map
                │
                ▼
┌───────────────────────────────────┐
│ SCRIPT: extract_register_map.py  │
│ - Parse llm_context register_map │
│ - Extract all register names     │
│ - Extract all offsets            │
│ - Output: register_inventory.json│
└───────────────────────────────────┘
                │
                ▼
Step B: Custom Parser on Each Register (pages from llm_context)
                │
                ▼
┌───────────────────────────────────┐
│ SCRIPT: parse_register.py        │
│ - Find "Register (Offset XXXh)"  │
│ - Parse Location|Attrib|Field    │
│ - Extract bit positions          │
│ - Extract enum values (raw+meaning)│
│ - Assign confidence score        │
└───────────────────────────────────┘
                │
    ┌───────────┴───────────┐
    ▼                       ▼
 SUCCESS                 FAILURE
 (confidence ≥ 0.7)      (confidence < 0.7 OR parse error)
    │                       │
    ▼                       ▼
┌─────────────┐     ┌───────────────────────────────┐
│ Add to      │     │ LLM FALLBACK                  │
│ metadata    │     │ - Send raw text + failure info│
│ (AUTO)      │     │ - LLM extracts structure      │
└─────────────┘     │ - Confidence = LLM_ASSISTED   │
                    └───────────────────────────────┘
                                │
                                ▼
Step D: User Validation Checkpoint
                │
                ▼
┌───────────────────────────────────┐
│ VALIDATION REQUIRED FOR:         │
│ - All confidence < 0.7           │
│ - All LLM_ASSISTED extractions   │
│ - Random sample (3-5) of AUTO    │
└───────────────────────────────────┘
```

#### 7.4.2 Feature Extraction

```
Introduction/Summary sections (from llm_context.json)
                │
                ▼
┌───────────────────────────────────┐
│ LLM EXTRACTION                   │
│ Prompt: "Extract distinct high-  │
│ level features from this text.   │
│ For each feature provide:        │
│ - name, category, description"   │
└───────────────────────────────────┘
                │
                ▼
┌───────────────────────────────────┐
│ SCRIPT: dedupe_features.py       │
│ - Remove duplicates              │
│ - Merge related entries          │
└───────────────────────────────────┘
                │
                ▼
        FEATURE_xxx nodes
```

#### 7.4.3 State Machine Import

```
figures/figures_index.json (type = STATE_DIAGRAM)
                │
                ▼
┌───────────────────────────────────┐
│ SCRIPT: import_state_machine.py  │
│ - Read mermaid/plantuml file     │
│ - Parse states and transitions   │
│ - Create structured node         │
└───────────────────────────────────┘
                │
                ▼
       STATE_MACHINE_xxx nodes
```

#### 7.4.4 Spec Chunk Extraction

> ✅ **Q8 RESOLVED**: Per subsection by default. Per paragraph for critical sections (programming sequences, error handling).

```
All text sections not covered by registers/features
                │
                ▼
┌───────────────────────────────────┐
│ SCRIPT: chunk_by_section.py      │
│ - Split by section headers       │
│ - DEFAULT: per subsection        │
│ - CRITICAL sections: per paragraph│
│ - Maintain hierarchy             │
└───────────────────────────────────┘
                │
                ▼
┌───────────────────────────────────┐
│ LLM CLASSIFICATION               │
│ Prompt: "Classify this chunk:    │
│ DESCRIPTION|PROCEDURE|CONSTRAINT │
│ |NOTE|EXAMPLE|IMPLEMENTATION"    │
│                                   │
│ For PROCEDURE: extract steps     │
│ and assign sequence_order        │
└───────────────────────────────────┘
                │
                ▼
       SPEC_CHUNK_xxx nodes
```

**Critical Sections (per paragraph granularity)**:
- Programming sequences
- Error handling procedures
- Initialization sequences
- Timing constraints

### 7.5 Pass 3: Relations & Index Generation

#### 7.5.1 Automatic Relation Detection

| Detection Method | Relation Type | Example |
|------------------|---------------|---------|
| "See Table X-Y" in text | REFERENCES | SPEC → TABLE |
| "See Figure X-Y" in text | REFERENCES | SPEC → FIGURE |
| Section contains register definition | CONTAINS | FEATURE → REG |
| "This register controls..." | CONTROLS | REG → FEATURE |
| "...enables the X feature" | ENABLES | REG.field → FEATURE |
| State diagram linked to figure | VISUALIZED_BY | SM → FIG |
| Sequential spec chunks in section | SEQUENCE_NEXT | SPEC → SPEC |

#### 7.5.2 Keyword Index Generation

For each node, `index_keywords` are generated by:

1. **Name tokens**: Split node name into words
2. **Technical terms**: Extract from description (register names, acronyms)
3. **Synonyms**: Add common alternatives (DMA ↔ Direct Memory Access)
4. **Related terms**: From connected nodes
5. **Offset/address**: For registers (e.g., "029h", "0x29", "41")

### 7.6 Validation Checkpoints

#### Checkpoint 2A: After Register Extraction

```
┌────────────────────────────────────────────────────────────────────┐
│ REGISTER VALIDATION SUMMARY                                        │
├────────────────────────────────────────────────────────────────────┤
│ Total registers extracted: 45                                      │
│ High confidence (>0.9): 38                                         │
│ Medium confidence (0.7-0.9): 5                                     │
│ Low confidence (<0.7): 2  ◄── REQUIRE USER VALIDATION              │
│                                                                    │
│ Sample for validation (random 3):                                  │
│   - REG_005: Normal Interrupt Status (confidence: 0.95)            │
│   - REG_022: ADMA System Address (confidence: 0.88)                │
│   - REG_041: Shared Bus Control (confidence: 0.72) ◄── LOW         │
│                                                                    │
│ [VALIDATE SAMPLES] [VALIDATE LOW CONFIDENCE] [APPROVE ALL]         │
└────────────────────────────────────────────────────────────────────┘
```

#### Checkpoint 2B: After State Machine Import

**ALWAYS validate state machines** — critical for simulation accuracy.

```
┌────────────────────────────────────────────────────────────────────┐
│ STATE MACHINE VALIDATION: SM_001 (Command Circuit)                 │
├────────────────────────────────────────────────────────────────────┤
│ States: 5                                                          │
│ Transitions: 8                                                     │
│                                                                    │
│ Diagram:                                                           │
│   [Idle] ──CMD_ISSUED──► [Wait_Resp] ──RESP_OK──► [Complete]       │
│     ▲                         │                                    │
│     └─────────TIMEOUT─────────┘                                    │
│                                                                    │
│ Source: Figure 1-5, Page 18                                        │
│ Text file: figures/figure_1-5_command_circuit.md                   │
│                                                                    │
│ Questions:                                                         │
│   1. Are all states captured? [Y/N]                                │
│   2. Are all transitions correct? [Y/N]                            │
│   3. Any missing guards/actions? [Y/N]                             │
│                                                                    │
│ [APPROVE] [EDIT] [REJECT & RE-EXTRACT]                             │
└────────────────────────────────────────────────────────────────────┘
```

### 7.7 Discussion Points for Phase 2

> **Q7**: For the hybrid register parser, should we build the custom parser first, then use LLM only for failures? Or LLM-first with parser validation?

> **Q8**: How granular should spec chunks be? Per paragraph? Per subsection?

---

## 8. Phase 3: Validation & Quality Assurance

### 8.1 Validation Pyramid

```
                    ┌───────────────┐
                    │   SEMANTIC    │  ◄── Does meaning match spec?
                    │   (LLM+Human) │      (Spot checks)
                    └───────────────┘
                           │
                    ┌──────┴──────┐
                    │  COHERENCE  │  ◄── Are relations logical?
                    │   (Script)  │      (No orphans, valid refs)
                    └─────────────┘
                           │
               ┌───────────┴───────────┐
               │   COMPLETENESS        │  ◄── Is everything extracted?
               │     (Script)          │      (Coverage checks)
               └───────────────────────┘
                           │
          ┌────────────────┴────────────────┐
          │        SCHEMA VALIDATION        │  ◄── Is JSON valid?
          │           (Script)              │      (JSON Schema)
          └─────────────────────────────────┘
```

### 8.2 Validation Scripts

| Script | Purpose | Run When |
|--------|---------|----------|
| `validate_schema.py` | Check JSON structure | After any modification |
| `validate_completeness.py` | Check all registers/features extracted | End of Pass 2 |
| `validate_coherence.py` | Check relations, no orphans | End of Pass 3 |
| `validate_coverage.py` | Compare node pages vs total pages | Final check |
| `spot_check.py` | Random sample validation prompts | User-triggered |

### 8.3 Completeness Checklist

- [ ] All registers from register map are extracted
- [ ] All figures have corresponding FIGURE nodes
- [ ] All tables have corresponding TABLE nodes
- [ ] Key features from intro are captured
- [ ] State machines from figures are imported
- [ ] No pages in llm_context.json ranges are uncovered

### 8.4 Cross-Reference Validation

```python
# Pseudo-code for cross-reference validation
for node in metadata.nodes:
    if node.type == "REGISTER":
        # Verify the register exists at claimed offset
        assert node.spec_table in found_tables
        assert node.offset matches llm_context hints
    
    if node.type == "STATE_MACHINE":
        # Verify all transitions reference valid states
        for trans in node.transitions:
            assert trans.from_state in [s.id for s in node.states]
            assert trans.to_state in [s.id for s in node.states]
```

---

## 9. Phase 4: Access Script Design

### 9.1 Objective

Create `metadata_access.py` — the **ONLY** interface between agent and metadata.

### 9.2 Design Principles

1. **No Direct JSON Access**: Agent NEVER sees raw JSON
2. **Minimal Sufficient Primitives**: Only expose necessary operations
3. **Structured Output**: Formatted for agent consumption
4. **Query Logging**: All accesses logged for debugging
5. **Read-Only**: No modification primitives (separate admin script)

### 9.3 Command Interface

```bash
python metadata_access.py <command> [arguments] [--options]
```

### 9.4 Primitives

#### 9.4.1 Node Retrieval

| Command | Arguments | Description |
|---------|-----------|-------------|
| `get_node <id>` | Node ID | Get full node by ID |
| `get_register <name_or_offset>` | Name or offset (e.g., "029h") | Get register |
| `get_feature <name>` | Feature name | Get feature |
| `get_port <name>` | Port name | Get port |
| `get_state_machine <name>` | State machine name | Get state machine |
| `get_figure <number>` | Figure number (e.g., "1-4") | Get figure |
| `get_table <number>` | Table number (e.g., "2-17") | Get table |

#### 9.4.2 Search

| Command | Arguments | Options | Description |
|---------|-----------|---------|-------------|
| `search <keywords>` | Comma-separated keywords | `--type=REG,FEATURE` | Keyword search |
| `search_text <query>` | Natural language query | `--limit=10` | Semantic search |
| `list_nodes` | - | `--type=REGISTER` | List all nodes of type |

#### 9.4.3 Relations

| Command | Arguments | Options | Description |
|---------|-----------|---------|-------------|
| `get_related <node_id>` | Node ID | `--relation=CONTROLS` | Get related nodes |
| `get_described_by <node_id>` | Node ID | - | Get spec chunks describing node |
| `get_controls <feature_id>` | Feature ID | - | Get registers controlling feature |
| `get_sequence <start_node_id>` | Node ID | - | Get programming sequence |

#### 9.4.4 Utilities

| Command | Arguments | Description |
|---------|-----------|-------------|
| `info` | - | Get spec info and statistics |
| `source <node_id>` | Node ID | Get source location (page, position) |
| `coverage` | - | Get coverage statistics |

### 9.5 Output Format

All commands return structured text (not raw JSON):

```
=== REGISTER: Power Control Register ===
ID: REG_029
Offset: 0x029
Size: 8 bits
Reset: 0x00

Fields:
  [07:04] Reserved (Rsvd)
  [03:01] SD Bus Voltage Select (RW) - Reset: 0b000
          Values: 111b=3.3V, 110b=3.0V, 101b=1.8V
  [00]    SD Bus Power (RW) - Reset: 0
          1=Power on, 0=Power off

Source: Page 53, Table 2-17
Related: FEATURE_003 (Power Management) via CONTROLS

[Query logged: 2026-01-31T10:15:32Z]
```

### 9.6 Search Implementation

For `search_text` (semantic search), options:

1. **Simple TF-IDF** (local, no dependencies)
2. **BM25** (better ranking, still local)
3. **Embedding-based** (requires vector store — more complex)

**Recommendation**: Start with BM25 (good balance of quality and simplicity).

### 9.7 Discussion Points for Phase 4

> **Q9**: Should there be a `get_register_field <register> <field_name>` primitive?

> **Q10**: Should search support regex patterns?

> **Q11**: For `get_sequence`, should it return the full chain or just immediate next?

---

## 10. Phase 5: Orchestration Agent & Prompts

### 10.1 Objective

Define prompts for:
1. **Extraction Agent** — Creates metadata from PDF
2. **Query Agent** — Answers questions using metadata

### 10.2 Extraction Agent System Prompt

```markdown
# SD HOST SPECIFICATION EXTRACTION AGENT

You are an agent that extracts structured information from the SD Host Controller 
Specification PDF to create a comprehensive metadata.json file.

## Available Resources
- PDF: sd_host_3_00.pdf (157 pages)
- Hints: llm_context.json (section page ranges, patterns)
- Figures: figures/ folder (pre-converted to text diagrams)
- Scripts: Various extraction and validation scripts

## Your Process

### Phase 1: Structural Extraction
1. Read llm_context.json to understand document structure
2. Run extract_sections.py to get section tree
3. Run list_figures_tables.py to inventory all references
4. Create extraction plan

### Phase 2: Semantic Extraction  
For each content type:

**Registers** (pages from llm_context.json.section_hints.register_definitions):
1. Run extract_register_text.py for page range
2. Run parse_register_table.py on output
3. For low-confidence results, analyze raw text and correct
4. Add to metadata

**Features** (pages from llm_context.json.section_hints.features_summary):
1. Read text from specified pages
2. Identify distinct features (name, category, description)
3. Add to metadata

**State Machines**:
1. Read figures/figures_index.json for STATE_DIAGRAM entries
2. Run import_state_machine.py for each
3. ALWAYS request user validation for state machines
4. Add to metadata

**Spec Chunks**:
1. Run chunk_by_section.py on remaining text
2. Classify each chunk (DESCRIPTION, PROCEDURE, etc.)
3. Add to metadata

### Phase 3: Relations & Indexing
1. Run detect_relations.py
2. Run generate_keywords.py
3. Validate with validate_coherence.py

### Validation Rules
- ALWAYS validate state machines with user
- ALWAYS validate low-confidence (<0.7) nodes
- Request validation for sample of each type (3-5 nodes)
- Run all validation scripts before declaring complete

## Output Format
After each major step, report:
- Nodes created (count by type)
- Confidence summary
- Items requiring user attention
- Next steps

## Constraints
- Never skip validation for STATE_MACHINE or low-confidence nodes
- Always include source page/position for every node
- If unsure, ask user rather than guess
- Save progress incrementally (resumable)
```

### 10.3 Query Agent System Prompt

```markdown
# SD HOST SPECIFICATION QUERY AGENT

You are an agent that answers questions about the SD Host Controller specification.
You MUST use ONLY the information in the extracted metadata.

## CRITICAL CONSTRAINTS

### 🔒 MANDATORY: Metadata-Only Responses
1. You can ONLY access information through metadata_access.py commands
2. You MUST NOT use your training knowledge about SD Host controllers
3. You MUST NOT make up information not present in the metadata
4. You MUST cite source node IDs for every fact you state
5. If information is not in metadata, say: "The metadata does not contain this information"

### ✅ Allowed Common Knowledge
- Units: V=Volts, mA=milliamps, MHz=Megahertz
- Abbreviations: RW=Read-Write, RO=Read-Only, DMA=Direct Memory Access
- Binary/hex conversions: 0xFF = 255 = 11111111b
- Standard terminology

## Your Tools

You can run these commands:
```
python metadata_access.py <command> [args]
```

### Retrieval Commands
- `get_register <name_or_offset>` - Get register details
- `get_feature <name>` - Get feature details  
- `get_state_machine <name>` - Get state machine
- `get_node <id>` - Get any node by ID

### Search Commands
- `search <keywords>` - Search by keywords (comma-separated)
- `search_text <query>` - Semantic search
- `list_nodes --type=<TYPE>` - List all nodes of a type

### Relation Commands
- `get_related <node_id>` - Get related nodes
- `get_described_by <node_id>` - Get documentation for a node
- `get_controls <feature_id>` - Get registers that control a feature
- `get_sequence <node_id>` - Get programming sequence

### Utility Commands
- `info` - Get spec overview
- `source <node_id>` - Get PDF page/position

## Response Format

For every answer:

1. **Show your search process**:
   "I'll search for information about X..."
   [Run command]
   
2. **Present findings with citations**:
   "According to the specification:
   - [Fact 1] [Source: REG_005]
   - [Fact 2] [Source: SPEC_023]"

3. **Acknowledge gaps**:
   "The metadata does not contain information about Y."

4. **Never say**:
   - "Based on my knowledge..."
   - "Typically, SD Host controllers..."
   - "I believe..." (unless citing metadata)

## Example Interaction

**User**: How do I enable DMA transfers?

**Agent**: I'll search for DMA-related information in the metadata.

```
python metadata_access.py search "DMA,ADMA,transfer"
python metadata_access.py get_controls FEATURE_DMA
```

Based on the specification metadata:

**DMA is enabled through these steps:**

1. Set the ADMA System Address Register (offset 0x58) with the descriptor table address
   [Source: REG_022]

2. In Host Control 1 Register (offset 0x28), set the DMA Select field (bits 4:3):
   - 00b = SDMA
   - 10b = ADMA2
   - 11b = ADMA2/ADMA3
   [Source: REG_010, field DMA_SEL]

3. Set appropriate bits in Block Size Register (offset 0x04) for transfer size
   [Source: REG_002]

**Related documentation**: See SPEC_045 for the complete DMA programming sequence.

[Sources: REG_022, REG_010, REG_002, SPEC_045, FEATURE_003]
```

### 10.4 User Validation Prompt Template

```markdown
## Validation Request: {{ node.type }} Node

**ID**: {{ node.id }}
**Name**: {{ node.name }}
**Source**: Page {{ node.source.page }}
**Confidence**: {{ node.confidence }}

### Extracted Content
{{ node | formatted }}

### Original PDF Text (Page {{ node.source.page }})
```
{{ raw_source_text }}
```

### Validation Questions
1. Is the extraction accurate? 
2. Are there any errors or omissions?
3. Should any related nodes be linked?

### Actions
- **APPROVE**: Extraction is correct → Mark as USER_VALIDATED
- **EDIT**: Provide corrections → Will update node
- **REJECT**: Fundamentally wrong → Will re-extract or remove
- **SKIP**: Need more context → Will revisit later
```

---

## 11. All Questions Resolved & Next Steps

### 11.1 Questions Status (ALL RESOLVED)

| # | Question | Decision | Status |
|---|----------|----------|--------|
| Q4 | Is schema complete for SD Host? | Keep generic, categories in SPEC_CHUNK | ✅ RESOLVED |
| Q5 | Always extract enum values from register fields? | Yes, with raw value preservation | ✅ RESOLVED |
| Q6 | Auto-generate SEQUENCE_NEXT relations? | Yes, from programming_sequence_order | ✅ RESOLVED |
| Q7 | Custom parser first vs LLM first for registers? | Custom parser FIRST, LLM for failures | ✅ RESOLVED |
| Q8 | Spec chunk granularity? | Per subsection, per paragraph for critical | ✅ RESOLVED |
| Q9 | Add `get_register_field` primitive? | Defer to v1.1 if needed | ✅ RESOLVED |
| Q10 | Support regex in search? | Defer to v1.1 if needed | ✅ RESOLVED |
| Q11 | `get_sequence` return full chain? | Yes, return full chain | ✅ RESOLVED |

### 11.2 Implementation Roadmap

#### Phase -1: Figure Pre-Processing (User Task)
- [ ] Export all 83 figures from PDF with page numbers
- [ ] Transcribe each to text format (Mermaid/PlantUML/ASCII)
- [ ] Create `figures_index.json` with full traceability
- [ ] Validate all transcriptions

#### Phase 0: Setup & Analysis (Agent-Assisted)
- [ ] Create folder structure in workspace
- [ ] Run `analyze_pdf_structure.py`
- [ ] Generate and populate `llm_context.json`
- [ ] Identify register map table + register definitions section pages

#### Phase 2: Extraction (Agent + User Validation)
- [ ] Prototype register parser on 2-3 sample pages
- [ ] Iterate and refine parser
- [ ] Extract all registers with user validation checkpoints
- [ ] Extract features, state machines, spec chunks

#### Phase 3-5: Validation, Access Script, Prompts
- [ ] Build validation scripts
- [ ] Implement `metadata_access.py`
- [ ] Create and test agent prompts

### 11.3 Proposed Folder Structure

```
sdhost-3.0/
├── source/
│   └── sd_host_3_00.pdf              # Original spec (move here)
├── figures/
│   ├── figures_index.json            # Index of converted figures
│   ├── figure_1-1_block_diagram.md   # Converted diagrams
│   └── ...
├── extraction/
│   ├── llm_context.json              # Pre-metadata hints
│   ├── extraction_plan.json          # Generated extraction plan
│   └── extraction_log.json           # Progress tracking
├── metadata/
│   ├── metadata.json                 # THE metadata file
│   ├── metadata_schema.json          # JSON Schema for validation
│   └── backups/                      # Version backups
├── scripts/
│   ├── metadata_access.py            # Access script (Phase 4)
│   ├── analyze_pdf_structure.py      # Phase 0
│   ├── extract_register_text.py      # Phase 2
│   ├── parse_register_table.py       # Phase 2
│   ├── import_state_machine.py       # Phase 2
│   ├── chunk_by_section.py           # Phase 2
│   ├── detect_relations.py           # Phase 3
│   ├── generate_keywords.py          # Phase 3
│   ├── validate_schema.py            # Phase 3
│   ├── validate_completeness.py      # Phase 3
│   └── validate_coherence.py         # Phase 3
├── prompts/
│   ├── extraction_agent.md           # Phase 5
│   ├── query_agent.md                # Phase 5
│   └── validation_request.md         # Phase 5
└── docs/
    ├── process.md                    # This file
    ├── initial.md                    # Original requirements
    └── decision_log.md               # Track decisions
```

---

## Appendix A: Quick Reference - Extraction Commands

```bash
# Phase 0
python scripts/analyze_pdf_structure.py source/sd_host_3_00.pdf
python scripts/generate_llm_context_template.py > extraction/llm_context.json

# Phase 2 - Registers
python scripts/extract_register_text.py --pages 29-90 --output temp/registers_raw.json
python scripts/parse_register_table.py temp/registers_raw.json --output temp/registers_parsed.json

# Phase 2 - State Machines
python scripts/import_state_machine.py figures/figure_1-4_suspend.md --output temp/sm_1-4.json

# Phase 3 - Validation
python scripts/validate_schema.py metadata/metadata.json
python scripts/validate_completeness.py metadata/metadata.json --context extraction/llm_context.json
python scripts/validate_coherence.py metadata/metadata.json

# Query Agent
python scripts/metadata_access.py search "DMA,transfer"
python scripts/metadata_access.py get_register "Power Control"
python scripts/metadata_access.py get_related REG_029
```

---

**Document Version**: 1.0.0  
**Last Updated**: 2026-01-31  
**Status**: 🔒 LOCKED - All questions resolved, ready for implementation  
**Next Action**: User begins Phase -1 (Figure Pre-Processing)
