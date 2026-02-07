# Spec Sections Directory - Context & Schema Documentation

**Purpose**: Contains extracted and chunked sections from the SD Host 3.0 specification PDF, organized as a hierarchical tree structure.

---

## 📁 Directory Structure

```
spec/
├── sections.json              # Master index with all sections & chunks
├── toc_raw.json               # Raw ToC extraction (intermediate)
├── extract_sections.py        # Main extraction script
└── context.md                 # This file
```

---

## 🛠️ Extraction Script: extract_sections.py

### Usage

```bash
# Full extraction (ToC + chunks + abstracts)
python spec/extract_sections.py

# Extract only ToC structure (no LLM calls for chunks)
python spec/extract_sections.py --toc-only

# Process specific page range
python spec/extract_sections.py --start-page 12 --end-page 50

# Skip ToC extraction, use existing toc_raw.json
python spec/extract_sections.py --skip-toc

# Dry run (no LLM calls)
python spec/extract_sections.py --dry-run
```

### Requirements

- Python 3.8+
- `pip install anthropic pymupdf`
- `ANTHROPIC_API_KEY` environment variable (or in `.env` file)

### Process Flow

```
1. Load resource maps (tables_page_map.json, figures_page_map.json)
2. Extract ToC/section structure from PDF
   └─► toc_raw.json (intermediate)
3. Process pages sequentially:
   ├─► Extract text from page
   ├─► Detect section headers
   ├─► Get tables/figures on page (to exclude)
   ├─► Call LLM for chunk extraction
   ├─► Validate JSON response (retry if invalid)
   └─► Store chunks by section
4. Generate abstracts per chunk (LLM)
5. Generate keywords per section (LLM)
6. Build final sections.json with:
   - Hierarchy (parent/children)
   - Page ranges
   - Table/figure references
   - Chunks with abstracts
```

### LLM Prompts

The script uses structured prompts that:
- Provide page context (spec page, PDF page)
- List detected section headers
- List tables/figures to EXCLUDE
- Request strict JSON output format
- Include previous page context for continuation handling
- Validate output and retry with feedback if malformed

---

## 📋 sections.json - CRITICAL SCHEMA

This is the **primary index** for all spec sections. It stores:
- Hierarchical tree of sections (parent/children links)
- Chunked content directly embedded (no separate MD files)
- Abstracts and keywords (Haiku/Sonnet generated)
- References to tables/figures/related sections

### JSON Schema

```json
{
  "_metadata": {
    "source_pdf": "string",              // Source PDF filename
    "extraction_date": "string",         // YYYY-MM-DD
    "total_sections": "integer",         // Total section count
    "total_chunks": "integer",           // Total chunk count across all sections
    "toc_source": "string",              // "extracted_from_text" | "pdf_toc"
    "page_offset": "integer",            // PDF page offset
    "chunk_target_words": "integer",     // Target words per chunk (default: 200)
    "abstract_generator": "string",      // "haiku" | "sonnet"
    "validation_attempts": "integer"     // Max validation attempts (default: 2)
  },

  "sections": {
    "<section_number>": {                // Key: "1", "2.1", "2.1.3" etc.
      "id": "string",                    // SEC_X_Y_Z format
      "section_number": "string",        // Same as key: "2.1.3"
      "title": "string",                 // Section title
      "level": "integer",                // Depth: 1, 2, 3, etc.

      "hierarchy": {
        "parent": "string | null",       // Parent section ID (null for root)
        "children": ["string"]           // Array of child section IDs (empty for leaves)
      },

      "source": {
        "spec_page_start": "integer",    // Start page in spec
        "spec_page_end": "integer",      // End page in spec
        "pdf_page_start": "integer",     // Start page in actual PDF
        "pdf_page_end": "integer"        // End page in actual PDF
      },

      "references": {
        "tables": ["string"],            // TABLE_X_Y IDs
        "figures": ["string"],           // FIG_X_Y IDs
        "related": ["string"]            // Other SEC_X_Y IDs (from "See Section X.Y")
      },

      "index": {
        "keywords": ["string"],          // Haiku/Sonnet generated searchable terms
        "technical_terms": ["string"]    // Register names, offsets, acronyms
      },

      "abstract": "string",              // Section-level summary (Haiku generated)
      "word_count": "integer",           // Total words in section

      "chunks": [                        // Array of content chunks
        {
          "chunk_id": "string",          // SEC_X_Y_Z_C0, SEC_X_Y_Z_C1, etc.
          "chunk_index": "integer",      // 0, 1, 2, ... (order within section)
          "abstract": "string",          // Chunk-level summary (Haiku generated)
          "raw": "string"                // Actual spec text (≤200 words target)
        }
      ],

      "extraction": {
        "status": "string",              // NOT_STARTED | IN_PROGRESS | COMPLETED | FAILED
        "confidence": "float",           // 0.0 - 1.0
        "validated": "boolean"           // User validation status
      }
    }
  }
}
```

