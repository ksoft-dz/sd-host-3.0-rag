# SDMMC RAG — Agent Instructions

> **You are an assistant helping developers and testers query the SDMMC (3MCR) controller from the SPC58 H-Line Reference Manual (RM0452).**

---

## CRITICAL CONSTRAINT

**ALL specification data access MUST use the metadata API script.**

```bash
python sdmmc_rag/_rag_v2/metadata/metadata_api.py <function> [args]
```

- **NEVER** read spec files directly, guess register values, or fabricate information.
- **ALWAYS** call the API function first, then answer based on the results.

---

## IP Summary

| Property | Value |
|----------|-------|
| **IP** | SDMMC (3MCR — multi card reader controller) |
| **SoC** | SPC58 H-Line (Power Architecture automotive MCU, triple z4 cores, 200 MHz) |
| **Reference Manual** | RM0452 Rev 4 (June 2021), Section 57 (pages 2849-2929) |
| **Standard Compliance** | SD Host Controller 3.0, MMC 4.51 |
| **PDF** | `sdmmc_chapter_57.pdf` (81-page extraction from 3897-page RM) |

---

## RAG Statistics

| Artifact | Count |
|----------|-------|
| Sections | 82 |
| Text Chunks | 81 |
| Tables | 59 |
| Figures | 57 |
| Registers | 43 |
| Register Fields | 91 |
| Register Classes | 7 |
| Features | 40 |
| HD Sequences | 7 |
| Relations | 101 |
| RM Raw Content Chunks | 149 (full SoC reference, ~889K words) |
| **Total Nodes** | **294** |

---

## Available Functions

### Category 1: Register & Field Queries
| Function | Usage |
|----------|-------|
| `get_register_by_offset <offset>` | Get register by hex offset (028, 0x028) |
| `get_register_by_id <id>` | Get register by ID (REG_028) |
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

### Category 2: Spec Content
| Function | Usage |
|----------|-------|
| `get_page_content <page>` | Get content of spec page |
| `get_section_by_number <num>` | Get section (e.g., "57.3.2.10") |
| `get_chunk_by_id <chunk_id>` | Get specific text chunk |
| `list_sections [parent]` | List sections |

### Category 3: Tables & Figures
| Function | Usage |
|----------|-------|
| `get_table_by_id <id>` | Get table metadata |
| `get_table_csv <id>` | Get table as CSV data |
| `list_tables [type]` | List tables |
| `get_figure_by_id <id>` | Get figure metadata |
| `get_figure_plantuml <id>` | Get PlantUML source |
| `list_figures [type]` | List figures |

### Category 4: Features & HD Sequences
| Function | Usage |
|----------|-------|
| `get_feature_by_id <id>` | Get feature details |
| `list_features [group]` | List features (optionally filter by group) |
| `get_hd_sequence_by_id <id>` | Get HD sequence details |
| `list_hd_sequences` | List all HD sequences |

### Category 5: Search
| Function | Usage |
|----------|-------|
| `search_by_keywords <kw1,kw2> [types]` | Search by keywords |
| `search_chunks_by_text <query>` | Full-text search in spec |
| `search_fields_by_text <query>` | Search in field descriptions |

### Category 6: Relationships
| Function | Usage |
|----------|-------|
| `get_tables_for_register <reg_id>` | Find tables defining register |
| `get_figures_for_register <reg_id>` | Find figures visualizing register |
| `get_chunks_for_register <reg_id>` | Find chunks describing register |
| `get_registers_for_table <table_id>` | Find registers defined by table |

### Category 7: Navigation
| Function | Usage |
|----------|-------|
| `get_spec_info` | Get spec metadata & stats |
| `get_register_map` | Full register address map |

---

## Register Classes

| Class | Offset Range | Description |
|-------|-------------|-------------|
| `REGCLASS_CMD_DATA` | 0x000–0x00F | Command & Data Transfer (SDMASYSADDR, BLOCKSIZE, BLOCKCOUNT, ARGUMENT1, TRANSFERMODE, COMMAND) |
| `REGCLASS_RESPONSE` | 0x010–0x01F | Response Registers (RESPONSEn) |
| `REGCLASS_HOST_CTRL` | 0x020–0x02F | Host Control & Configuration (DATAPORT, PRESENTSTATE, HOSTCONTROL1, POWERCONTROL, BLOCKGAPCONTROL, WAKEUPCONTROL, CLOCKCONTROL, TIMEOUTCONTROL, SOFTWARERESET) |
| `REGCLASS_INTERRUPT` | 0x030–0x03F | Interrupt & Status (NORMALINTRSTS, ERRORINTRSTS, enable/signal enables, AUTOCMDERRSTS, HOSTCONTROL2) |
| `REGCLASS_CAPABILITIES` | 0x040–0x06F | Capabilities & Preset Values (CAPABILITIES, MAXCURRENTCAP, PRESETVALUEn) |
| `REGCLASS_ADMA` | 0x054–0x05F | ADMA Control (ADMAERRSTS, ADMASYSADDRn) |
| `REGCLASS_VENDOR` | 0x080–0x0FF | ST-Specific Extensions (BOOTTIMEOUTCNT, CORE_CONFIG, FB_CLK_SEL, DBG_STA1-5) |

---

## Key Features

| Feature ID | Name | Priority |
|------------|------|----------|
| `F_SD_HOST_3_0` | SD Host Controller 3.0 Compliance | P0 |
| `F_MMC_4_51` | MMC 4.51 Support | P0 |
| `F_3MCR` | 3MCR Multi Card Reader | P0 |
| `F_SDMA` | SDMA Transfer | P0 |
| `F_ADMA2` | ADMA2 Transfer | P0 |
| `F_BOOT_OP` | Boot Operation | P1 |
| `F_INTERRUPT` | Interrupt System | P0 |
| `F_CLOCK_CONTROL` | Clock Control | P0 |

---

## HD Sequences (Driver Flow Sequences)

| Sequence ID | Name | Primary Section |
|-------------|------|-----------------|
| `HDS_NON_DMA_XFER` | Non-DMA Data Transfer | 57.4.1 |
| `HDS_DMA_XFER` | DMA Data Transfer | 57.4.2 |
| `HDS_ADMA_XFER` | ADMA Data Transfer | 57.4.3 |
| `HDS_ABORT_XFER` | Abort Transaction | 57.4.4 |
| `HDS_BOOT_OP` | Boot Operation | 57.4.5 |
| `HDS_CARD_INIT` | Card Detection and Initialization | 57.2.5 |
| `HDS_CLK_FREQ_CHANGE` | Clock Frequency Change | 57.2.2 |

---

## rm_raw_content

The `metadata.json` also contains `rm_raw_content` — 149 raw text chunks from the full RM0452 reference manual (3897 pages). These provide lightweight context about the broader SPC58 H-Line SoC (86 chapters covering: cores, clocks, memory, peripherals, safety, security, debug).

Access via: `metadata["rm_raw_content"]["chunks"]`

Each chunk has: `id`, `title`, `page_range`, `page_count`, `word_count`, `content`.
