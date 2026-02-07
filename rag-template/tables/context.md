# Tables Extraction Context

## Purpose
This folder contains extracted tables from the source PDF specification.

## Files
- `tables_page_map.json` - Metadata about all tables (location, status, references)
- `csv/` - Converted tables in CSV format

## JSON Structure

### Table Entry
```json
{
  "id": "TABLE_1_1",
  "spec_reference": "Table 1-1",
  "title": "Human-readable title",
  "spec_page": 2,
  "definition_page": 13,
  "referenced_on_pages": [13, 45],
  "abstract": "LLM-generated summary for embeddings",
  "conversion": {
    "status": "COMPLETED",
    "file_format": "CSV",
    "file_name": "TABLE_1_1.csv"
  }
}
```

### Multi-Page Tables
Tables can span multiple pages. Use these fields:
- `spec_page`: First page where table appears
- `spec_page_end`: Last page (if multi-page)
- `definition_page`: First PDF page
- `definition_page_end`: Last PDF page (if multi-page)

```json
{
  "id": "TABLE_2_5",
  "spec_page": 10,
  "spec_page_end": 12,
  "definition_page": 21,
  "definition_page_end": 23
}
```

### Status Values
- `NOT_STARTED` - Table identified but not converted
- `IN_PROGRESS` - Conversion underway
- `COMPLETED` - Successfully converted to CSV
- `INCOMPLETE` - Partial conversion (manual review needed)
- `FAILED` - Conversion failed (see validation_notes)

## Workflow
1. Extract table locations from PDF (manually or via OCR)
2. Populate tables_page_map.json with metadata
3. Convert each table to CSV using LLM
4. Validate converted CSV matches source
5. Generate abstracts for embedding

## CSV Naming Convention
- `TABLE_{chapter}_{number}.csv`
- Example: `TABLE_1_1.csv`, `TABLE_2_10.csv`
