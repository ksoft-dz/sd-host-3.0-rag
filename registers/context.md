# Registers Extraction Context

## Purpose
This folder contains the register extraction pipeline for the SD Host Controller 3.0 specification. It extracts structured register information including register classes, individual registers, and their fields.

## Schema

### REG_CLASS Node
Register classes group related registers by address range and version support.

```json
{
  "id": "REGCLASS_CMD_GEN",
  "type": "REG_CLASS",
  "name": "SD Command Generation",
  "address_range": {
    "start": "000h",
    "end": "00Fh"
  },
  "version_support": {
    "1.00": "Mand.",
    "2.00": "Mand.",
    "3.00": "Mand."
  },
  "source": {
    "figure": "FIG_1_2",
    "table": "TABLE_1_1"
  }
}
```

### REGISTER Node
Individual register with offset, section reference, and field definitions.

```json
{
  "id": "REG_029",
  "type": "REGISTER",
  "name": "Power Control Register",
  "offset": "029h",
  "spec_section": "2.2.11",
  "spec_table": "TABLE_2_17",
  "class_id": "REGCLASS_HOST_CTRL1",
  "source": {
    "table": "TABLE_2_17",
    "page": 32,
    "definition_page": 43
  },
  "fields": [
    {
      "id": "REG_029_F0",
      "name": "SD Bus Power",
      "bits": "00",
      "bit_high": 0,
      "bit_low": 0,
      "access": "RW",
      "raw": "Before setting this bit the SD Host Driver shall set...",
      "abstract": "Controls SD bus power on/off state.",
      "values": [
        { "code": "1", "meaning": "Power on" },
        { "code": "0", "meaning": "Power off" }
      ]
    }
  ]
}
```

### Field Structure
Each field within a register contains:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique field ID (REG_XXX_FN format) |
| `name` | string | Human-readable field name |
| `bits` | string | Bit range (e.g., "07-04", "00") |
| `bit_high` | int | Highest bit number |
| `bit_low` | int | Lowest bit number |
| `width` | int | Bit width of the field |
| `access` | string | Normalized access type (see below) |
| `read_effect` | string | What happens on read (see below) |
| `write_effect` | string | What happens on write (see below) |
| `original_attrib` | string | Original attribute from spec (RW, RO, ROC, etc.) |
| `raw` | string | Original specification text |
| `abstract` | string | LLM-generated summary (max 120 chars) |
| `values` | array | Enumerated values with meanings |

### Access Types (Normalized)
The `access` field is normalized to one of:
- `read-write` - Field can be read and written
- `read-only` - Field can only be read
- `write-only` - Field can only be written
- `reserved` - Reserved field, should not be modified

### Read Effects
The `read_effect` field indicates what happens when software reads:
- `none` - Normal read, value unchanged
- `clear` - Field is cleared to 0 after read (ROC type)
- `undefined` - Read value may be undefined during certain operations

### Write Effects
The `write_effect` field indicates what happens when software writes:
- `none` - Normal write
- `write-1-clear` - Writing 1 clears the bit (RW1C type)
- `auto-clear` - Bit automatically clears after action (RWAC type)
- `ignored` - Writes are ignored (for RO fields)
- `set-by-hardware` - Field set by hardware only (HwInit type)

### Original Attribute Types (from spec)
- `RW` - Read/Write
- `RO` - Read Only
- `WO` - Write Only
- `ROC` - Read Only, Clear on read
- `RW1C` - Read/Write 1 to Clear
- `RWAC` - Read/Write, Auto Clear
- `HwInit` - Hardware Initialized (read-only after reset)
- `Rsvd` - Reserved

### Relations
```
REGISTER --BELONGS_TO--> REG_CLASS
REGISTER --DEFINED_IN--> TABLE
TABLE --DESCRIBES--> REGISTER
```

## Data Sources

| Source | Content |
|--------|---------|
| FIG_1_2 | Register class groupings with address ranges |
| TABLE_1_1 | Version support (1.00, 2.00, 3.00) per class |
| TABLE_2_X | Individual register field definitions |

## Register Classes (12 total)

| ID | Name | Address Range | Ver 1.00 | Ver 2.00 | Ver 3.00 |
|----|------|---------------|----------|----------|----------|
| REGCLASS_CMD_GEN | SD Command Generation | 000h-00Fh | Mand. | Mand. | Mand. |
| REGCLASS_RESPONSE | Response | 010h-01Fh | Mand. | Mand. | Mand. |
| REGCLASS_BUFFER | Buffer Data Port | 020h-023h | Mand. | Mand. | Mand. |
| REGCLASS_HOST_CTRL1 | Host Control 1 and Others | 024h-02Fh | Mand. | Mand. | Mand. |
| REGCLASS_INTERRUPT | Interrupt Controls | 030h-03Dh | Mand. | Mand. | Mand. |
| REGCLASS_HOST_CTRL2 | Host Control 2 | 03Eh-03Fh | N/A | N/A | Mand. |
| REGCLASS_CAPABILITIES | Capabilities | 040h-04Fh | Mand. | Mand. | Mand. |
| REGCLASS_FORCE_EVENT | Force Event | 050h-053h | N/A | Mand. | Mand. |
| REGCLASS_ADMA | ADMA | 054h-05Fh | N/A | Opt. | Mand. |
| REGCLASS_PRESET | Preset Value | 060h-06Fh | N/A | N/A | Mand. |
| REGCLASS_SHARED_BUS | Shared Bus | 0E0h-0E3h | N/A | N/A | Opt. |
| REGCLASS_COMMON | Common Area | 0F0h-0FFh | Mand. | Mand. | Mand. |

## Excluded Tables
These TABLE_2_X files are NOT register field definitions:
- TABLE_2_1: Register map layout
- TABLE_2_2: Available Byte Enable Pattern
- TABLE_2_8: Multi/Single Block function table
- TABLE_2_10/11/12: Response type mappings
- TABLE_2_25/31: Error truth tables
- TABLE_2_36: Current value conversion
- TABLE_2_41/42: Preset value mappings

## Output File
`registers.json` contains:
```json
{
  "_metadata": { ... },
  "reg_classes": [ REG_CLASS nodes ],
  "registers": [ REGISTER nodes with fields ],
  "relations": [ relation objects ]
}
```

## Integration with merge_metadata.py
The `registers.json` output should be merged into `metadata/metadata.json` by the merge script, replacing the basic REGISTER nodes with fully detailed ones including fields.