---

## 🌳 Hierarchy Structure

### Root Sections
Root sections (1, 2, 3, etc.) act as containers but still have full node structure:

```json
"1": {
  "id": "SEC_1",
  "section_number": "1",
  "title": "Introduction",
  "level": 1,
  "hierarchy": {
    "parent": null,
    "children": ["SEC_1_1", "SEC_1_2", "SEC_1_3"]
  },
  "chunks": [],          // May be empty for container sections
  "word_count": 0
}
```

### Leaf Sections
Leaf sections have no children and contain the actual content:

```json
"2.1.3": {
  "id": "SEC_2_1_3",
  "section_number": "2.1.3",
  "title": "Power Control Register",
  "level": 3,
  "hierarchy": {
    "parent": "SEC_2_1",
    "children": []        // Empty = leaf section
  },
  "chunks": [...]         // Contains actual content chunks
}
```

### Intermediate Sections
May have both their own intro content AND children:

```json
"2.1": {
  "id": "SEC_2_1",
  "section_number": "2.1",
  "title": "Register Definitions",
  "level": 2,
  "hierarchy": {
    "parent": "SEC_2",
    "children": ["SEC_2_1_1", "SEC_2_1_2", "SEC_2_1_3"]
  },
  "chunks": [             // Intro content BEFORE first subsection
    {
      "chunk_id": "SEC_2_1_C0",
      "abstract": "Overview of register organization.",
      "raw": "This section defines the registers..."
    }
  ]
}
```

---

## 📦 Chunking Strategy

### Rules

| Rule | Description |
|------|-------------|
| **Target size** | ~200 words per chunk |
| **Paragraph integrity** | Never split mid-paragraph |
| **Split points** | Prefer paragraph boundaries, blank lines |
| **Single chunks** | Still use array format for consistency |
| **Chunk ID format** | `{section_id}_C{index}` (e.g., `SEC_2_1_3_C0`) |

### Splitting Algorithm

