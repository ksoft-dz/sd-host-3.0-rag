# SDMA Boundaries and Block Gap

> **Source**: SD Host Controller Simplified Specification Version 3.00  
> **Date**: February 2026

---

## SDMA System Address — Can Multi-Block Work Without Driver Intervention?

**Short answer**: Multi-block SDMA transfers work fine *without* driver intervention **as long as the total transfer fits within one SDMA buffer boundary**. If it crosses a boundary, the HC pauses and the driver must reprogram the address.

Here's the logic:

1. **SDMA Buffer Boundary** is configured in Block Size[14:12] — values are 4K, 8K, 16K, 32K, 64K, 128K, 256K, 512K.

2. The HC monitors the SDMA System Address as it increments during transfer. When it detects a **carry-out** at the boundary bit (e.g., bit 11→12 for 4K), it pauses and fires DMA Interrupt.

3. **Example — no boundary crossing**: You set SDMA address to 0x10000, boundary is 64K (64K aligned region = 0x10000–0x1FFFF), and you transfer 4 blocks × 512 bytes = 2K. Total fits within the 64K region → **no DMA Interrupt**, just Transfer Complete at the end. No driver intervention needed.

4. **Example — boundary crossing**: Same setup but you transfer 200 blocks × 512 = 100K. After 128 blocks (64K), the address hits 0x20000 → boundary crossed → DMA Interrupt fired, HC pauses. Driver must write the next address and restart. This happens again at 0x30000, etc.

So the real constraint is:

> **SDMA can do multi-block without intervention only if `start_address + total_bytes` stays within the same boundary-aligned region.**

In practice, with the maximum boundary of 512K, you can do up to 1024 blocks of 512 bytes without intervention. But the driver can't guarantee alignment in virtual memory systems (that's the whole reason the boundary mechanism exists — virtual memory pages may not be contiguous in physical memory).

That's exactly why ADMA2 was invented — the spec says it explicitly (§1.13):
> *"SDMA had disadvantage that DMA Interrupt generated at every page boundary disturbs CPU to reprogram the new system address. This SDMA algorithm forms a performance bottleneck by interruption at every page boundary."*

### Spec References
- CHUNK_2_2_1_0 — §2.2.1 SDMA System Address Register (000h)
- CHUNK_2_2_2_0 — §2.2.2 Block Size Register (004h), Host SDMA Buffer Boundary
- CHUNK_1_13_1_0 — §1.13.1 ADMA2 intro (SDMA bottleneck motivation)

---

## Block Size × Block Count = Total Transfer Length

**Yes.** In SDMA mode, the HC knows how much to transfer from `Block Size (004h) × Block Count (006h)`. It decrements the internal block counter after each block. When it hits 0 → Transfer Complete.

### Writing the New Address Restarts DMA

Per §2.2.1: *"When the most upper byte of this register (003h) is written, the Host Controller restarts the SDMA transfer."* So the HC resumes from the new address, continues block-by-block until the next boundary or until block count is exhausted.

### SDMA Interrupts During a Normal (No-Error) Transfer

During a perfectly normal SDMA transfer, the **only** interrupts are:

| Interrupt | Condition |
|---|---|
| **DMA Interrupt** | Address crossed buffer boundary |
| **Transfer Complete** | All blocks transferred (block count reached 0) |

That's it. No per-block interrupt. The HC silently fetches/sends blocks one by one between boundaries. If the entire transfer fits in one boundary region → you get **only** Transfer Complete, zero DMA Interrupts.

### Spec References
- CHUNK_2_2_1_0 — §2.2.1 SDMA System Address (restart on upper byte write)
- CHUNK_2_2_17_2 — §2.2.17 DMA Interrupt: "shall not be generated after Transfer Complete"
- CHUNK_3_7_2_2_0 — §3.7.2.2 SDMA transfer sequence (Figure 3-14)
- CHUNK_3_7_2_2_1 — §3.7.2.2 Step-by-step flow

