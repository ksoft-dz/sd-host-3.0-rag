# RAG Knowledge Base Guide

> **Purpose**: This guide explains how the RAG (Retrieval Augmented Generation) system organizes extracted data from technical PDF specifications.

---

## Quick Overview

```
PDF Document
    ↓
┌─────────────────────────────────────────────────────────┐
│  EXTRACTION PHASE                                       │
├─────────────────────────────────────────────────────────┤
│  tables/tables_page_map.json    → 60 tables extracted   │
│  figures/figures_page_map.json  → 83 figures extracted  │
│  spec/sections.json             → 112 sections, 287 chunks │
│  registers/registers.json       → 32 registers, 249 fields │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│  MERGE PHASE                                            │
├─────────────────────────────────────────────────────────┤
│  scripts/merge_metadata.py      → Combines all sources  │
│  metadata/metadata.json         → Unified graph output  │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│  QUERY PHASE                                            │
├─────────────────────────────────────────────────────────┤
│  metadata/metadata_api.py       → LLM-friendly API      │
└─────────────────────────────────────────────────────────┘
```

---

## 1. Source JSON Formats

### 1.1 Tables (`tables/tables_page_map.json`)

Tracks tables extracted from the PDF. Each table may be converted to CSV.

```json
{
  "_metadata": {
    "source_pdf": "sd_host_3_00.pdf",
    "total_tables": 60,
    "page_offset": 11,
    "conversion_progress": {
      "not_started": 0,
      "completed": 60,
      "failed": 0
    }
  },
  "tables": [
    {
      "id": "TABLE_1_1",
      "spec_reference": "Table 1-1",
      "title": "Supported Registers",
      "spec_page": 2,
      "definition_page": 13,
      "referenced_on_pages": [13],
      "abstract": "Short AI-generated summary...",
      "conversion": {
        "status": "COMPLETED",
        "file_format": "CSV",
        "file_name": "TABLE_1_1.csv",
        "validated": true
      }
    }
  ]
}
```

**Key fields**:
- `id`: Unique identifier (TABLE_X_Y pattern)
- `spec_page`: Page number in specification (excluding ToC)
- `definition_page`: Actual PDF page number
- `abstract`: LLM-generated summary for embedding
- `conversion.status`: COMPLETED | IN_PROGRESS | NOT_STARTED | FAILED

---

### 1.2 Figures (`figures/figures_page_map.json`)

Tracks figures/diagrams. May include PlantUML transcriptions.

```json
{
  "_metadata": {
    "source_pdf": "sd_host_3_00.pdf",
    "total_figures": 83,
    "page_offset": 11
  },
  "figures": [
    {
      "id": "FIG_1_1",
      "spec_reference": "Figure 1-1",
      "title": "Host Hardware and Driver Architecture",
      "spec_page": 1,
      "definition_page": 12,
      "referenced_on_pages": [12],
      "abstract": "Layered architecture: applications, card drivers...",
      "transcription": {
        "status": "COMPLETED",
        "text_file": "plantuml/FIG_1_1.puml",
        "format": "plantuml"
      }
    }
  ]
}
```

**Key fields**:
- `id`: Unique identifier (FIG_X_Y pattern)
- `transcription.status`: Status of diagram-to-code conversion
- `transcription.format`: plantuml | mermaid | text

---

### 1.3 Sections (`spec/sections.json`)

The document structure with text chunks for embedding.

```json
{
  "_metadata": {
    "total_sections": 112,
    "total_chunks": 287,
    "chunk_target_words": 200,
    "chunk_max_words": 250
  },
  "sections": {
    "1": {
      "id": "SEC_1",
      "section_number": "1",
      "title": "Overview of the SD Standard Host",
      "level": 1,
      "hierarchy": {
        "parent": null,
        "children": ["SEC_1_1", "SEC_1_2", "..."]
      },
      "source": {
        "spec_page_start": 1,
        "spec_page_end": 1,
        "pdf_page_start": 12,
        "pdf_page_end": 12
      },
      "references": {
        "tables": [],
        "figures": ["FIG_1_1"]
      },
      "chunks": [
        {
          "id": "SEC_1_C1",
          "chunk_index": 0,
          "text": "Raw text content...",
          "abstract": "AI-generated summary...",
          "word_count": 187,
          "embedding_ready": true
        }
      ]
    }
  }
}
```

**Key fields**:
- `hierarchy`: Parent/children for navigation
- `references`: Cross-references to tables/figures
- `chunks[].text`: Raw text for embedding
- `chunks[].abstract`: Summary for retrieval

---

### 1.4 Registers (`registers/registers.json`)

Hardware register definitions with bit-field details (domain-specific).

```json
{
  "_metadata": {
    "total_reg_classes": 12,
    "total_registers": 32,
    "total_fields": 249
  },
  "reg_classes": [
    {
      "id": "REGCLASS_CMD_GEN",
      "type": "REG_CLASS",
      "name": "SD Command Generation",
      "address_range": { "start": "000h", "end": "00Fh" }
    }
  ],
  "registers": [
    {
      "id": "REG_004",
      "type": "REGISTER",
      "name": "Block Size Register",
      "offset": "004h",
      "spec_section": "2.2.2",
      "spec_table": "TABLE_2_4",
      "class_id": "REGCLASS_CMD_GEN",
      "fields": [
        {
          "id": "REG_004_F0",
          "name": "Transfer Block Size",
          "bits": "11-00",
          "bit_high": 11,
          "bit_low": 0,
          "width": 12,
          "access": "read-write",
          "abstract": "Specifies block size for transfers...",
          "values": [
            { "code": "0x200", "meaning": "512 Bytes" }
          ]
        }
      ]
    }
  ]
}
```

