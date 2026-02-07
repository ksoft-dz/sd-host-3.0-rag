# Registers Extraction

Extracts comprehensive register information from the SD Host Controller 3.0 specification CSV tables.

## Features

- **REG_CLASS nodes**: 12 register class groupings with address ranges and version support
- **REGISTER nodes**: Full register definitions with offset, section, and table references
- **Field extraction**: Every field processed by LLM for structured output
- **Values extraction**: Enumerated values (e.g., `1 = Power on`, `111b = 3.3V`)
- **Abstracts**: Concise summaries for each field (max 120 chars)

## Prerequisites

```bash
pip install anthropic
```

Set your API key:
```bash
# Windows
set ANTHROPIC_API_KEY=your-key-here

# Linux/Mac
export ANTHROPIC_API_KEY=your-key-here
```

## Usage

### Full extraction (all register tables)
```bash
python registers/extract_registers.py
```

### Parallel extraction with workers
```bash
python registers/extract_registers.py --workers 4
```

### Verbose mode (show progress per field)
```bash
python registers/extract_registers.py --verbose
```

### Test with limited tables
```bash
python registers/extract_registers.py --limit 3
```

### Process specific table
```bash
python registers/extract_registers.py --table TABLE_2_17
```

### Dry run (parse CSVs without LLM calls)
```bash
python registers/extract_registers.py --dry-run
```

### Combined options
```bash
python registers/extract_registers.py --workers 2 --limit 10 --verbose
```

## Command Line Options

| Option | Short | Description |
|--------|-------|-------------|
| `--workers N` | `-w N` | Number of parallel workers (default: 1, max: 4) |
| `--verbose` | `-v` | Show per-field progress |
| `--limit N` | `-l N` | Process only first N tables |
| `--table ID` | `-t ID` | Process specific table only |
| `--dry-run` | | Parse CSVs without LLM calls |

## Output

Creates `registers/registers.json`:

```json
{
  "_metadata": {
    "source": "SD Host Controller Simplified Specification Version 3.00",
    "extraction_date": "2026-02-01",
    "total_reg_classes": 12,
    "total_registers": 30,
    "total_fields": 200,
    "total_relations": 60
  },
  "reg_classes": [...],
  "registers": [...],
  "relations": [...]
}
```

## Processing Notes

### CSV Format Detection
The script auto-detects three CSV formats:
1. **3-column**: `Location, Attrib, Register Field Explanation`
2. **5-column**: `Location, Attrib, Register Field Explanation, Value, Meaning`
3. **4-column alt**: `Address, Access, Field Name, Description`

### Rate Limiting
- 1.5 second delay between API calls
- Auto-retry on rate limit errors (exponential backoff)
- Max 3 retries per field

### Excluded Tables
Non-register tables are automatically excluded:
- TABLE_2_1 (register map)
- TABLE_2_2, 8, 10-12, 25, 31, 36, 41, 42 (reference/truth tables)

## Integration

After extraction, merge into `metadata/metadata.json`:

```bash
python scripts/merge_metadata.py
```

The merge script should:
1. Add REG_CLASS nodes
2. Replace basic REGISTER nodes with detailed ones (including fields)
3. Add new relations (BELONGS_TO, DEFINED_IN, DESCRIBES)

## File Structure

```
registers/
├── extract_registers.py   # Main extraction script
├── registers.json         # Output (generated)
├── context.md             # Schema documentation
└── README.md              # This file
```