---

## Block Gap — What It Is and How It Stops SDMA

Block Gap is a **completely separate, orthogonal mechanism** from DMA boundaries.

### What is a "block gap"?

On the SD bus, when you do a multi-block transfer, there's a tiny pause between blocks — that's the "block gap." It's the moment on the wire between the CRC of one block and the start of the next block. Every multi-block transfer has these gaps, regardless of DMA mode (even PIO has them).

### How does it work?

1. The driver sets **Stop At Block Gap Request** (Block Gap Control[0] = 1) *during* an ongoing transfer
2. At the next block gap on the SD bus, the HC:
   - **Read**: Stops reading from the card (using Read Wait or clock stop)
   - **Write**: Finishes the current block's CRC status, then stops
3. The HC fires **Block Gap Event** interrupt (Normal[2])
4. The transfer is now **paused at the SD bus level**

### How to resume:

- Set **Continue Request** (Block Gap Control[1] = 1) → transfer resumes
- Or issue an **Abort** (CMD12) → transfer ends

### The key difference from DMA boundary:

| Aspect | DMA Boundary (SDMA only) | Block Gap (any mode) |
|---|---|---|
| Where it pauses | At a **memory address** boundary | At a **SD bus block** boundary |
| Trigger | Automatic — HC detects address carry-out | Manual — driver sets Stop At Block Gap Request |
| Purpose | Virtual memory page management | Suspend/resume, debugging, giving CPU time |
| Interrupt | DMA Interrupt (Normal[3]) | Block Gap Event (Normal[2]) |
| How to resume | Write new address to SDMA System Address | Set Continue Request |
| Applies to | SDMA only | SDMA, ADMA2, and PIO |

### Example — both mechanisms at play in SDMA:

```
Block 1  ──► Block 2  ──► Block 3  ──► Block 4  ──► Block 5  ──► Block 6
                              │                          │
                         DMA boundary hit           Driver set Stop At
                         → DMA Interrupt             Block Gap Request
                         → HC pauses memory side     → Block Gap Event
                         → driver writes new addr    → HC pauses SD bus side
                         → resumes                   → driver sets Continue
                                                     → resumes
```

They can even happen at the **same block** — the HC would handle both. But they're independent mechanisms with independent status bits.

**One important nuance**: After Block Gap stops the transfer and the driver wants to end it (not resume), the spec says the driver should wait for **Transfer Complete** — because when Stop At Block Gap is set and data is flushed, Transfer Complete is generated to signal the partial-but-intentional end.

### Full picture of "what can pause/stop an SDMA transfer":

| Event | Automatic? | Resumes how? |
|---|---|---|
| DMA Boundary | Yes (auto at boundary) | Driver writes new SDMA address |
| Block Gap | No (driver must request it) | Driver sets Continue Request |
| Transfer Complete | Yes (block count exhausted) | N/A — transfer is done |
| Any Error | Yes (HC detected error) | Error recovery + reset |

### Spec References
- CHUNK_2_2_12_0 — §2.2.12 Block Gap Control Register (02Ah)
- CHUNK_2_2_12_1 — §2.2.12 Block Gap Control Register — restart cases
- CHUNK_2_2_17_2 — §2.2.17 Block Gap Event bit definition
- CHUNK_2_2_9_3 — §2.2.9 Write Transfer Active (Block Gap Event generation)
- CHUNK_2_2_9_4 — §2.2.9 DAT Line Active (read block gap)
- CHUNK_1_4_0 — §1.4 Supporting DMA (stop/restart via Block Gap)

---

## CMD12 at Block Gap — What Happens to Remaining Blocks?

### Short answer

**Yes**, when CMD12 is issued after stopping at block gap, the HC treats it as a **permanent stop**. Remaining blocks are abandoned. The SD card accepts whatever blocks were validly received as committed data.

### HC Side — Two Abort Mechanisms