**Key fields**:
- `offset`: Memory address offset (hex)
- `fields[].bits`: Bit range string (e.g., "11-00")
- `fields[].access`: read-only | read-write | write-only | write-1-to-clear
- `fields[].values`: Enumerated values and meanings

---

## 2. Unified Metadata (`metadata/metadata.json`)

The merge script combines all sources into a **graph structure** with nodes and relations.

### 2.1 Node Types

| Type | Source | Example ID |
|------|--------|------------|
| `TABLE` | tables_page_map.json | TABLE_1_1 |
| `FIGURE` | figures_page_map.json | FIG_1_1 |
| `SPEC_CHUNK` | sections.json | SEC_1_C1 |
| `REGISTER` | registers.json | REG_004 |
| `REG_CLASS` | registers.json | REGCLASS_CMD_GEN |

### 2.2 Node Structure

```json
{
  "id": "TABLE_1_1",
  "type": "TABLE",
  "name": "Supported Registers",
  "description": "AI-generated abstract...",
  "index_keywords": ["register", "support", "version"],
  "source": {
    "page": 2,
    "pdf_page": 13,
    "spec_reference": "Table 1-1"
  },
  "coverage": {
    "status": "NOT_IMPLEMENTED",
    "notes": "",
    "implemented_in": ""
  },
  "confidence": 0.95,
  "extras": {
    "csv_file": "tables/csv/TABLE_1_1.csv"
  }
}
```

### 2.3 Relation Types

| Relation | Description | Example |
|----------|-------------|---------|
| `REFERENCES` | Node A references Node B | SEC_1 → FIG_1_1 |
| `CONTAINS` | Parent contains child | SEC_1 → SEC_1_1 |
| `DESCRIBES` | Section describes register | SEC_2_2 → REG_004 |
| `VISUALIZED_BY` | Register shown in figure | REG_004 → FIG_2_1 |
| `DEFINED_BY` | Field defined in table | REG_004_F0 → TABLE_2_4 |
| `SEQUENCE_NEXT` | Chunk ordering | SEC_1_C1 → SEC_1_C2 |
| `CHILD_OF` | Hierarchy | SEC_1_1 → SEC_1 |

### 2.4 Relation Structure

```json
{
  "id": "REL_0001",
  "type": "REFERENCES",
  "source_node": "SEC_1",
  "target_node": "FIG_1_1",
  "description": "Section 1 references Figure 1-1",
  "bidirectional": false
}
```

---

## 3. Merge Process

```
┌─────────────────┐
│ tables_page_map │──→ TABLE nodes
└─────────────────┘
         ↘
┌─────────────────┐    ┌──────────────┐
│figures_page_map │──→ │  MERGE       │──→ metadata.json
└─────────────────┘    │  + Create    │    (nodes + relations)
         ↗            │    relations │
┌─────────────────┐    └──────────────┘
│  sections.json  │──→ SPEC_CHUNK nodes + hierarchy relations
└─────────────────┘
         ↗
┌─────────────────┐
│ registers.json  │──→ REGISTER + REG_CLASS nodes
└─────────────────┘
```

**Merge steps**:
1. Load all 4 source JSON files
2. Create nodes from each source (normalize structure)
3. Auto-detect cross-references in text (regex patterns)
4. Build relation graph
5. Add keywords for search indexing
6. Write unified metadata.json

---

## 4. Metadata API

The `metadata_api.py` provides LLM-friendly query functions:

```python
# Get register by memory offset
api.get_register_by_offset("028h")

# Search by keyword
api.search_nodes("interrupt status")

# Get all chunks for a section
api.get_section_chunks("SEC_2_2")

# Find what references a figure
api.get_chunks_referencing("FIG_2_1")

# Navigate register hierarchy
api.get_register_fields("REG_028")
```

**Response format** (consistent for all calls):
```json
{
  "success": true,
  "function": "get_register_by_offset",
  "params": { "offset": "028h" },
  "count": 1,
  "results": [...],
  "error": null
}
```

---

## 5. File Locations Summary

```
project/
├── tables/
│   ├── tables_page_map.json     # Table extraction metadata
│   └── csv/                     # Converted CSV files
│       └── TABLE_1_1.csv
├── figures/
│   ├── figures_page_map.json    # Figure extraction metadata
│   └── plantuml/                # PlantUML transcriptions
│       └── FIG_1_1.puml
├── spec/
│   └── sections.json            # Document structure + chunks
├── registers/
│   └── registers.json           # Register definitions (domain-specific)
├── metadata/
│   ├── metadata.json            # UNIFIED GRAPH (main output)
│   └── metadata_api.py          # Query API for LLM agents
└── scripts/
    └── merge_metadata.py        # Merge script
```

---

## 6. ID Naming Conventions

| Entity | Pattern | Example |
|--------|---------|---------|
| Table | `TABLE_{chapter}_{number}` | TABLE_1_1 |
| Figure | `FIG_{chapter}_{number}` | FIG_2_10 |
| Section | `SEC_{number}` | SEC_1_2_3 |
| Chunk | `SEC_{section}_C{index}` | SEC_1_C1 |
| Register | `REG_{offset}` | REG_028 |
| Field | `REG_{offset}_F{index}` | REG_028_F0 |
| Register Class | `REGCLASS_{name}` | REGCLASS_INTERRUPT |
| Relation | `REL_{index:04d}` | REL_0001 |

---

## 7. Coverage Tracking

Each node has a `coverage` field for implementation tracking:

```json
"coverage": {
  "status": "NOT_IMPLEMENTED",  // PARTIAL | IMPLEMENTED | NOT_APPLICABLE
  "notes": "Needs testing",
  "implemented_in": "src/interrupt.c"
}
```

This allows tracking which spec items have been implemented in code.