1. Extract raw text for section
2. Split into paragraphs (by double newline or blank line)
3. Accumulate paragraphs until ~200 words
4. Create chunk, start new accumulation
5. Last chunk may be smaller (don't pad)

### Example

Section with 450 words → 2-3 chunks:
```json
"chunks": [
  { "chunk_id": "SEC_2_1_3_C0", "chunk_index": 0, "abstract": "...", "raw": "..." },  // ~200 words
  { "chunk_id": "SEC_2_1_3_C1", "chunk_index": 1, "abstract": "...", "raw": "..." },  // ~200 words
  { "chunk_id": "SEC_2_1_3_C2", "chunk_index": 2, "abstract": "...", "raw": "..." }   // ~50 words
]
```

---

## 🔗 References & Cross-Links

### Table/Figure References
When section contains or references tables/figures:

```json
"references": {
  "tables": ["TABLE_2_17", "TABLE_2_18"],
  "figures": ["FIG_2_15"],
  "related": []
}
```

### Cross-Section References
When text contains "See Section X.Y" or similar:

```json
"references": {
  "tables": [],
  "figures": [],
  "related": ["SEC_3_2_4", "SEC_2_1_1"]  // Detected cross-references
}
```

**Detection patterns**:
- "See Section X.Y"
- "Refer to Section X.Y"
- "described in Section X.Y"
- "Section X.Y defines..."

---

## 🏷️ Keywords & Index

### Generation
Both `keywords` and `technical_terms` are **Haiku/Sonnet generated**:

```json
"index": {
  "keywords": ["power", "voltage", "bus power", "supply", "enable"],
  "technical_terms": ["SD Bus Voltage Select", "offset 029h", "RW", "Rsvd", "3.3V", "1.8V"]
}
```

### Distinction

| Field | Content | Example |
|-------|---------|---------|
| `keywords` | General searchable terms | "power", "voltage", "control" |
| `technical_terms` | Spec-specific terms, offsets, acronyms | "offset 029h", "RW", "ADMA2" |

---

## 🔄 Extraction Workflow

```
1. Extract ToC from PDF
   └─► toc_raw.json (intermediate)

2. Build section tree structure
   └─► sections.json with hierarchy, empty chunks

3. For each section (depth-first):
   ├─► Extract raw text from PDF pages
   ├─► Split into chunks (~200 words, paragraph boundaries)
   ├─► Generate abstract per chunk (Haiku)
   ├─► Generate section-level abstract (Haiku)
   ├─► Generate keywords & technical_terms (Haiku)
   ├─► Detect table/figure/section references
   └─► Validate abstracts (Haiku, 2 attempts max)

4. Update extraction status
```

---

## 🎯 Integration with Metadata Pipeline

When building final `metadata.json`:

1. **Load sections.json** as the section/chunk inventory
2. **For each section with chunks**:
   - Create SPEC_CHUNK nodes from chunks
   - Link to referenced tables/figures
   - Build SEQUENCE_NEXT relations for procedures
   - Create parent/child relations

3. **Merge with other resources**:
   - `tables/tables_page_map.json` → TABLE nodes
   - `figures/figures_page_map.json` → FIGURE nodes
   - `spec/sections.json` → SPEC_CHUNK nodes

4. **Relation types**:
   - Section → Table: `REFERENCES`
   - Section → Figure: `REFERENCES`
   - Section → Section: `REFERENCES` (cross-refs)
   - Parent → Child: `CONTAINS`

---

## 🔍 Quick Reference

| Resource | Purpose |
|----------|---------|
| `sections.json` | Master index - START HERE |
| `toc_raw.json` | Raw ToC (intermediate, optional) |
| `_metadata.total_chunks` | Total chunks for RAG indexing |
| `section.hierarchy` | Navigate tree structure |
| `section.chunks[].raw` | Actual spec text for RAG |
| `section.chunks[].abstract` | Quick context without full text |

---

## ⚠️ Important Notes

1. **Keys vs IDs**: Dictionary keys use `"2.1.3"` format, `id` field uses `"SEC_2_1_3"` format
2. **Page Numbers**: Use `page_offset` to convert between spec pages and PDF pages
3. **Empty Sections**: Root/container sections may have empty `chunks` array
4. **Validation**: Abstracts validated via Haiku (2 attempts max)
5. **No MD Files**: All content embedded directly in `sections.json`
6. **Paragraph Integrity**: Chunks never split mid-paragraph

---

## 📖 Usage Example

```python
import json

# Load sections
with open('spec/sections.json') as f:
    data = json.load(f)

# Get a specific section
section = data['sections']['2.1.3']
print(f"Title: {section['title']}")
print(f"Abstract: {section['abstract']}")
print(f"Chunks: {len(section['chunks'])}")

# Navigate hierarchy
parent_id = section['hierarchy']['parent']  # "SEC_2_1"
parent_key = parent_id.replace('SEC_', '').replace('_', '.')  # "2.1"
parent = data['sections'][parent_key]

# Get all chunks for RAG
all_chunks = []
for sec_key, sec in data['sections'].items():
    for chunk in sec['chunks']:
        all_chunks.append({
            'id': chunk['chunk_id'],
            'section': sec_key,
            'title': sec['title'],
            'abstract': chunk['abstract'],
            'text': chunk['raw'],
            'tables': sec['references']['tables'],
            'figures': sec['references']['figures']
        })
```

---

**For metadata extraction agents**: Read this file first to understand the section/chunk schema. Use `sections.json` as the authoritative source for all spec text content.

**Critical for RAG**: The `chunks[].raw` field contains the actual retrievable text. Use `chunks[].abstract` for quick context. Use `index.keywords` and `index.technical_terms` for search optimization.