**Synchronous Abort** (the "stop at block gap then CMD12" case — §3.8.2):

1. Driver sets **Stop At Block Gap Request** = 1
2. HC finishes current block, stops at gap
3. HC generates **Transfer Complete** (partial completion counts)  
   *"when data has stopped at the block gap and completed the data transfer by setting the Stop At Block Gap Request"* (§2.2.17)
4. Driver clears Transfer Complete status
5. Driver issues **CMD12** (Command Type = `11b` = Abort)
6. HC: *"stop reads to the buffer"* (read) / *"stop driving the DAT line"* (write) (§2.2.6)
7. Driver performs **Software Reset for DAT + CMD lines**
8. Done — remaining block count is irrelevant

**Asynchronous Abort** (CMD12 without block gap stop — §3.8.1):

1. Driver issues CMD12 immediately
2. HC stops buffer operations
3. Driver resets DAT + CMD lines
4. Done — more abrupt, no Transfer Complete guaranteed before CMD12

### SD Card Side — Card Accepts Partial Transfer as Valid

CMD12 (`STOP_TRANSMISSION`) is the **standard, well-defined** way to end a multi-block operation early on the SD bus protocol. The card:

- **Read**: Stops transmitting, returns to Standby state. Data already in host buffer is valid.
- **Write**: Transitions from Receive-data → Programming state. All CRC-confirmed blocks are committed to flash. Card asserts busy on DAT0 until flush complete (max 250ms, 500ms for SDXC).

Per SD Physical Layer Spec v3.01, §4.3.4:
> *"If a block write operation is stopped and the block length and CRC of the last block are valid, the data will be programmed."*

**This is NOT an error condition** — it is normal protocol.

### Detailed Flows

#### Synchronous Abort — Read:
```
1. Driver: Stop At Block Gap Request = 1
2. HC: finishes current block, asserts Read Wait (or stops clock)
3. HC: clears DAT Line Active → Block Gap Event fires
4. HC: clears Read Transfer Active → Transfer Complete fires
5. Driver: clears Transfer Complete, issues CMD12 (Abort type)
6. CMD12 on SD bus → card stops transmitting, returns to Standby
7. Driver: Software Reset for DAT + CMD lines
8. Done — remaining blocks abandoned
```

#### Synchronous Abort — Write:
```
1. Driver: writes all current block data to Buffer Data Port
2. Driver: Stop At Block Gap Request = 1
3. HC: sends current block, waits for CRC status + busy release
4. HC: clears Write Transfer Active → Block Gap Event fires
5. HC: clears DAT Line Active → Transfer Complete fires
6. Driver: clears Transfer Complete, issues CMD12 (Abort type)
7. CMD12 on bus → card enters Programming State, flushes buffer to flash
8. Card: busy on DAT0 until all buffered blocks committed
9. Driver: Software Reset for DAT + CMD lines
10. Done
```

### Abort vs. Suspend/Resume

| Aspect | Abort (CMD12) | Suspend/Resume |
|---|---|---|
| Purpose | **Terminate** permanently | **Pause** then continue later |
| Remaining blocks | Abandoned forever | Resumed later |
| Card state after | Returns to Standby | Stays in suspended transfer state |
| Transfer Complete | Generated at gap (sync abort) | Generated at gap, cleared on resume |

### Spec References
- CHUNK_2_2_6_0 — §2.2.6 Command Register: Abort command type behavior
- CHUNK_2_2_12_0 — §2.2.12 Block Gap Control Register
- CHUNK_2_2_17_2 — §2.2.17 Transfer Complete at block gap
- CHUNK_2_2_17_3 — §2.2.17 Transfer Complete priority
- CHUNK_3_8_1_0 — §3.8.1 Asynchronous Abort
- CHUNK_3_8_2_0 — §3.8.2 Synchronous Abort at block gap
- CHUNK_3_12_3_0 — §3.12.3 Read Transaction Wait/Continue Timing
- CHUNK_3_12_4_0 — §3.12.4 Write Transaction Wait/Continue Timing
- SD Physical Layer Spec v3.01, §4.3.4 — Data Write (block gap + CMD12 behavior)

