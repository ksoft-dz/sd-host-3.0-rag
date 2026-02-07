# Scripts Folder

This folder contains the main merge script that combines all extracted resources into a unified metadata graph.

## Quick Start

```powershell
# Run the merge to create metadata.json
python merge_metadata.py

# Dry run (shows stats without creating file)
python merge_metadata.py --dry-run

# Validate existing metadata.json
python merge_metadata.py --validate-only
```

## Scripts

### `merge_metadata.py`
The core merge script that combines tables, figures, and sections into a unified graph.

**Input Sources**:
- `tables/tables_page_map.json` - 60 tables with metadata
- `figures/figures_page_map.json` - 83 figures with metadata
- `spec/sections.json` - 112 sections, 287 chunks

**Output**:
- `metadata/metadata.json` - Unified graph (464 nodes, 570 relations)

**Arguments**:
| Argument | Description |
|----------|-------------|
| `--dry-run` | Show statistics without saving |
| `--validate-only` | Validate existing metadata.json |

## Node Types Generated

| Type | Count | Description |
|------|-------|-------------|
| `TABLE` | 60 | Tables from the spec |
| `FIGURE` | 83 | Figures/diagrams from the spec |
| `SPEC_CHUNK` | 287 | Text chunks from sections |
| `REGISTER` | 34 | Registers parsed from section titles |

## Relation Types Generated

| Type | Count | Description |
|------|-------|-------------|
| `REFERENCES` | 87 | Chunk → Table/Figure references |
| `CHILD_OF` | 259 | Section hierarchy |
| `DEFINED_BY` | ~34 | Register → Table |
| `VISUALIZED_BY` | ~34 | Register → Figure |
| `DESCRIBES` | ~100 | Chunk → Register |

## Output Schema

See `metadata/metadata.json` for the complete structure:

```json
{
  "metadata_version": "1.0.0",
  "spec_info": { ... },
  "extraction_info": {
    "statistics": {
      "total_nodes": 464,
      "by_type": { "TABLE": 60, "FIGURE": 83, "SPEC_CHUNK": 287, "REGISTER": 34 },
      "total_relations": 570
    }
  },
  "nodes": [ ... ],
  "relations": [ ... ]
}
```
