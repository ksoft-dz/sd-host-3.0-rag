# Events That Can Interrupt a Data Transfer

> **Source**: SD Host Controller Simplified Specification Version 3.00  
> **Date**: February 2026  
> **Scope**: All events (normal + error) that occur during SDMA and ADMA2 data transfers

---

## Interrupt Registers Involved

| Register | Offset | Role |
|---|---|---|
| Normal Interrupt Status | 030h | Transfer Complete, DMA Interrupt, Block Gap Event, Buffer Read/Write Ready |
| Error Interrupt Status | 032h | Data Timeout, Data CRC, Data End Bit, ADMA Error, Auto CMD Error, Current Limit, Tuning Error |
| Auto CMD Error Status | 03Ch | Auto CMD12/CMD23 sub-errors (Timeout, CRC, End Bit, Index, Not Executed) |
| ADMA Error Status | 054h | ADMA state at error + Length Mismatch |

---

## Table 1 — SDMA Transfer Events

| # | Event | Bit(s) | When it Fires | Impact on Transfer | Driver Action |
|---|---|---|---|---|---|
| 1 | **Command Complete** | Normal[0] | After command response received | Transfer begins on SD bus | Clear bit, read response, wait for data events |
| 2 | **DMA Interrupt** (boundary) | Normal[3] | SDMA address crosses Host SDMA Buffer Boundary (4K–512K, configured in Block Size[14:12]) | **Transfer pauses** — HC stops DMA, waits for driver | Clear bit, write next system address to SDMA System Address reg (000h) — writing upper byte restarts DMA |
| 3 | **Transfer Complete** | Normal[1] | Last block transferred & busy released (write) or last data read to host system (read) | **Transfer ends normally** | Clear bit. Done. |
| 4 | **Block Gap Event** | Normal[2] | Stop At Block Gap Request was set AND read/write stopped at block gap | **Transfer paused** at block gap | Continue Request to resume, or Suspend, or abort. Must wait for Transfer Complete before restarting. |
| 5 | **Data Timeout Error** | Error[4] | No data/busy within timeout period (TMCLK × 2^(13+val)) | **Transfer aborted** | Error recovery: reset DAT line, optionally issue CMD12 |
| 6 | **Data CRC Error** | Error[5] | CRC mismatch in received data block | **Transfer corrupted** — HC may stop | Error recovery: reset DAT line, retry |
| 7 | **Data End Bit Error** | Error[6] | End bit of data block is 0 (should be 1) | **Transfer corrupted** | Error recovery |
| 8 | **Current Limit Error** | Error[7] | Power supply current exceeded | **Transfer may be corrupted** | Error recovery, check power |
| 9 | **Auto CMD12 Error** | Error[8] | Auto CMD12 response has errors (Auto CMD12 Enable set) | Data transfer completed but stop command failed | Check Auto CMD Error Status reg (03Ch). Recovery per §3.10.2 |
| 10 | **Auto CMD23 Error** | Error[8] | Auto CMD23 response has errors (Auto CMD23 Enable set) | **Main command NOT issued** — no transfer starts | Check Auto CMD Error Status. Recovery needed. |
| 11 | **Tuning Error** | Error[10] | Unrecoverable tuning circuit error during transfer | **Highest priority** — data must be discarded | Abort command, perform re-tuning |
| 12 | **Transfer Complete + Stop At Block Gap** | Normal[1] | Stop At Block Gap → data flushed | **Transfer ends** (partial) | Clear bit. Partial transfer complete. |

### SDMA Normal Flow

```
Command Complete
  → [DMA Interrupt → reprogram SDMA address → DMA resumes] ... (repeats at each boundary)
  → Transfer Complete
```

> "DMA Interrupt shall not be generated after Transfer Complete" (§2.2.17).  
> Transfer Complete has higher priority than DMA Interrupt.

---

## Table 2 — ADMA2 Transfer Events