---

## Physical SD Card — Write Data Flow

> **Source**: SD Physical Layer Simplified Specification v3.01, May 2010

### Core Question: Does the card write to flash as data arrives, or buffer everything first?

**The card writes to flash incrementally as blocks arrive.** It uses an internal write buffer to pipeline reception and programming.

### The Write Pipeline

```
Host sends block N on DAT lines
  → Card receives block, checks CRC16
  → Card sends CRC status token on DAT0 (positive/negative/write error)
  → If CRC OK: block goes into internal write buffer
  → Card begins programming buffered data to flash
  → If buffer has space: DAT0 goes high (not busy) → host can send block N+1
  → If buffer is full: DAT0 stays low (busy) until space frees up
  → [repeat for each block]
  → CMD12 to stop → card enters Programming State
  → Card flushes remaining buffer to flash
  → Busy on DAT0 until done (max 250ms / 500ms for SDXC)
```

### Key Spec Quotes

**Buffering and busy** (Physical Layer Spec, p.28–31):
> *"The card may provide buffering for block write. This means that the next block can be sent to the card while the previous is being programmed."*

> *"After receiving a block of data and completing the CRC check, the card will begin writing and hold the DAT0 line low **if its write buffer is full** and unable to accept new data."*

> *"If all write buffers are full, and as long as the card is in Programming State, the DAT0 line will be kept low (BUSY)."*

**What busy means**: The card is **actually programming flash**. It continues even if the host stops the clock:
> *"The host is allowed to shut down the clock of a 'busy' card. The card will complete the programming operation regardless of the host clock."*

**Pipeline model acknowledged** (Physical Layer Spec, re ACMD22):
> *"Systems that use Pipeline mechanism for data buffers management are, in some cases, unable to determine which block was the last to be well written to the flash if an error occurs in the middle of a Multiple Blocks Write operation. The card will respond to ACMD22 with the number of well written blocks."*

This is why ACMD22 (`SEND_NUM_WR_BLOCKS`) exists — because the host can't know exactly which buffered blocks were committed to flash when an error occurs mid-stream.

### CMD12 Stops Write — What Happens to Buffered Data?

> *"If a block write operation is stopped and the block length and CRC of the last block are valid, the data will be programmed."*

When CMD12 arrives:
1. Card transitions from **Receive-data** → **Programming** state
2. All validly received + CRC-checked blocks in the buffer are committed to flash
3. Card signals busy on DAT0 until flush complete
4. Pre-erased but unreceived areas (from CMD23) contain **undefined data**

### Summary

| Aspect | Behavior |
|---|---|
| When does flash programming start? | As soon as CRC-confirmed data enters the write buffer |
| Does the card buffer? | **Yes** — "may provide buffering" (most real cards do) |
| Next block while programming? | **Yes** — if buffer has space, DAT0 goes high, host sends next block |
| What does busy (DAT0 low) mean? | Write buffer full, card programming flash, cannot accept new data |
| CMD12 mid-transfer? | Buffered data committed to flash, remaining blocks abandoned |
| How to check blocks written? | ACMD22 (`SEND_NUM_WR_BLOCKS`) |

### Spec References
- SD Physical Layer Spec v3.01, §4.3.4 (p.28–31) — Data Write, busy, buffering
- SD Physical Layer Spec v3.01, §4.4 (p.53) — Clock control during busy
- SD Physical Layer Spec v3.01, §4.6.1 (p.69) — State transitions, CMD12 from rcv→prg
- SD Physical Layer Spec v3.01, §4.7.2 (p.76) — Card Status: READY_FOR_DATA
- SD Physical Layer Spec v3.01, §4.3.4 (p.90) — CMD23 + partial write: undefined unwritten areas
