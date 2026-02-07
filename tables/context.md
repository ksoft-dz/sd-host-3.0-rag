# Tables Directory - Context & Schema Documentation

**Purpose**: Contains extracted and converted tables from the SD Host 3.0 specification PDF.

---

## 📁 Directory Structure

```
tables/
├── tables_page_map.json       # Master index of all 60 tables
├── csv/                       # Converted CSV files
│   ├── TABLE_1_1.csv
│   ├── TABLE_1_2.csv
│   └── ... (60 tables)
├── images/                    # Original table images/extractions
└── context.md                 # This file
```

---

## 📋 tables_page_map.json - CRITICAL SCHEMA

This is the **primary index** for all tables in the specification. Use this to:
- Find tables by ID, title, or page number
- Track conversion status
- Access converted CSV files
- Build metadata nodes

### JSON Schema

```json
{
  "_metadata": {
    "source_pdf": "string",              // Source PDF filename
    "total_pages": "integer",            // Total pages in PDF
    "extraction_date": "string",         // YYYY-MM-DD
    "total_tables": "integer",           // Total number of tables
    "page_offset": "integer",            // PDF page offset (spec_page + offset = PDF page)
    "page_offset_note": "string",        // Explanation of offset
    "conversion_progress": {
      "not_started": "integer",          // Count of unconverted tables
      "in_progress": "integer",          // Count being converted
      "completed": "integer",            // Count successfully converted
      "incomplete": "integer",           // Count partially converted
      "failed": "integer"                // Count failed conversions
    }
  },
  "tables": [
    {
      "id": "string",                    // TABLE_X_Y format (e.g., "TABLE_1_1")
      "spec_reference": "string",        // As appears in spec (e.g., "Table 1-1")
      "title": "string",                 // Table title/description
      "spec_page": "integer",            // Page in spec (not PDF)
      "definition_page": "integer",      // Actual PDF page number
      "referenced_on_pages": ["int"],    // All pages referencing this table
      "reference_count": "integer",      // How many times referenced
      "columns": ["string"],             // Column headers (after extraction)
      "nb_lines": "integer",             // Number of rows
      "nb_columns": "integer",           // Number of columns
      "content": {},                     // Raw structured content
      "raw_content": "string",           // Raw text extraction
      "abstract": "string",              // Brief description of table content
      "conversion": {
        "status": "string",              // NOT_STARTED | IN_PROGRESS | COMPLETED | INCOMPLETE | FAILED
        "file_format": "string",         // csv | json | etc.
        "file_name": "string",           // Filename in csv/ (e.g., "TABLE_1_1.csv")
        "validated": "boolean",          // User validation status
        "validation_notes": "string"     // Any validation comments
      }
    }
  ]
}
```

---

## 📊 CSV Files (tables/csv/)

Converted tables in CSV format for easy parsing. Each CSV file:
- Named using table ID: `TABLE_X_Y.csv`
- First row contains column headers
- Preserves table structure as much as possible
- May contain multi-line cells (quoted)

### Usage

```python
import json
import csv

# Load the master index
with open('tables/tables_page_map.json') as f:
    tables_data = json.load(f)

# Find a specific table
table = next(t for t in tables_data['tables'] if t['id'] == 'TABLE_1_1')

# Check if converted
if table['conversion']['status'] == 'COMPLETED':
    csv_file = f"tables/csv/{table['conversion']['file_name']}"
    with open(csv_file) as f:
        reader = csv.DictReader(f)
        for row in reader:
            print(row)
```

---

## 🎯 Integration with Metadata Pipeline

When building `metadata.json`:

1. **Load tables_page_map.json** to get complete table inventory
2. **For each table**:
   - Create a TABLE node in metadata
   - Link to CSV file in `csv/` directory
   - Extract column schema from CSV headers
   - Link table to related nodes (registers, features, etc.)

3. **Special table types**:
   - **REGISTER_MAP**: Contains register addresses → Link to REGISTER nodes
   - **REGISTER_FIELDS**: Contains field definitions → Part of REGISTER nodes
   - **SIGNAL_LIST**: Port/signal definitions → Create PORT nodes
   - **TIMING**: Timing specifications → Link to relevant nodes

4. **Relation creation**:
   - SPEC_CHUNK → TABLE (when text references "See Table X-Y")
   - REGISTER → TABLE (register definition table)
   - FEATURE → TABLE (feature description table)

---

## 🔍 Quick Reference

| Resource | Purpose |
|----------|---------|
| `tables_page_map.json` | Master index - START HERE |
| `csv/*.csv` | Converted tabular data |
| `images/` | Original extractions (if needed) |
| `_metadata.conversion_progress` | Track conversion status |
| `table[].conversion.status` | Check if table is ready to use |

---

## ⚠️ Important Notes

1. **Page Numbers**: Use `page_offset` to convert between spec pages and PDF pages
2. **IDs**: Table IDs use underscore format: `TABLE_1_1` (not `TABLE_1-1`)
3. **Validation**: Always check `conversion.validated` before using in production
4. **Multi-page Tables**: Some tables span pages - check `referenced_on_pages`
5. **Status Tracking**: Use `conversion.status` to filter usable tables

---

**For metadata extraction agents**: Read this file first to understand the table resources schema. Use `tables_page_map.json` as the authoritative source for all table metadata.
