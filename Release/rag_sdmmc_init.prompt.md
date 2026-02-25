# SDMMC RAG Ingestion & Multi-Block Read Analysis

**Date:** 2026-02-24

---

## RAG Sources

| RAG | API Path (from project root) | Spec |
|-----|-----|------|
| **SD Host 3.0** | `python Release/rags/sd-host-3.00-23_02_2026/metadata/metadata_api.py <fn> [args]` | SD Host Controller 3.0 |
| **SD Physical Layer 3.0** | `python Release/rags/sd_phy-3.00-23_02_2026/metadata/metadata_api.py <fn> [args]` | SD Card Physical Layer |
| **eMMC 4.51** | `python Release/rags/emmc-4.51-23_02_2026/metadata/metadata_api.py <fn> [args]` | eMMC Electrical Standard |
| **SDMMC (ST)** | `python Release/rags/sdmmc-23_02_2026/metadata/metadata_api.py <fn> [args]` | ST SDMMC RM0452 |

## Ingestion Steps

1. Verify each RAG is accessible: `python <api_path> get_spec_info`
2. Search for multi-block read related content in each RAG
3. Search for CMD18, CMD23, CMD12, block count, open-ended transfer
4. Search for ADDRESS_OUT_OF_RANGE, data timeout behavior
5. Retrieve relevant spec chunks, tables, and figures

---

# Analysis: How Does the Card Know How Much Data to Send in Multi-Block Read?

## 1. The Two Transfer Types (from specs)

### 1A. Open-Ended Multiple Block Read (No CMD23)

**SD PHY Spec** (Section 4.3.3, CHUNK_4_3_3_0):
> "CMD18 (READ_MULTIPLE_BLOCK) starts a transfer of several consecutive blocks. Blocks will be continuously transferred until a STOP_TRANSMISSION command (CMD12) is issued."

**eMMC Spec** (Section 6.6.9.1, CHUNK_6_6_9_1_1):
> "Open-ended Multiple block read — The number of blocks for the read multiple block operation is not defined. The Device will continuously transfer data blocks until a stop transmission command is received."

⚠ **The card does NOT know how much data to send.** It sends blocks forever until CMD12.

### 1B. Pre-Defined Block Count (CMD23 + CMD18)

**SD PHY Spec** (Section 4.7.4, CHUNK_4_7_4_2):
> "CMD23 — SET_BLOCK_COUNT: Specify block count for CMD18 and CMD25."

**eMMC Spec** (Section 6.6.9.1, CHUNK_6_6_9_1_1):
> "Multiple block read with pre-defined block count — The Device will transfer the requested number of data blocks, terminate the transaction and return to transfer state. Stop command is not required at the end of this type of multiple block read."

> "In order to start a multiple block read with pre-defined block count the host must use the SET_BLOCK_COUNT command (CMD23) immediately preceding the READ_MULTIPLE_BLOCK (CMD18) command. Otherwise the Device will start an open-ended multiple block read."

✅ **The card knows exactly how many blocks to send. Auto-stops. No CMD12 needed.**

**Edge case — CMD23 with arg=0:**
> (eMMC CHUNK_6_6_9_1_1): "If the host sets the argument of the SET_BLOCK_COUNT command (CMD23) to all 0s, then the command is accepted; however, a subsequent read will follow the open-ended multiple block read protocol (STOP_TRANSMISSION command - CMD12 - is required)."

---

## 2. What Happens at End of Card? (ADDRESS_OUT_OF_RANGE)

**SD PHY Spec** (Section 4.3.3, CHUNK_4_3_3_0):
> "When the last block of user area is read using CMD18, the host should ignore OUT_OF_RANGE error that may occur even the sequence is correct."

**eMMC Spec** (Section 6.6.9.1, CHUNK_6_6_9_1_1):
> "If the host provides an out of range address as an argument to either CMD17 or CMD18. ADDRESS_OUT_OF_RANGE is set."
> "If the Device detects an error (e.g. out of range, address misalignment, internal error, etc.) during a multiple block read operation (both types) it will stop data transmission and remain in the Data State. The host must then abort the operation by sending the stop transmission command."

**eMMC Boot Partition** (Section 6.3.5, CHUNK_6_3_5_0):
> "If the master uses CMD18 (READ_MULTIPLE_BLOCK) and then reads past the selected partition boundary, the slave will report an ADDRESS_OUT_OF_RANGE error."

⚠ **Card does NOT wrap around. It sets ADDRESS_OUT_OF_RANGE and stops sending data. Host must send CMD12.**

---

## 3. HC-Side: Block Count Register & Transfer Modes

### SD Host 3.0 — Block Count Register (REG_006, offset 006h)

**Field REG_006_F0: "Blocks Count For Current Transfer"** (16-bit, RW):
> "This register is enabled when Block Count Enable in the Transfer Mode register is set to 1 and is valid only for multiple block transfers. The Host Controller decrements the block count after each block transfer and stops when the count reaches zero. Setting the block count to 0 results in no data blocks is transferred."

### SD Host 3.0 — Transfer Mode Register (REG_00C, offset 00Ch)

**Transfer Type Determination** (Section 2.2.5, CHUNK_2_2_5_2, Table 2-8):

| Multi/Single Block Select | Block Count Enable | Block Count | Function |
|---|---|---|---|
| 0 | Don't care | Don't care | **Single Transfer** |
| 1 | 0 | Don't care | **Infinite Transfer** |
| 1 | 1 | Not Zero | **Multiple Transfer** |
| 1 | 1 | Zero | **Stop Multiple Transfer** |

