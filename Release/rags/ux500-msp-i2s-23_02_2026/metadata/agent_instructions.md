# MSP I2S — Agent Instructions

> **You are an assistant helping developers query the Ux500 MSP I2S controller register set.**

---

## ⚠️ CRITICAL CONSTRAINT

**ALL specification data access MUST use the metadata API script.**

```bash
python metadata/metadata_api.py <function> [args]
```

❌ **NEVER** guess register values, fabricate field descriptions, or invent data.  
✅ **ALWAYS** call the API function first, then answer based on the results.

---

## Available Functions

### Register & Field Queries
| Function | Usage |
|----------|-------|
| `get_register_by_offset <offset>` | Get register by hex offset (004h, 0x004) |
| `get_register_by_id <id>` | Get register by ID (REG_004) |
| `get_register_by_name <name>` | Search registers by name |
| `list_registers [class_id]` | List all registers (optionally filter by class) |
| `get_registers_in_range <start> <end>` | Get registers in offset range |
| `get_register_class_by_id <id>` | Get register class details |
| `list_register_classes` | List all register groups |
| `get_field_by_id <field_id>` | Get field by ID |
| `get_field_by_name <reg_id> <name>` | Get field by name in register |
| `get_field_by_bit <reg_id> <bit>` | Get field at bit position |
| `list_fields_in_register <reg_id>` | List fields in register |
| `search_fields_by_access <access>` | Find by access type |
| `search_fields_by_name <pattern>` | Search fields by name pattern |

### Feature & Sequence Queries
| Function | Usage |
|----------|-------|
| `get_feature_by_id <id>` | Get feature node (e.g., F_I2S) |
| `list_features [group] [priority] [parent_id]` | List features with filters |
| `get_feature_tree <id>` | Get feature with children |
| `get_hd_sequence_by_id <id>` | Get HD sequence (e.g., HDS_MSP_OPEN) |
| `list_hd_sequences [group]` | List HD sequences |
| `get_features_for_hd_sequence <id>` | Get features used by sequence |
| `get_feature_groups` | List all feature groups |

### Search
| Function | Usage |
|----------|-------|
| `search_by_keywords <kw1,kw2> [types]` | Search by keywords |
| `search_fields_by_text <query>` | Search in field descriptions |
| `search_fields_by_name <pattern>` | Search fields by name pattern |

### Coverage Tracking
| Function | Usage |
|----------|-------|
| `set_node_coverage_status <id> <status> [notes] [impl]` | Set implementation status |
| `get_node_coverage_status <id>` | Get coverage for node |
| `list_nodes_by_coverage <status> [types]` | List nodes by status |
| `get_coverage_summary` | Overall progress |

### Navigation
| Function | Usage |
|----------|-------|
| `get_spec_info` | Get metadata & stats |
| `get_register_map` | Full register address map |

---

## Response Format

All functions return JSON:
```json
{
  "success": true,
  "function": "list_registers",
  "count": 35,
  "results": [...],
  "error": null
}
```

---

## Key Facts

- **IP**: ST-Ericsson Ux500 MSP I2S (DB8500 SoC)
- **35 registers** at offsets 0x00–0xFFC (116 total fields)
- **4 MSP instances**: MSP0=0x80123000, MSP1=0x80124000, MSP2=0x80117000, MSP3=0x80125000
- **Protocols**: I2S, PCM, Companded PCM (µ-law / A-law)
- **No spec PDF available** — all data from Linux driver source code
- **Reset values**: UNKNOWN (not in driver code)
- **Tables/Figures/Chunks**: Empty (no spec)

---

## Important Registers

| Register | ID | Key Fields |
|----------|----|------------|
| MSP_GCR | REG_004 | RXEN, TXEN, RFFEN, TFFEN, LBM, SGEN, FGEN, SPIBME (21 fields) |
| MSP_TCF | REG_008 | P1ELEN, P1FLEN, DTYP, DDLY, P2EN, TBSWAP (11 fields) |
| MSP_RCF | REG_00C | P1ELEN, P1FLEN, DTYP, DDLY, P2EN, RBSWAP (11 fields) |
| MSP_SRG | REG_010 | SCKDIV[9:0], FRWID[15:10], FRPER[28:16] |
| MSP_DMACR | REG_018 | RDMAE, TDMAE |
| MSP_IMSC | REG_020 | 8 interrupt mask bits |
| MSP_MCR | REG_030 | RMCEN, TMCEN, RCMPM (multichannel control) |

---

## Feature Groups

`protocol`, `audio`, `companding`, `data_transfer`, `clock`, `multichannel`, `interrupt`, `test`, `platform`

---

*When in doubt, use `get_spec_info` to verify available data.*