| # | Event | Bit(s) | When it Fires | Impact on Transfer | Driver Action |
|---|---|---|---|---|---|
| 1 | **Command Complete** | Normal[0] | After command response received | ADMA2 starts executing descriptor table automatically | Clear bit, read response, wait for data events |
| 2 | **DMA Interrupt** (descriptor Int bit) | Normal[3] | A descriptor with **Int=1** attribute completes its operation | **Informational only** — transfer continues automatically to next descriptor | Clear bit. Used for debugging/progress. Spec: "Suppose that it is used for debugging." |
| 3 | **Transfer Complete** | Normal[1] | Descriptor with **End=1** completes + last data transferred | **Transfer ends normally** | Clear bit. Done. |
| 4 | **Block Gap Event** | Normal[2] | Stop At Block Gap Request set AND ADMA2 stopped at block gap | **Transfer paused** — ADMA2 stops. HC uses Read Wait or stops SD clock. | Continue Request to resume, or abort. "Any SD commands cannot be issued" while stopped. |
| 5 | **ADMA Error** | Error[9] | Invalid descriptor (Valid=0) at ST_FDS, or other ADMA internal error | **Transfer aborted** — ADMA2 goes to ST_STOP | Check ADMA Error Status (054h) for state. Abort & reset DAT line. Issue CMD12 if multi-block. |
| 6 | **ADMA Length Mismatch** | ADMA Error Status[2] | Block Count Enable set AND total descriptor length ≠ Block Count × Block Size, OR total length not divisible by block size | **Sub-error of ADMA Error** | Fix descriptor table or block count |
| 7 | **Data Timeout Error** | Error[4] | No data/busy within timeout | **Transfer aborted** | Error recovery |
| 8 | **Data CRC Error** | Error[5] | CRC mismatch in data | **Transfer corrupted** | Error recovery |
| 9 | **Data End Bit Error** | Error[6] | End bit of data = 0 | **Transfer corrupted** | Error recovery |
| 10 | **Current Limit Error** | Error[7] | Power supply exceeded | **Transfer may be affected** | Error recovery |
| 11 | **Auto CMD12 Error** | Error[8] | Auto CMD12 failed at end of transfer | Data completed but stop failed | Auto CMD12 error recovery (§3.10.2) |
| 12 | **Auto CMD23 Error** | Error[8] | Auto CMD23 failed before transfer | **Main command NOT issued** | Auto CMD error recovery |
| 13 | **Tuning Error** | Error[10] | Tuning circuit error during transfer | **Highest priority** — discard data | Abort, re-tune |

### ADMA2 Normal Flow

```
Command Complete
  → ADMA2 state machine runs autonomously:
      ST_FDS (fetch descriptor) → ST_CADR (advance pointer) → ST_TFR (transfer data)
      ... repeat for each descriptor ...
      [optional DMA Interrupt if Int=1 — does NOT stop transfer]
  → Transfer Complete (when End=1 descriptor completes)
```

> No driver intervention needed during normal ADMA2 transfer — unlike SDMA.

---

## Table 3 — Comparative Summary

| Event | SDMA | ADMA2 | Key Difference |
|---|---|---|---|
| **DMA Interrupt** | At every buffer boundary — **pauses transfer**, driver must reprogram address | Only if descriptor has Int=1 — **does NOT pause**, continues automatically | Fundamental behavioral difference |
| **Transfer Complete** | After all blocks | After End=1 descriptor completes | Same semantics |
| **Block Gap Event** | If Stop At Block Gap set | If Stop At Block Gap set | Same behavior, both modes |
| **ADMA Error** | N/A | Invalid descriptor or length mismatch | ADMA2-specific |
| **Data errors** (Timeout/CRC/EndBit) | Stops transfer | Stops transfer | Same in both |
| **Auto CMD errors** | Same | Same (ADMA2 required for Auto CMD23 + DMA) | Auto CMD23 needs ADMA if DMA used |
| **Current Limit** | Same | Same | Both modes |
| **Tuning Error** | Same | Same | Highest priority in both |
| **Buffer Read/Write Ready** | Not used (driver ignores) | Not used (driver ignores) | Only PIO mode |
| **Driver intervention during transfer** | **YES** — at every boundary | **NO** — fully autonomous | Core design trade-off |

---

## Key Design Insights

1. **SDMA DMA Interrupt = hard pause**: HC stops transferring until the driver writes to SDMA System Address (000h). Each boundary crossing is a mandatory interrupt point.

2. **ADMA2 DMA Interrupt = soft/informational**: ADMA2 continues processing the next descriptor automatically. The spec explicitly says it's for debugging.

3. **Transfer Complete is terminal**: "DMA Interrupt shall not be generated after Transfer Complete" (§2.2.17).

4. **Any Error Interrupt Status bit stops the transfer** in both modes.

5. **Block Gap** is orthogonal to DMA mode: it operates at the SD bus block boundary (between blocks on the wire), not at memory/descriptor boundaries. Works in both SDMA and ADMA2.

6. **Transfer Complete priority**: "Transfer Complete has higher priority than Data Timeout Error. If both bits are set to 1, execution of a command can be considered to be completed." (§2.2.17)

---

## Spec References

