# MSP I2S RAG — Context

## Overview

This RAG contains the register-level knowledge graph for the **ST-Ericsson Ux500 MSP (Multi-Serial Port) I2S Controller**, as found in the DB8500 SoC. The data was extracted entirely from Linux kernel driver source code — no hardware specification PDF was available.

## IP Block

- **Name**: MSP I2S (Multi-Serial Port with I2S support)
- **SoC**: ST-Ericsson DB8500 (Ux500 platform)
- **Bus**: APB (AMBA Peripheral Bus)
- **Input Clock**: 48 MHz
- **Compatible**: `stericsson,ux500-msp-i2s`
- **Register Page**: 4 KB (0x000–0xFFF)

## MSP Instances

| Instance | Base Address | Notes |
|----------|-------------|-------|
| MSP0 | 0x80123000 | |
| MSP1 | 0x80124000 | Used in DT example |
| MSP2 | 0x80117000 | |
| MSP3 | 0x80125000 | Used in DT example |

## Data Sources

All data extracted from 4 Linux kernel driver files:

| File | Lines | Content |
|------|-------|---------|
| `ux500-msp-i2s.h` | 430 | Register offsets, bit masks, shift constants, enums |
| `ux500-msp-i2s.c` | 578 | Driver implementation (configure, enable, flush, open/close/trigger) |
| `device-tree-binding.txt` | 45 | Device tree binding documentation |
| `cpu-db8500.c` | 182 | Platform device registration for 4 MSP instances |

## Metadata Summary

| Resource | Count |
|----------|-------|
| Registers | 35 (116 fields) |
| Register Classes | 2 |
| Features | 20 |
| HD Sequences | 6 |
| Tables | 0 (no spec) |
| Figures | 0 (no spec) |
| Spec Chunks | 0 (no spec) |
| **Total Nodes** | **63** |
| **Total Relations** | **53** |

## Register Map

### Core Registers (REGCLASS_CORE: 0x00–0x8C)

| Offset | Name | Fields | Description |
|--------|------|--------|-------------|
| 0x00 | MSP_DR | 1 | Data Register (TX/RX FIFO access) |
| 0x04 | MSP_GCR | 21 | Global Configuration Register |
| 0x08 | MSP_TCF | 11 | Transmit Configuration Register |
| 0x0C | MSP_RCF | 11 | Receive Configuration Register |
| 0x10 | MSP_SRG | 3 | Sample Rate Generator Register |
| 0x14 | MSP_FLR | 6 | Flag Register |
| 0x18 | MSP_DMACR | 2 | DMA Control Register |
| 0x20 | MSP_IMSC | 8 | Interrupt Mask Set/Clear |
| 0x24 | MSP_RIS | 8 | Raw Interrupt Status |
| 0x28 | MSP_MIS | 8 | Masked Interrupt Status |
| 0x2C | MSP_ICR | 8 | Interrupt Clear Register |
| 0x30 | MSP_MCR | 5 | Multichannel Control Register |
| 0x34 | MSP_RCV | 1 | Receive Comparison Value |
| 0x38 | MSP_RCM | 1 | Receive Comparison Mask |
| 0x40 | MSP_TCE0 | 1 | TX Channel Enable 0 |
| 0x44 | MSP_TCE1 | 1 | TX Channel Enable 1 |
| 0x48 | MSP_TCE2 | 1 | TX Channel Enable 2 |
| 0x4C | MSP_TCE3 | 1 | TX Channel Enable 3 |
| 0x60 | MSP_RCE0 | 1 | RX Channel Enable 0 |
| 0x64 | MSP_RCE1 | 1 | RX Channel Enable 1 |
| 0x68 | MSP_RCE2 | 1 | RX Channel Enable 2 |
| 0x6C | MSP_RCE3 | 1 | RX Channel Enable 3 |
| 0x70 | MSP_IODLY | 1 | I/O Delay Register |
| 0x80 | MSP_ITCR | 2 | Integration Test Control |
| 0x84 | MSP_ITIP | 1 | Integration Test Input |
| 0x88 | MSP_ITOP | 1 | Integration Test Output |
| 0x8C | MSP_TSTDR | 1 | Test Data Read Register |

### Identification Registers (REGCLASS_ID: 0xFE0–0xFFC)

| Offset | Name | Description |
|--------|------|-------------|
| 0xFE0–0xFEC | MSP_PID0–PID3 | Peripheral Identification |
| 0xFF0–0xFFC | MSP_CID0–CID3 | Component Identification |

## Supported Protocols

Derived from driver protocol descriptors:

1. **I2S** — Standard Inter-IC Sound, 32-bit elements, dual-phase, active-low fsync, 1-bit data delay
2. **PCM** — Pulse Code Modulation, 16-bit elements, single-phase, 256-element frames
3. **Companded PCM** — PCM with µ-law or A-law companding, 8-bit elements

## Feature Groups

| Group | Features | Description |
|-------|----------|-------------|
| protocol | I2S, PCM, COMPANDED_PCM | Audio protocol modes |
| audio | DUAL_PHASE, ENDIANNESS, BYTE_SWAP | Audio data formatting |
| companding | ULAW, ALAW | Companding algorithms |
| data_transfer | FIFO, DMA | Data movement mechanisms |
| clock | SRG, FRAME_GEN, CLOCK_SELECT | Clocking infrastructure |
| multichannel | MULTICHANNEL | Multi-channel TDM support |
| interrupt | INTERRUPT | Interrupt generation/handling |
| test | LOOPBACK, INTEGRATION_TEST | Debug/test features |
| platform | DEVICE_TREE | Platform integration |

## Querying

```bash
python metadata/metadata_api.py get_spec_info
python metadata/metadata_api.py list_registers
python metadata/metadata_api.py list_fields_in_register REG_004
python metadata/metadata_api.py search_fields_by_name "RXEN"
python metadata/metadata_api.py list_features
python metadata/metadata_api.py get_register_map
```

## Enrichment

See `tune_this_rag.prompt.md` for instructions on providing additional spec data. The tune prompt enforces a strict policy: only incorporate data the user explicitly provides.

## Limitations

- **No reset values** — driver code does not define register reset values
- **No access type verification** — R/W vs RO inferred from driver usage patterns
- **No spec text** — no PDF/HTML spec was available; all info from driver code
- **Some field widths uncertain** — see known ambiguities in tune prompt
