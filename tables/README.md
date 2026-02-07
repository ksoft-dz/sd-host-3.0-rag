# Tables Extraction Pipeline

This folder contains tools and outputs for extracting tables from the SD Host 3.0 specification PDF.

## Quick Start

```powershell
# 1. Extract table inventory from PDF
python extract_tables_map.py

# 2. Extract table images (for manual review or LLM vision)
python extract_table_images.py

# 3. Convert tables to CSV using LLM
python convert_tables_to_csv.py --workers 4
```

## Scripts

### `extract_tables_map.py`
Scans the PDF and builds an inventory of all tables with their locations.

**Output**: `tables_page_map.json`

```powershell
python extract_tables_map.py
```

### `extract_table_images.py`
Extracts table images from PDF pages for manual review or LLM vision processing.

**Output**: `images/TABLE_X_Y.png`

```powershell
python extract_table_images.py
```

### `convert_tables_to_csv.py`
Uses Claude LLM to convert table images to structured CSV format.

**Arguments**:
- `--workers N` - Number of parallel workers (default: 4)
- `--skip-existing` - Skip tables that already have CSV files
- `--table TABLE_ID` - Process specific table only

**Output**: `csv/TABLE_X_Y.csv`

```powershell
# Process all tables with 4 workers
python convert_tables_to_csv.py --workers 4

# Skip already converted tables
python convert_tables_to_csv.py --skip-existing --workers 4

# Convert specific table
python convert_tables_to_csv.py --table TABLE_2_17
```

## Output Files

| File | Description |
|------|-------------|
| `tables_page_map.json` | Index of all 60 tables with metadata |
| `csv/TABLE_X_Y.csv` | Converted CSV files |
| `images/TABLE_X_Y.png` | Extracted table images |
| `table_conversion.log` | Conversion process log |
| `tables_to_check.md` | Tables that need manual review |

## Schema: tables_page_map.json

```json
{
  "_metadata": {
    "source_pdf": "sd_host_3_00.pdf",
    "total_tables": 60,
    "conversion_progress": {
      "completed": 50,
      "pending": 10
    }
  },
  "tables": [
    {
      "id": "TABLE_2_17",
      "spec_reference": "Table 2-17",
      "title": "Power Control Register",
      "spec_page": 53,
      "definition_page": 64,
      "csv_file": "csv/TABLE_2_17.csv",
      "conversion_status": "COMPLETED"
    }
  ]
}
```

## Notes

- Page offset: `pdf_page = spec_page + 11`
- Tables are numbered as `TABLE_X_Y` where X is section, Y is sequence
- Some tables span multiple pages - check `tables_to_check.md` for these cases