| Chunk ID | Section | Title | Content Used |
|---|---|---|---|
| CHUNK_1_4_0 | §1.4 | Supporting DMA | DMA overview, stop/restart via Block Gap Control |
| CHUNK_1_8_0 | §1.8 | Relationship between Interrupt Control Registers | Interrupt enable/signal/status chain |
| CHUNK_1_9_0 | §1.9 | HW Block Diagram and Timing Part | Table 1-7: Summary of Register Status for Data Transfer |
| CHUNK_1_11_0 | §1.11 | Auto CMD12 | Auto CMD12 mechanism, error table (Table 1-9) |
| CHUNK_1_13_1_0 | §1.13.1 | Block Diagram of ADMA2 | SDMA vs ADMA2 intro, scatter-gather overview |
| CHUNK_1_13_3_0 | §1.13.3 | Data Address and Data Length Requirements | Descriptor total length, block count limits |
| CHUNK_1_13_4_0 | §1.13.4 | Descriptor Table | ADMA2 attributes: Valid, End, Int, Act1/Act2 |
| CHUNK_1_13_5_0 | §1.13.5 | ADMA2 States | State machine: ST_FDS, ST_CADR, ST_TFR, ST_STOP |
| CHUNK_2_2_1_0 | §2.2.1 | SDMA System Address / Argument 2 Register (000h) | SDMA address reprogramming, boundary wait |
| CHUNK_2_2_2_0 | §2.2.2 | Block Size Register (004h) | Host SDMA Buffer Boundary field [14:12] |
| CHUNK_2_2_5_1 | §2.2.5 | Transfer Mode Register (00Ch) | Auto CMD Enable, Block Count Enable, DMA Enable |
| CHUNK_2_2_9_2 | §2.2.9 | Present State Register (024h) | Read Transfer Active, Buffer Read/Write Enable |
| CHUNK_2_2_9_3 | §2.2.9 | Present State Register (024h) | Write Transfer Active, Block Gap Event generation |
| CHUNK_2_2_9_4 | §2.2.9 | Present State Register (024h) | DAT Line Active, Command Inhibit (DAT) |
| CHUNK_2_2_10_0 | §2.2.10 | Host Control 1 Register (028h) | DMA Select field [4:3] |
| CHUNK_2_2_12_0 | §2.2.12 | Block Gap Control Register (02Ah) | Stop At Block Gap, Continue Request, Read Wait |
| CHUNK_2_2_12_1 | §2.2.12 | Block Gap Control Register (02Ah) | Restart cases, Transfer Complete before restart |
| CHUNK_2_2_15_0 | §2.2.15 | Timeout Control Register (02Eh) | Data Timeout Counter Value |
| CHUNK_2_2_16_0 | §2.2.16 | Software Reset Register (02Fh) | Reset For DAT Line clears transfer state |
| CHUNK_2_2_17_0 | §2.2.17 | Normal Interrupt Status Register (030h) | All normal interrupt bit definitions |
| CHUNK_2_2_17_2 | §2.2.17 | Normal Interrupt Status Register (030h) | DMA Interrupt, Block Gap Event, Transfer Complete |
| CHUNK_2_2_17_3 | §2.2.17 | Normal Interrupt Status Register (030h) | Transfer Complete priority over Data Timeout |
| CHUNK_2_2_18_0 | §2.2.18 | Error Interrupt Status Register (032h) | All error bit definitions |
| CHUNK_2_2_18_2 | §2.2.18 | Error Interrupt Status Register (032h) | Command error bits |
| CHUNK_2_2_19_0 | §2.2.19 | Normal Interrupt Status Enable (034h) | Status enable bits |
| CHUNK_2_2_23_0 | §2.2.23 | Auto CMD Error Status Register (03Ch) | Auto CMD error sub-fields |
| CHUNK_2_2_23_1 | §2.2.23 | Auto CMD Error Status Register (03Ch) | Error recovery timing |
| CHUNK_2_2_29_0 | §2.2.29 | ADMA Error Status Register (054h) | ADMA error states, length mismatch |
| CHUNK_2_2_29_1 | §2.2.29 | ADMA Error Status Register (054h) | ADMA Error State field encoding |
| CHUNK_2_2_30_0 | §2.2.30 | ADMA System Address Register (058h) | Descriptor pointer for ADMA2 |
| CHUNK_3_7_2_2_0 | §3.7.2.2 | Using SDMA | SDMA transfer sequence (Figure 3-14) |
| CHUNK_3_7_2_2_1 | §3.7.2.2 | Using SDMA | Step-by-step SDMA flow |
| CHUNK_3_7_2_3_1 | §3.7.2.3 | Using ADMA | Step-by-step ADMA flow |
| CHUNK_3_10_0 | §3.10 | Error Recovery | Error report/recovery overview (Figure 3-19) |
| CHUNK_3_10_1 | §3.10 | Error Recovery | Error Interrupt vs Auto CMD12 recovery classification |
| CHUNK_3_10_2_0 | §3.10.2 | Auto CMD12 Error Recovery | Recovery sequence (Figure 3-22) |
| CHUNK_3_12_4_3 | §3.12.4 | Write Transaction Wait / Continue Timing | DMA write timing details |
