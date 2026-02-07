# SD Host RAG System - Process Definition Document

> **Status**: DRAFT - Discussion Phase  
> **Goal**: Define a clear, reproducible, testable, and validable plan for building a structured RAG system for embedded IP specifications.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Phase 0: PDF Pre-Analysis & Preparation](#2-phase-0-pdf-pre-analysis--preparation)
3. [Phase 1: Metadata Structure Definition](#3-phase-1-metadata-structure-definition)
4. [Phase 2: Extraction Pipeline Design](#4-phase-2-extraction-pipeline-design)
5. [Phase 3: Validation & Quality Assurance](#5-phase-3-validation--quality-assurance)
6. [Phase 4: Access Script Design](#6-phase-4-access-script-design)
7. [Phase 5: Orchestration Agent & Prompts](#7-phase-5-orchestration-agent--prompts)
8. [Open Questions & Discussion Points](#8-open-questions--discussion-points)

---

## 1. Overview

### 1.1 Problem Statement

We need to extract structured information from IP specification PDFs (e.g., SD Host 3.0) into a queryable graph-based metadata structure. This metadata will serve as the **single source of truth** for an agent that answers questions about the IP.

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

### 1.3 Constraints Recap

- [ ] Agent must **NEVER** access `metadata.json` directly
- [ ] Agent answers based on metadata **ONLY** (no hallucination from training data)
- [ ] Exception: Common knowledge (units like V=Volts, standard acronyms)
- [ ] PDF may contain non-text elements (tables, images, diagrams)
- [ ] Process must be iterative and allow user validation
- [ ] Coverage tracking must be built-in for future implementation tracking

---

## 2. Phase 0: PDF Pre-Analysis & Preparation

### 2.1 Objective

Before any extraction, we need to understand the PDF structure and identify potential extraction challenges.

### 2.2 Sub-Steps

#### 2.2.1 PDF Structure Analysis

| Check Item | Method | Expected Output |
|------------|--------|-----------------|
| Is text selectable? | Manual + PyMuPDF test | Yes/No |
| Are tables structured or images? | Visual inspection | List of table pages |
| Are state machine diagrams images? | Visual inspection | List of diagram pages |
| Is there a ToC? | Manual check | ToC page range |
| Register tables format | Manual check | Format description |

#### 2.2.2 Pre-Processing Decision Tree

```
PDF Analysis
    │
    ├─► Text fully extractable?
    │       │
    │       ├─► YES → Proceed to Phase 1
    │       │
    │       └─► NO → Which parts are problematic?
    │               │
    │               ├─► Tables as images → OCR + Manual correction
    │               ├─► Diagrams → Manual extraction or LLM vision
    │               └─► Scanned pages → Full OCR pipeline
    │
    └─► Tables structured?
            │
            ├─► YES → Use tabula-py / camelot
            │
            └─► NO (merged cells, complex layout) 
                    → Custom parsing or manual extraction
```

#### 2.2.3 Output of Phase 0

- `pdf_analysis_report.md` containing:
  - Total pages
  - Extractable text percentage estimate
  - List of problematic pages/sections
  - Recommended pre-processing steps
  - Table inventory (page, type, content summary)
  - Figure/Diagram inventory

### 2.3 Discussion Points for Phase 0

> **Q1**: Do you have the SD Host 3.0 PDF already? If yes, have you done any preliminary analysis?

> **Q2**: What tools are acceptable for PDF parsing? (PyMuPDF, pdfplumber, tabula-py, camelot, LLM vision APIs?)

> **Q3**: For images/diagrams (state machines), do you prefer:
> - (a) Manual transcription to structured format
> - (b) LLM vision API extraction
> - (c) Skip and mark as "manual review required"

---

## 3. Phase 1: Metadata Structure Definition

### 3.1 Objective

Define the complete JSON schema for the metadata file.

### 3.2 Proposed Node Types & Schemas

#### 3.2.1 Common Fields (All Nodes)

```json
{
  "id": "string (prefix_uniqueid, e.g., REG_001, PORT_001)",
  "type": "enum: FEATURE | REGISTER | PORT | STATE_MACHINE | SPEC_CHUNK | TABLE | FIGURE",
  "name": "string (human readable name)",
  "description": "string (extracted or summarized description)",
  "index_keywords": ["array", "of", "searchable", "terms"],
  "source": {
    "page": "integer",
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
    "notes": "string (optional)"
  },
  "confidence": "float 0-1 (extraction confidence, for validation)"
}
```

#### 3.2.2 FEATURE Node (Additional Fields)

```json
{
  "...common_fields",
  "type": "FEATURE",
  "category": "string (e.g., 'DMA', 'Interrupt', 'Power Management')",
  "spec_section": "string (e.g., '2.1.3')"
}
```

#### 3.2.3 REGISTER Node (Additional Fields)

```json
{
  "...common_fields",
  "type": "REGISTER",
  "offset": "string (hex, e.g., '0x00')",
  "size_bits": "integer (e.g., 32)",
  "reset_value": "string (hex)",
  "access": "enum: RO | RW | WO | RW1C | ...",
  "fields": [
    {
      "name": "string",
      "bits": "string (e.g., '31:24' or '7')",
      "access": "string",
      "reset": "string",
      "description": "string"
    }
  ]
}
```

#### 3.2.4 PORT Node (Additional Fields)

```json
{
  "...common_fields",
  "type": "PORT",
  "direction": "enum: INPUT | OUTPUT | INOUT",
  "width_bits": "integer",
  "signal_type": "string (e.g., 'clock', 'reset', 'data', 'control')",
  "active_level": "string (e.g., 'active_low', 'active_high')",
  "connected_to": "string (optional, what it connects to)"
}
```

#### 3.2.5 STATE_MACHINE Node (Additional Fields)

```json
{
  "...common_fields",
  "type": "STATE_MACHINE",
  "states": [
    {
      "id": "string",
      "name": "string",
      "description": "string",
      "is_initial": "boolean",
      "is_final": "boolean"
    }
  ],
  "transitions": [
    {
      "from_state": "string (state id)",
      "to_state": "string (state id)",
      "trigger": "string (condition/event)",
      "action": "string (optional)"
    }
  ]
}
```

#### 3.2.6 SPEC_CHUNK Node (Additional Fields)

```json
{
  "...common_fields",
  "type": "SPEC_CHUNK",
  "section_number": "string (e.g., '3.2.1')",
  "section_title": "string",
  "content_type": "enum: DESCRIPTION | PROCEDURE | CONSTRAINT | NOTE | EXAMPLE",
  "full_text": "string (the actual content)"
}
```

#### 3.2.7 TABLE Node (Additional Fields)

```json
{
  "...common_fields",
  "type": "TABLE",
  "table_number": "string (e.g., 'Table 2-1')",
  "columns": ["array", "of", "column", "names"],
  "row_count": "integer",
  "data": "array of arrays (optional, actual table data)"
}
```

#### 3.2.8 FIGURE Node (Additional Fields)

```json
{
  "...common_fields",
  "type": "FIGURE",
  "figure_number": "string (e.g., 'Figure 3-1')",
  "figure_type": "enum: BLOCK_DIAGRAM | STATE_DIAGRAM | TIMING_DIAGRAM | FLOWCHART | OTHER",
  "extracted_info": "string (any text/info extracted from the figure)"
}
```

### 3.3 Relation Types

```json
{
  "relations": [
    {
      "id": "REL_001",
      "type": "enum (see below)",
      "source_node": "node_id",
      "target_node": "node_id",
      "description": "string (optional, context)"
    }
  ]
}
```

#### Proposed Relation Types:

| Relation Type | Description | Example |
|---------------|-------------|---------|
| `DESCRIBES` | Spec chunk describes a node | SPEC_001 DESCRIBES REG_005 |
| `CONTAINS` | Parent contains child | FEATURE_001 CONTAINS REG_002 |
| `CONTROLS` | Register controls a feature | REG_003 CONTROLS FEATURE_002 |
| `TRIGGERS` | Event/register triggers state change | REG_004 TRIGGERS SM_001 |
| `DEPENDS_ON` | Node depends on another | FEATURE_002 DEPENDS_ON FEATURE_001 |
| `REFERENCES` | Node references another | SPEC_005 REFERENCES TABLE_001 |
| `VISUALIZED_BY` | Node is visualized by figure | SM_001 VISUALIZED_BY FIG_003 |
| `CONNECTED_TO` | Port connection | PORT_001 CONNECTED_TO PORT_002 |
| `FIELD_OF` | Field belongs to register | (implicit in register.fields) |
| `SEQUENCE_STEP` | Part of a programming sequence | SPEC_010 SEQUENCE_STEP SPEC_011 |

### 3.4 Complete Metadata File Structure

```json
{
  "metadata_version": "1.0.0",
  "spec_info": {
    "name": "SD Host Controller Simplified Specification",
    "version": "3.00",
    "date": "string",
    "source_file": "sd_host_3_00.pdf",
    "total_pages": "integer"
  },
  "extraction_info": {
    "extracted_date": "ISO date",
    "extractor_version": "string",
    "validation_status": "enum: DRAFT | VALIDATED | APPROVED"
  },
  "nodes": [
    { "...node objects" }
  ],
  "relations": [
    { "...relation objects" }
  ]
}
```

### 3.5 Discussion Points for Phase 1

> **Q4**: Is the proposed schema complete? Any missing node types for SD Host specifically?

> **Q5**: For register fields, should we support nested fields (bit groups)?

> **Q6**: Should we add a `version` field to nodes for tracking changes across spec revisions?

> **Q7**: The `coverage` field - what statuses make sense for your workflow?

> **Q8**: Do you need to track "optional" vs "mandatory" features per the spec?

---

## 4. Phase 2: Extraction Pipeline Design

### 4.1 Objective

Define the step-by-step process to extract and populate the metadata from the PDF.

### 4.2 Extraction Strategy Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    EXTRACTION PIPELINE                              │
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
- ToC parsing            - Register details        - Link nodes
- Section boundaries     - Port details            - Generate keywords
- Table detection        - State machines          - Validate refs
- Figure detection       - Feature enrichment      - Cross-check
```

### 4.3 Pass 1: Structural Extraction (Semi-Automated)

#### 4.3.1 Steps

| Step | Input | Process | Output | Automation Level |
|------|-------|---------|--------|------------------|
| 1.1 | PDF | Extract ToC | Section list with pages | Automated |
| 1.2 | PDF | Detect all tables | Table inventory | Automated |
| 1.3 | PDF | Detect all figures | Figure inventory | Automated |
| 1.4 | PDF | Extract raw text per page | Page text map | Automated |
| 1.5 | Table inventory | Classify tables (register vs other) | Classified tables | LLM-assisted |
| 1.6 | Figure inventory | Classify figures | Classified figures | LLM-assisted |

#### 4.3.2 User Validation Checkpoint #1

- [ ] Review ToC extraction accuracy
- [ ] Confirm table classifications
- [ ] Confirm figure classifications
- [ ] Identify any missed structural elements

### 4.4 Pass 2: Semantic Extraction (LLM-Assisted + Scripts)

#### 4.4.1 Register Extraction Sub-Pipeline

```
Register Tables
      │
      ▼
┌─────────────────┐
│ Table Parser    │ ◄── Script: parse_register_table.py
│ (tabula/custom) │
└─────────────────┘
      │
      ▼
┌─────────────────┐
│ LLM Structurer  │ ◄── Prompt: "Given this raw table, extract register fields..."
│                 │
└─────────────────┘
      │
      ▼
┌─────────────────┐
│ Schema Validator│ ◄── Script: validate_register_schema.py
│                 │
└─────────────────┘
      │
      ▼
  REG_xxx node
```

#### 4.4.2 Feature Extraction Sub-Pipeline

```
Intro/Summary Sections
      │
      ▼
┌─────────────────┐
│ Text Chunker    │ ◄── Script: chunk_by_section.py
│                 │
└─────────────────┘
      │
      ▼
┌─────────────────┐
│ LLM Extractor   │ ◄── Prompt: "Identify distinct features in this section..."
│                 │
└─────────────────┘
      │
      ▼
┌─────────────────┐
│ Deduplication   │ ◄── Script: dedupe_features.py
│                 │
└─────────────────┘
      │
      ▼
  FEATURE_xxx nodes
```

#### 4.4.3 State Machine Extraction Sub-Pipeline

```
State Diagram Figures + Related Text
      │
      ├─► Image ──► LLM Vision API ──► States & Transitions (raw)
      │
      └─► Text ──► LLM Extractor ──► States & Transitions (raw)
      │
      ▼
┌─────────────────┐
│ Merge & Validate│ ◄── Combine image + text extracted info
│                 │
└─────────────────┘
      │
      ▼
  STATE_MACHINE_xxx node
```

#### 4.4.4 Port Extraction Sub-Pipeline

```
Signal/Port Tables or Sections
      │
      ▼
┌─────────────────┐
│ Port Parser     │ ◄── Script or LLM
│                 │
└─────────────────┘
      │
      ▼
  PORT_xxx nodes
```

#### 4.4.5 Spec Chunk Extraction Sub-Pipeline

```
All remaining text sections
      │
      ▼
┌─────────────────┐
│ Semantic Chunker│ ◄── Split by: section, paragraph, or semantic boundary
│                 │
└─────────────────┘
      │
      ▼
┌─────────────────┐
│ LLM Classifier  │ ◄── Prompt: "Classify this chunk: DESCRIPTION/PROCEDURE/..."
│                 │
└─────────────────┘
      │
      ▼
  SPEC_CHUNK_xxx nodes
```

#### 4.4.6 User Validation Checkpoint #2

For EACH node type, present to user:

```
┌────────────────────────────────────────────────────────────┐
│ NODE VALIDATION REQUEST                                    │
├────────────────────────────────────────────────────────────┤
│ Type: REGISTER                                             │
│ ID: REG_005                                                │
│ Name: Normal Interrupt Status Register                     │
│ Extracted from: Page 45, Table 2-5                         │
│                                                            │
│ Fields Extracted:                                          │
│   [31:16] Reserved (RO, 0x0000)                            │
│   [15] Error Interrupt (RW1C, 0x0)                         │
│   ...                                                      │
│                                                            │
│ Confidence: 0.92                                           │
│                                                            │
│ ► [APPROVE] [EDIT] [REJECT] [VIEW SOURCE]                  │
└────────────────────────────────────────────────────────────┘
```

**Validation Options:**
- **Batch Mode**: Validate by type (all registers at once)
- **Confidence Filter**: Auto-approve if confidence > threshold
- **Diff Mode**: Show only uncertain extractions

### 4.5 Pass 3: Relations & Index Generation

#### 4.5.1 Automatic Relation Detection

| Method | Detects |
|--------|---------|
| Text reference matching | "See Register X" → REFERENCES |
| Section hierarchy | Parent section contains → CONTAINS |
| Keyword co-occurrence | Feature + Register in same chunk → DESCRIBES |
| Explicit spec language | "This register controls..." → CONTROLS |

#### 4.5.2 Keyword Index Generation

For each node, generate `index_keywords` by:
1. Extracting nouns and technical terms from name + description
2. Adding synonyms for common terms (e.g., "DMA" → ["DMA", "Direct Memory Access"])
3. Adding abbreviation expansions
4. Including related node names

#### 4.5.3 User Validation Checkpoint #3

- [ ] Review detected relations (especially CONTROLS, DEPENDS_ON)
- [ ] Verify no orphan nodes (nodes with no relations)
- [ ] Spot-check keyword indexes

### 4.6 Discussion Points for Phase 2

> **Q9**: What's the acceptable error rate before user validation is required?
> - Option A: Validate ALL nodes (safest, most time-consuming)
> - Option B: Validate only low-confidence nodes (<0.8)
> - Option C: Validate samples per type + full validation for complex types (state machines)

> **Q10**: For register extraction, SD Host spec likely has a consistent table format. Should we:
> - (a) Build a custom parser tuned to that format
> - (b) Use generic LLM extraction
> - (c) Hybrid: parser + LLM validation

> **Q11**: How to handle spec ambiguities? (e.g., unclear if something is optional)
> - Flag for user review?
> - Add "ambiguity" field to node?

> **Q12**: Should extraction be resumable? (save progress, continue later)

---

## 5. Phase 3: Validation & Quality Assurance

### 5.1 Objective

Ensure the extracted metadata is complete, accurate, and consistent.

### 5.2 Validation Layers

```
┌─────────────────────────────────────────────────────────────────────┐
│                     VALIDATION PYRAMID                              │
└─────────────────────────────────────────────────────────────────────┘

                    ┌───────────────┐
                    │   SEMANTIC    │  ◄── Does the meaning match the spec?
                    │   VALIDATION  │      (LLM + Human review)
                    └───────────────┘
                           │
                    ┌──────┴──────┐
                    │  COHERENCE  │  ◄── Are relations logical?
                    │  VALIDATION │      (Script + LLM)
                    └─────────────┘
                           │
               ┌───────────┴───────────┐
               │   COMPLETENESS        │  ◄── Is everything extracted?
               │   VALIDATION          │      (Script: count checks)
               └───────────────────────┘
                           │
          ┌────────────────┴────────────────┐
          │        SCHEMA VALIDATION        │  ◄── Is JSON valid?
          │                                 │      (Script: JSON Schema)
          └─────────────────────────────────┘
```

### 5.3 Validation Scripts

#### 5.3.1 Schema Validation

```
validate_schema.py metadata.json
  ├── Check all required fields present
  ├── Check field types correct
  ├── Check enum values valid
  └── Output: PASS/FAIL + error list
```

#### 5.3.2 Completeness Validation

```
validate_completeness.py metadata.json --spec-stats spec_stats.json
  ├── Compare: extracted register count vs expected
  ├── Compare: page coverage (% of pages with nodes)
  ├── Check: all ToC sections have corresponding nodes
  └── Output: Coverage report + missing items list
```

#### 5.3.3 Coherence Validation

```
validate_coherence.py metadata.json
  ├── Check: no orphan nodes
  ├── Check: no circular DEPENDS_ON relations
  ├── Check: CONTROLS relations make sense (register → feature)
  ├── Check: all referenced node IDs exist
  └── Output: Coherence report + warnings
```

#### 5.3.4 Semantic Validation (LLM-Assisted)

```
For each node:
  1. Retrieve source text from PDF (using bbox)
  2. Ask LLM: "Does this extracted node accurately represent the source?"
  3. Flag discrepancies for human review
```

### 5.4 Cross-Reference Validation Agent

An automated agent that:
1. Picks a random sample of nodes
2. Goes back to the PDF source location
3. Compares extracted content vs original
4. Reports discrepancies

### 5.5 Discussion Points for Phase 3

> **Q13**: What's the minimum acceptable coverage before sign-off?
> - 100% of registers?
> - 90% of spec pages?

> **Q14**: Should we implement a "confidence score" aggregated at the file level?

> **Q15**: Validation feedback loop - if validation fails, should it:
> - (a) Auto-retry extraction with different prompt
> - (b) Queue for human intervention
> - (c) Both, based on failure type

---

## 6. Phase 4: Access Script Design

### 6.1 Objective

Create `metadata_access.py` - the ONLY interface between the agent and the metadata.

### 6.2 Design Principles

1. **No Direct JSON Access**: Agent NEVER reads metadata.json directly
2. **Minimal Sufficient Primitives**: Only expose necessary operations
3. **Structured Output**: All responses are structured (not raw JSON dumps)
4. **Query Logging**: Log all queries for debugging/auditing

### 6.3 Proposed Primitives

#### 6.3.1 Node Retrieval

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `get_node(id)` | node_id | Full node object | Get any node by ID |
| `get_register(name_or_offset)` | name OR offset | Register node | Get register by name or offset |
| `get_feature(name)` | feature_name | Feature node | Get feature by name |
| `get_port(name)` | port_name | Port node | Get port by name |
| `get_state_machine(name)` | sm_name | State machine node | Get state machine |
| `get_figure(number)` | figure_number | Figure node | Get figure |
| `get_table(number)` | table_number | Table node | Get table |

#### 6.3.2 Search & Query

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `search_by_keywords(keywords, node_types=None)` | keyword list, optional type filter | List of matching nodes (summary) | Keyword search in index |
| `search_by_text(query, limit=10)` | natural language query | Ranked list of relevant nodes | Semantic search in descriptions |
| `get_nodes_of_type(type)` | node type | List of all nodes of that type | List all registers, etc. |

#### 6.3.3 Relation Queries

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `get_related_nodes(node_id, relation_type=None)` | node_id, optional relation filter | List of related nodes | Get connected nodes |
| `get_nodes_that_control(feature_id)` | feature node id | Registers that control it | Find controlling registers |
| `get_nodes_described_by(node_id)` | node_id | Spec chunks describing it | Find documentation |

#### 6.3.4 Utility

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `get_spec_info()` | - | Spec metadata | Get spec name, version, etc. |
| `get_statistics()` | - | Node counts by type | Overview of metadata |
| `get_source_location(node_id)` | node_id | Page, bbox | Where to find in PDF |

### 6.4 CLI Interface

```bash
# Examples of CLI usage
python metadata_access.py get_register "Command Register"
python metadata_access.py search_by_keywords "DMA,transfer,buffer"
python metadata_access.py get_related_nodes "REG_005" --relation-type CONTROLS
```

### 6.5 Output Format

All functions return structured output:

```json
{
  "status": "success | error",
  "query": { "function": "get_register", "params": {...} },
  "result": { ... },
  "result_count": 1,
  "execution_time_ms": 12
}
```

### 6.6 Discussion Points for Phase 4

> **Q16**: Should the script support batch queries? (get multiple registers at once)

> **Q17**: Should there be a `get_programming_sequence(feature)` primitive that returns ordered steps?

> **Q18**: For `search_by_text`, should we:
> - (a) Implement simple TF-IDF locally
> - (b) Use embedding-based search (requires vector DB)
> - (c) Pass to LLM for relevance ranking

> **Q19**: Should there be an `explain_register_field(register, field_name)` primitive?

---

## 7. Phase 5: Orchestration Agent & Prompts

### 7.1 Objective

Define the prompts and agent behavior for:
1. **Extraction Agent**: Creates metadata from PDF
2. **Query Agent**: Answers questions using metadata

### 7.2 Extraction Orchestration Prompt (Main)

```markdown
# EXTRACTION AGENT SYSTEM PROMPT

You are an IP Specification Extraction Agent. Your task is to extract structured 
information from a PDF specification and create a comprehensive metadata.json file.

## Your Tools
- `pdf_extract_text(page_range)` - Extract text from PDF pages
- `pdf_extract_table(page, table_index)` - Extract table from PDF
- `pdf_get_figure_info(page)` - Get figure metadata from page
- `validate_node(node_json)` - Validate a node against schema
- `add_node(node_json)` - Add validated node to metadata
- `add_relation(relation_json)` - Add relation between nodes
- `request_user_validation(node_id, question)` - Ask user to validate

## Process
1. Start with Phase 0: Analyze PDF structure
2. Execute Pass 1: Structural extraction
3. Execute Pass 2: Semantic extraction (with user validation checkpoints)
4. Execute Pass 3: Relations and indexing
5. Run validation checks
6. Present final report to user

## Constraints
- NEVER skip validation for REGISTER or STATE_MACHINE nodes
- ALWAYS include source page and bbox for every node
- If confidence < 0.7, MUST request user validation
- Maximum 50 nodes per validation batch

## Output
After each major step, report:
- Nodes created
- Confidence levels
- Items requiring attention
```

### 7.3 Query Agent System Prompt

```markdown
# QUERY AGENT SYSTEM PROMPT

You are an SD Host Specification Query Agent. You answer questions about the 
SD Host Controller specification based EXCLUSIVELY on the extracted metadata.

## CRITICAL CONSTRAINTS
1. You can ONLY access information through the metadata_access.py script
2. You MUST NOT make up information not present in the metadata
3. You MUST cite the source node IDs for every fact you state
4. You MAY use common knowledge for units and standard terminology
   (e.g., V = Volts, MHz = Megahertz, RW = Read-Write)

## Your Tools
- `run_command(cmd)` - Execute metadata_access.py commands
  Examples:
  - run_command("get_register 'Command Register'")
  - run_command("search_by_keywords 'DMA,transfer'")
  - run_command("get_related_nodes 'REG_005'")

## Response Format
For every answer:
1. State what you found in the metadata
2. Cite the source nodes: [Source: REG_005, SPEC_023]
3. If information is incomplete, say: "The metadata does not contain information about X"
4. NEVER say "Based on my knowledge..." - ONLY use metadata

## Example Interaction

User: "How does DMA work in this controller?"

Agent thinking:
1. Search for DMA-related nodes
2. Find feature, registers, and spec chunks
3. Synthesize answer from found nodes

Agent response:
"Based on the specification metadata:

The SD Host Controller supports ADMA2 (Advanced DMA) for data transfers. 
[Source: FEATURE_003]

DMA is controlled by:
- ADMA System Address Register (offset 0x58) - sets the descriptor table address 
  [Source: REG_022]
- Host Control 1 Register, bit 3 (DMA Select) - enables DMA mode 
  [Source: REG_010, field DMA_SEL]

The DMA transfer sequence is:
1. Set up descriptor table in system memory
2. Write table address to ADMA System Address Register
3. Enable DMA in Host Control 1
4. Issue transfer command
[Source: SPEC_045, SPEC_046]"
```

### 7.4 User Validation Prompt Template

```markdown
# VALIDATION REQUEST

I need your help validating an extracted node.

## Node Information
- **Type**: {{ node.type }}
- **ID**: {{ node.id }}
- **Name**: {{ node.name }}
- **Source**: Page {{ node.source.page }}

## Extracted Content
{{ node | format_for_display }}

## Original Text (from PDF)
```
{{ source_text }}
```

## Questions
1. Is the extraction accurate? (Yes/No/Partially)
2. If not, what should be corrected?
3. Confidence in this extraction (1-5)?

Please respond with:
- APPROVE - if extraction is correct
- EDIT - followed by corrections
- REJECT - if extraction is fundamentally wrong
```

### 7.5 Discussion Points for Phase 5

> **Q20**: Should the Query Agent have a "strict mode" where it refuses to answer if confidence is low?

> **Q21**: For the Extraction Agent, should it:
> - (a) Extract all nodes first, then validate in batch
> - (b) Extract and validate incrementally per section
> - (c) Configurable based on user preference

> **Q22**: Should there be a "learning" mechanism where user corrections improve future extractions?

---

## 8. Open Questions & Discussion Points

### 8.1 Summary of All Questions

| # | Question | Priority | Your Answer |
|---|----------|----------|-------------|
| Q1 | Do you have the PDF? Preliminary analysis done? | HIGH | |
| Q2 | Acceptable PDF parsing tools? | HIGH | |
| Q3 | How to handle images/diagrams? | HIGH | |
| Q4 | Is the schema complete for SD Host? | HIGH | |
| Q5 | Support nested register fields? | MEDIUM | |
| Q6 | Version field for spec revisions? | LOW | |
| Q7 | Coverage status options? | MEDIUM | |
| Q8 | Track optional vs mandatory features? | MEDIUM | |
| Q9 | Validation mode (all/threshold/sample)? | HIGH | |
| Q10 | Register parser approach? | HIGH | |
| Q11 | Handle spec ambiguities? | MEDIUM | |
| Q12 | Resumable extraction? | MEDIUM | |
| Q13 | Minimum coverage for sign-off? | HIGH | |
| Q14 | Aggregated confidence score? | LOW | |
| Q15 | Validation failure handling? | MEDIUM | |
| Q16 | Batch queries in access script? | LOW | |
| Q17 | `get_programming_sequence` primitive? | MEDIUM | |
| Q18 | Text search implementation? | MEDIUM | |
| Q19 | `explain_register_field` primitive? | LOW | |
| Q20 | Query agent strict mode? | MEDIUM | |
| Q21 | Extraction validation timing? | HIGH | |
| Q22 | Learning from corrections? | LOW | |

### 8.2 Next Steps After Discussion

1. [ ] Finalize answers to all questions
2. [ ] Lock schema v1.0
3. [ ] Perform PDF analysis (Phase 0)
4. [ ] Prototype register extraction on 1-2 pages
5. [ ] Iterate based on prototype results

### 8.3 Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Complex tables break extraction | HIGH | Custom parser + manual fallback |
| State diagrams only as images | MEDIUM | LLM vision + manual validation |
| Spec ambiguities cause inconsistencies | MEDIUM | Flag and document all ambiguities |
| Too many validation requests fatigue user | HIGH | Confidence thresholds, batch mode |
| Agent hallucinates despite constraints | HIGH | Strict script-only access, logging |

---

## Appendix A: Proposed File Structure

```
sdhost-3.0/
├── source/
│   └── sd_host_3_00.pdf              # Original spec
├── extraction/
│   ├── pdf_analysis_report.md        # Phase 0 output
│   ├── raw_tables/                   # Extracted table CSVs
│   ├── raw_figures/                  # Extracted figure PNGs
│   └── extraction_log.json           # Extraction history
├── metadata/
│   ├── metadata.json                 # THE metadata file
│   ├── metadata_schema.json          # JSON Schema for validation
│   └── metadata_backup/              # Version backups
├── scripts/
│   ├── metadata_access.py            # Access script
│   ├── validate_schema.py
│   ├── validate_completeness.py
│   └── validate_coherence.py
├── prompts/
│   ├── extraction_agent.md
│   ├── query_agent.md
│   └── validation_request.md
└── docs/
    ├── process.md                    # This file
    └── decision_log.md               # Track decisions made
```

---

## Appendix B: Example Nodes (Preview)

### Example REGISTER Node

```json
{
  "id": "REG_001",
  "type": "REGISTER",
  "name": "SD Command Argument Register",
  "description": "This register contains the SD command argument.",
  "index_keywords": ["command", "argument", "CMD_ARG", "SD command"],
  "source": {
    "page": 45,
    "bbox": {"x0": 50, "y0": 200, "x1": 550, "y1": 350},
    "raw_text": "..."
  },
  "coverage": {
    "status": "NOT_IMPLEMENTED",
    "notes": ""
  },
  "confidence": 0.95,
  "offset": "0x08",
  "size_bits": 32,
  "reset_value": "0x00000000",
  "access": "RW",
  "fields": [
    {
      "name": "CMD_ARG",
      "bits": "31:0",
      "access": "RW",
      "reset": "0x00000000",
      "description": "Command Argument"
    }
  ]
}
```

### Example Relation

```json
{
  "id": "REL_001",
  "type": "CONTROLS",
  "source_node": "REG_005",
  "target_node": "FEATURE_002",
  "description": "Normal Interrupt Status Register controls the Interrupt feature"
}
```

---

**Document Version**: 0.1 (Draft for Discussion)  
**Last Updated**: 2026-01-31  
**Status**: Awaiting user feedback on open questions