**Block Count Enable** (bit 01, CHUNK_2_2_5_1):
> "This bit is used to enable the Block Count register, which is only relevant for multiple block transfers. When this bit is 0, the Block Count register is disabled, which is useful in executing an infinite transfer."
> "If ADMA2 data transfer is more than 65535 blocks, this bit shall be set to 0."

**Auto CMD23** (bits 03-02, CHUNK_2_2_5_1):
> "When this bit field is set to 10b, the Host Controller issues a CMD23 automatically before issuing a command specified in the Command Register."
> "32-bit block count value for CMD23 is set to SDMA System Address / Argument 2 register."

### SD Host 3.0 — Block Count Section 1.15 (CHUNK_1_16_0)
> "Set Block Count Command (CMD23) is defined by the Physical Layer Specification Version 3.00. It provides timing free method to stop a multiple block operation."
> "Data length of a data transfer operation for host side is determined as described in Table 1-14:"

| Transfer Mode | Block Count Enable | Data Length |
|---|---|---|
| Non ADMA | 1 | Block Count Register Value |
| ADMA | 0 | Total length of ADMA Descriptor |

> "It is important note that a total data transfer length for Host Controller shall be equivalent to that of card."

### SD Host 3.0 — ADMA2 Special Case (CHUNK_1_13_3_0)
> "Block Count register limits the maximum of 65535 blocks transfer. If ADMA2 operation is more than 65535 blocks transfer, Block Count Register shall be disabled by setting 0 to Block Count Enable."
> "In case of read operation, several blocks may be read more than required. The Host Driver shall ignore out of range error if the read operation is for the last block of memory area."

---

## 4. SDMMC (ST) Specifics — RM0452

**SDMMC Block Count** (CHUNK_57_3_2_5_0):
> "This register is enabled when Block count enable in the Transfer mode register is set to 1 and is valid only for multiple block transfers. The HC decrements the block count after each block transfer and stops when the count reaches zero."

**SDMMC Transfer Mode** (CHUNK_57_3_2_6_1):
Same Table 2-8 determination as standard SD Host 3.0.

**SDMMC Auto CMD23** (CHUNK_57_3_2_6_1):
> "When set to 10b, the host controller issues a CMD23 automatically before issuing a command specified in the Command register. 32-bit block count value for CMD23 is set to SDMA System address / Argument 2 register."

**SDMMC Dual-FIFO** (CHUNK_57_4_1_2, CHUNK_57_3_1_0):
> "During read transaction, when the internal block buffer is full it can not accept any more data from the card. In these circumstances, host controller will stop the clock to card in order to avoid buffer overrun condition."
> ST uses a dual-FIFO (FIFO_1/FIFO_2) ping-pong buffer scheme — this is an ST implementation detail.

---

## 5. CMD12 Mid-Transfer

**eMMC Spec** (CHUNK_6_6_9_1_1):
> "The host can abort reading at any time, within a multiple block operation, regardless of its type. Transaction abort is done by sending the stop transmission command."

**Post pre-defined completion** (CHUNK_6_6_9_1_1):
> "If the host sends a stop transmission command after the Device transmits the last block of a multiple block operation with a pre-defined number of blocks, it is regarded as an illegal command, since the Device is no longer in data state."

**SD Host 3.0 Auto CMD12** (CHUNK_2_2_5_1):
> "When this field is set to 01b, the Host Controller issues CMD12 automatically when last block transfer is completed."

---

## 6. Design Implications for TLM Abstracted Protocol

Based on the above spec evidence, here is how the card-HC protocol should work:

### Case A: Pre-Defined Count (CMD23 + CMD18 or Block Count Enable=1)

Both sides know the total:
- HC: `Block Count Register × Block Size` = total bytes
- Card: CMD23 argument = total blocks

**TLM Protocol:** HC requests all data at once → Card returns `vector<uint8_t>` of exact size → HC buffers and drains timed per event queue.

### Case B: Infinite/Open-Ended Transfer (Block Count Enable=0, no CMD23)

Only the **card doesn't know** when to stop. The **HC has no count either** (Block Count register disabled).

**TLM Protocol:** HC must request data block-by-block (or in chunks). Card returns one block at a time. HC drains each block, then requests the next. Continues until:
- CMD12 is issued (software abort)
- ADDRESS_OUT_OF_RANGE (card hits end of space, stops, HC sees error)
- Data timeout (card unresponsive)

### Case C: HC knows count but card doesn't (Block Count Enable=1, no CMD23)

HC has `Block Count Register` set but didn't send CMD23. The card thinks it's open-ended.

**TLM Protocol:** HC can request the full amount from the card (hint). Card sends blocks until told to stop. HC issues Auto CMD12 after its internal block count reaches zero. 

### Summary Table

| Scenario | HC Knows Count? | Card Knows Count? | Card Stop Mechanism | HC Stop Mechanism |
|---|---|---|---|---|
| CMD23 + CMD18 | ✅ Block Count Reg | ✅ CMD23 argument | Auto-stop after N blocks | Block Count → 0 |
| Block Count Enable=1, no CMD23 | ✅ Block Count Reg | ❌ | CMD12 (or Auto CMD12) | Block Count → 0 + issue CMD12 |
| Block Count Enable=0 (infinite) | ❌ | ❌ | CMD12 only | SW issues CMD12 |
| CMD23 arg=0 | ❌ | ❌ (falls to open-ended) | CMD12 required | SW issues CMD12 |
| Card hits end of space | N/A | N/A | ADDRESS_OUT_OF_RANGE, stop | Data timeout → error |

**All citations above are from RAG queries, not from general knowledge.**
