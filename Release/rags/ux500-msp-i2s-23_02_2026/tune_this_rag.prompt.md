# MSP I2S RAG — Tuning Prompt

> **This file is your interface to enrich and correct the MSP I2S metadata knowledge graph.**
> Paste spec fragments, register descriptions, field corrections, or any additional info below.
> The agent will update `metadata/metadata.json` accordingly via `metadata_api.py`.

---

## ⛔ MANDATORY RULES — DO NOT VIOLATE

1. **STRICTLY STICK TO WHAT THE USER GIVES AS INFO.**
   - Do NOT invent, hallucinate, or infer data beyond what the user explicitly provides.
   - Do NOT fill gaps with "reasonable assumptions", "common practice", or "educated guesses".
   - If a field width, reset value, or description is not given, leave it as-is or mark it `UNKNOWN`.
   - If the user provides partial info (e.g., only 3 fields of a register), update ONLY those 3 fields.

2. **EXCEPTIONS**: Only deviate from rule 1 if the user gives **CLEAR AND HARDCORE OTHER INSTRUCTIONS**
   (e.g., "fill in all gaps using ARM PrimeCell MSP TRM" or "infer reset values from driver init code").
   Casual remarks like "do your best" or "figure it out" do **NOT** override rule 1.

3. **ALL updates to the knowledge graph MUST go through `metadata_api.py`.**
   - Never edit `metadata.json` by hand or with raw file writes.
   - Use the script's `set_node_coverage_status`, or re-run `generate_metadata.py` after modifying it.

4. **Preserve existing data.** When adding new info, merge — do not overwrite unrelated fields.

5. **Cite your source.** When updating a field, note where the info came from (e.g., "from user-provided spec page", "from driver code", "from DT binding").

---

## Current State of the RAG

| Resource | Count | Notes |
|----------|-------|-------|
| Registers | 35 | 0x00–0xFFC, derived from `ux500-msp-i2s.h` |
| Fields | 116 | Bit definitions from mask/shift #defines |
| Register Classes | 2 | CORE (0x00–0x8C), ID (0xFE0–0xFFC) |
| Features | 20 | Derived from driver capabilities |
| HD Sequences | 6 | Derived from driver function call patterns |
| Tables | 0 | None — no spec PDF available |
| Figures | 0 | None — no spec PDF available |
| Spec Chunks | 0 | None — no spec PDF available |
| **Total Nodes** | **63** | |
| **Total Relations** | **53** | |

### Source files (read-only reference)

| File | Content |
|------|---------|
| `driver_sources/ux500-msp-i2s.h` | Register offsets, bit masks, shift constants, enums |
| `driver_sources/ux500-msp-i2s.c` | Driver implementation — configure, enable, flush, open/close |
| `driver_sources/device-tree-binding.txt` | DT compatible string, register ranges, example nodes |
| `driver_sources/cpu-db8500.c` | 4 MSP instances: MSP0–MSP3 base addresses |

---

## Known Gaps & Ambiguities

The following items could NOT be determined from driver code alone.
If you have a spec fragment that clarifies any of these, paste it below.

### 1. TCF/RCF bit 10 overlap
- `TFSPOL_SHIFT=10` (frame sync polarity) and `DTYP_SHIFT=10, COMPANDING_MODE_MASK=0xC00` (companding mode bits [11:10]) both claim bit 10.
- Driver `set_prot_desc_tx()` OR's both into MSP_TCF.
- **Likely**: TFSPOL is GCR-only (bit 10 in GCR context); the TCF bit 10 is part of DTYP. The driver may have a bug or dual-purpose usage.
- **Action needed**: Confirm TCF register layout for bits [11:10].

### 2. GCR bits [31:24]
- Only bits [23:0] are defined via driver masks.
- Bits [27:24] and [31:29] may be reserved or undocumented.
- **Action needed**: Confirm reserved bits or document additional fields.

### 3. MCR field widths
- `RMCSF_SHIFT=1`, `RCMPM_SHIFT=3` → gap suggests RMCSF might be 2 bits ([2:1]) or bit 2 is reserved.
- `TNCSF_SHIFT=6` → unknown width (1 bit? 2 bits?).
- **Action needed**: Confirm MCR register bit-field layout.

### 4. Reset values
- No reset values available from driver code for any register.
- **Action needed**: Provide reset values from spec or test data.

### 5. Interrupt bit names
- Interrupt bits are named from mask constants (RSIP, ROEP, RFEP, RFIP, TSIP, TUEP, TFEP, TFIP).
- Full names inferred: Receive Service Interrupt Pending, Receive Overrun Error, etc.
- **Action needed**: Confirm official interrupt bit names.

### 6. IODLY, ITIP, ITOP, TSTDR field layouts
- These registers have single 32-bit fields in metadata because no sub-field definitions exist in driver code.
- **Action needed**: Provide detailed bit-field breakdowns.

---

## How to Provide Enrichment Data

### Option A: Paste a spec fragment
```
### Register: MSP_GCR (0x04)
Bit [31:29] - RESERVED
Bit [28] - TBSWAP ...
...
Reset value: 0x00000000
```

### Option B: Provide field corrections
```
Fix: REG_004 field TFSSEL bits should be 12:11 (confirmed)
Fix: REG_030 field RMCSF is 1 bit only, bit 2 is reserved
Add: REG_004 reset_value = "0x00000000"
```

### Option C: Provide new features or sequences
```
Add feature: F_FRAME_SYNC_GEN — Frame sync generation (internal/external)
  group: clock
  priority: P1
  description: "MSP can generate frame sync internally via FGEN bit in GCR"
```

### Option D: Reference external documentation
```
Use ARM DDI0218 (PrimeCell MSP) for:
- Complete register field descriptions
- Reset values
- Timing diagrams
NOTE: THIS IS AN EXPLICIT OVERRIDE — fill gaps from this document.
```

---

## API Quick Reference

```bash
# Query
python metadata_api.py get_spec_info
python metadata_api.py list_registers
python metadata_api.py list_fields_in_register REG_004
python metadata_api.py search_fields_by_name "RXEN"
python metadata_api.py list_features
python metadata_api.py list_hd_sequences

# Coverage tracking
python metadata_api.py set_node_coverage_status REG_004 IMPLEMENTED "verified" "driver.c"
python metadata_api.py get_coverage_summary
```

---

## Enrichment Log

_Record each tuning session below so changes are traceable._

| Date | What changed | Source | Who |
|------|-------------|--------|-----|
| 2025-02-23 | Initial metadata from driver code | ux500-msp-i2s.h/.c | auto-generated |
| | | | |

---

*Remember: stick to what the user provides. No guessing. No hallucinating. No "filling in the blanks".*
