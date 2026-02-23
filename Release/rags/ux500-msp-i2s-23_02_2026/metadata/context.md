# MSP I2S Metadata — Context

## Schema

The `metadata.json` follows the RAG v2.0.0 schema, identical to the SD Host, SDIO, eMMC, and SD Physical Layer RAGs.

### Top-level structure

```json
{
  "metadata_version": "2.0.0",
  "spec_info": { "name", "version", "page_offset" },
  "extraction_info": { "extracted_date", "pipeline", "sources", "statistics" },
  "nodes": [ ... ],
  "relations": [ ... ]
}
```

### Node types

| Type | ID Pattern | Count | Description |
|------|-----------|-------|-------------|
| REGISTER | `REG_<offset>` | 35 | Register definitions with fields |
| REG_CLASS | `REGCLASS_<name>` | 2 | Register groupings |
| FEATURE | `F_<name>` | 20 | IP capabilities/features |
| HD_SEQUENCE | `HDS_<name>` | 6 | Hardware driver sequences |
| TABLE | `TABLE_<n>` | 0 | (empty — no spec available) |
| FIGURE | `FIG_<n>` | 0 | (empty — no spec available) |
| SPEC_CHUNK | `CHUNK_<n>` | 0 | (empty — no spec available) |

### Relation types used

| Type | Count | Description |
|------|-------|-------------|
| BELONGS_TO | 35 | Register → REG_CLASS |
| PART_OF | 4 | Sub-feature → Parent feature |
| USES_FEATURE | 14 | HD_SEQUENCE → FEATURE |

### Register node structure

```json
{
  "id": "REG_004",
  "type": "REGISTER",
  "name": "MSP_GCR — Global Configuration Register",
  "offset": "004h",
  "size": 32,
  "access": "R/W",
  "reset_value": "UNKNOWN",
  "description": "...",
  "fields": [
    {
      "id": "REG_004_F0",
      "name": "RXEN",
      "bits": "0",
      "access": "R/W",
      "reset_value": "UNKNOWN",
      "description": "RX Enable. ..."
    }
  ],
  "keywords": ["global", "configuration", ...],
  "spec_refs": [],
  "coverage_status": "NOT_IMPLEMENTED"
}
```

## Data Source

Unlike other RAGs that extract from PDF specifications, this metadata was generated entirely from Linux kernel driver source code:
- Register offsets from `#define MSP_<name> <offset>` in the header
- Field bit positions from `#define <NAME>_SHIFT` and `#define <NAME>_MASK` constants
- Feature identification from driver functions and enum definitions
- HD sequences from driver operational flow (open/trigger/close/flush)

## Generation

```bash
cd msp_i2s_rag/_rag_v2
python scripts/generate_metadata.py
```

This regenerates `metadata/metadata.json` from scratch. The script contains all register/field/feature/sequence definitions as hand-analyzed Python data structures.

## API

The `metadata_api.py` is identical to the one used by all other RAGs. It loads `metadata.json` from the same directory and exposes all query functions.

```bash
python metadata/metadata_api.py <function> [args]
```

All functions return JSON with `{success, function, params, count, results, error}`.
