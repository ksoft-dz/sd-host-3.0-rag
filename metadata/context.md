# Metadata Generation Context

## Overview

The `metadata.json` file is the unified knowledge graph for the SD Host Controller 3.0 RAG system. It consolidates all extracted artifacts (tables, figures, spec chunks, registers) into a single queryable structure with typed nodes and relations.

## Generation Script

**Script**: `scripts/merge_metadata.py`

**Command**:
```powershell
python scripts/merge_metadata.py          # Generate metadata.json
python scripts/merge_metadata.py --dry-run # Preview without writing
python scripts/merge_metadata.py --validate-only # Validate existing
```

## Input Sources

| Source File | Description |
|-------------|-------------|
| `tables/tables_page_map.json` | Table definitions with CSV references |
| `figures/figures_page_map.json` | Figure definitions with PlantUML references |
| `spec/sections.json` | Specification chunks with hierarchies |
| `registers/registers.json` | Register definitions with LLM-extracted fields |

## Output Structure

```json
{
  "metadata_version": "1.0.0",
  "spec_info": { ... },
  "extraction_info": {
    "extracted_date": "ISO-8601",
    "sources": { /* paths to all input files */ },
    "statistics": { /* node/relation counts */ }
  },
  "nodes": [ /* array of typed nodes */ ],
  "relations": [ /* array of typed relations */ ]
}
```

## Node Types

### TABLE
Tables extracted from the PDF specification.

| Field | Description |
|-------|-------------|
| `id` | TABLE_X_Y format (chapter_sequence) |
| `type` | "TABLE" |
| `name` | Table title from spec |
| `description` | Table abstract |
| `source.page` | Spec page number |
| `source.pdf_page` | Physical PDF page (spec_page + 11) |
| `extras.table_type` | REGISTER_FIELDS, REGISTER_MAP, SIGNAL_LIST, etc. |
| `extras.csv_file` | Path to CSV export |

### FIGURE
Figures extracted from the PDF specification.

| Field | Description |
|-------|-------------|
| `id` | FIG_X_Y format |
| `type` | "FIGURE" |
| `name` | Figure title |
| `description` | Figure abstract |
| `source.page` | Spec page number |
| `extras.figure_type` | STATE_DIAGRAM, TIMING_DIAGRAM, BLOCK_DIAGRAM, etc. |
| `extras.text_diagram_file` | Path to PlantUML file |

### SPEC_CHUNK
Text chunks from specification sections.

| Field | Description |
|-------|-------------|
| `id` | CHUNK_X_Y_Z format (section_chunkindex) |
| `type` | "SPEC_CHUNK" |
| `name` | Section title + chunk index |
| `description` | Chunk abstract |
| `extras.section_number` | Section identifier (e.g., "2.2.1") |
| `extras.full_text` | Complete raw text |
| `extras.word_count` | Token count for chunking |

### REGISTER
Hardware registers with field-level detail.

| Field | Description |
|-------|-------------|
| `id` | REG_XXX format (hex offset) |
| `type` | "REGISTER" |
| `name` | Register name |
| `offset` | Hex offset (e.g., "024h") |
| `extras.spec_section` | Section number where documented |
| `extras.spec_table` | Primary definition table |
| `extras.class_id` | Reference to REG_CLASS |
| `extras.fields` | Array of field definitions |

#### Field Structure
Each register field contains:
- `id`: REG_XXX_FN format
- `name`: Field name
- `bits`: Bit range string (e.g., "7-4")
- `bit_high`, `bit_low`: Numeric bounds
- `width`: Bit count
- `access`: Normalized (read-write, read-only, write-only, reserved)
- `read_effect`: none, clear, undefined
- `write_effect`: none, write-1-clear, auto-clear, ignored, set-by-hardware
- `original_attrib`: Original access string from table
- `raw`: Complete raw text from CSV
- `abstract`: LLM-condensed description
- `values`: Array of {code, meaning} pairs

### REG_CLASS
Register classification groups (functional areas).

| Field | Description |
|-------|-------------|
| `id` | REGCLASS_NAME format |
| `type` | "REG_CLASS" |
| `name` | Class name |
| `address_range.start/end` | Offset range |
| `version_support` | 1.00/2.00/3.00 support status |
| `source.table` | TABLE_1_1 reference |

## Relation Types

| Type | Source → Target | Description |
|------|-----------------|-------------|
| `REFERENCES` | SPEC_CHUNK → TABLE/FIGURE | Chunk mentions table/figure |
| `CHILD_OF` | SPEC_CHUNK → SPEC_CHUNK | Section hierarchy |
| `DEFINED_BY` | REGISTER → TABLE | Register fields from table |
| `VISUALIZED_BY` | REGISTER → FIGURE | Register layout in figure |
| `DESCRIBES` | TABLE/SPEC_CHUNK → REGISTER | Resource documents register |
| `BELONGS_TO` | REGISTER → REG_CLASS | Register in functional class |
| `DEFINED_IN` | REGISTER → TABLE | Register defined in table |

## PAGE_OFFSET Constant

```python
PAGE_OFFSET = 11  # PDF page = spec_page + 11
```

The specification uses a different page numbering than the physical PDF:
- Spec page 1 = PDF page 12
- Used consistently across all node generation

## Validation Checks

The merge script validates:
1. **Orphan nodes**: Nodes not referenced by any relation
2. **Dangling relations**: Relations pointing to non-existent nodes
3. **Node completeness**: Required fields present
4. **Keyword coverage**: Index keywords populated

## Backup Policy

Before each merge:
1. Existing `metadata.json` backed up to `metadata/backups/`
2. Backup filename includes ISO timestamp
3. No automatic cleanup - manual management required

## Usage by RAG Agent

The RAG agent uses `metadata_access.py` to query this file:
- Keyword search across nodes
- Node type filtering
- Relation traversal
- Coverage tracking for implementation

**IMPORTANT**: Agents should NEVER directly read `metadata.json`. Always use the metadata access layer.

## Regeneration

To regenerate metadata after extraction updates:

```powershell
# Ensure all sources are up to date
python registers/extract_registers.py  # If register tables changed
python scripts/merge_metadata.py       # Rebuild unified graph
```

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | Initial | Tables, figures, spec chunks, basic registers |
| 1.1.0 | Current | Full register extraction with LLM-processed fields |
