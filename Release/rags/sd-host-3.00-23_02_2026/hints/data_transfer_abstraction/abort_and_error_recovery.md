# Abort Mechanism & Error Recovery (CMD12, ACMD22)

## 1. Sync Abort — Does the HC Detect CMD12 by Index?

**No. The HC is Command-Type-driven, not Command-Index-aware.**

The HC does NOT parse the Command Index field (bits [13:08]) to decide its internal behavior. The spec makes this explicit in the Transfer Mode register:

> *(Note, the Host Controller does not check command index.)*
> — §2.2.5 Transfer Mode Register

When the driver issues CMD12 manually, it writes two things to the Command Register:

| Field | Bits | Value | Purpose |
|-------|------|-------|---------|
| Command Index | [13:08] | 12 | Serialized onto CMD line for the card |
| Command Type | [07:06] | `11b` (Abort) | Triggers HC internal behavior |

The HC's response to **Command Type = Abort (11b)** is:
- **For reads**: Stop reading data into the buffer immediately
- **For writes**: Stop driving the DAT line immediately
- **Bypass Command Inhibit (DAT) check**: Per §3.7.1.1, abort commands skip step (4), going directly to step (5) — this is how the abort can be issued while DAT is busy

The Command Index bits are simply placed on the wire verbatim — the HC does not interpret them.

### When Does the HC "Know" a Specific Command Index?

Only for **hardcoded auto-commands**:
- **Auto CMD12**: HC generates the CMD12 frame itself after the last block transfer — index is hardwired in hardware
- **Auto CMD23**: Same — hardcoded

> *The Host Controller automatically issues CMD12 when the last block transfer is completed. Auto CMD12 timing synchronization with the last data block shall be done by hardware in the Host Controller.*
> — §1.11

### Sync Abort Sequence (§3.8.2)

| Step | Actor | Action |
|------|-------|--------|
| 1 | Driver | Set **Stop At Block Gap Request** = 1 in Block Gap Control register |
| 2 | HC | Stops transaction at next block gap → raises **Transfer Complete** interrupt |
| 3 | Driver | Clear Transfer Complete status (write 1 to Normal Interrupt Status) |
| 4 | Driver | Issue abort command: Command Index = 12, Command Type = `11b` |
| 4a | HC | Sees Command Type = Abort → stops buffer reads/writes, skips DAT inhibit check, serializes CMD12 onto bus |
| 5 | Driver | Set Software Reset for DAT Line + CMD Line = 1 |
| 6 | Driver | Poll until both Software Reset bits clear to 0 |

### Async Abort Sequence (§3.8.1) — for comparison

| Step | Actor | Action |
|------|-------|--------|
| 1 | Driver | Issue abort command directly (no block gap stop first) |
| 1a | HC | Same as step 4a above — Command Type = Abort triggers behavior |
| 2 | Driver | Set Software Reset for DAT Line + CMD Line = 1 |
| 3 | Driver | Poll until both resets clear |

The difference: sync abort waits for the current block to finish (cleaner), async abort interrupts mid-block (faster but messier).

---

## 2. ACMD22 (SEND_NUM_WR_BLOCKS) — Does the Card Send It Automatically?

**No. ACMD22 is a regular command the driver must explicitly issue.**

The card does NOT send anything automatically after CMD12. The card simply stores internally how many blocks were successfully programmed and waits for the host to ask.

### HC Involvement

**None.** There is no ACMD22 register, no auto-ACMD22 mechanism, no hardware support. The HC treats CMD55 + ACMD22 like any other command pair — it's just a dumb transport pipe.

### Why ACMD22 Exists

From the Physical Layer Spec (§4.3.4):

> *Systems that use Pipeline mechanism for data buffers management are, in some cases, unable to determine which block was the last to be well written to the flash if an error occurs in the middle of a Multiple Blocks Write operation. The card will respond to ACMD22 with the number of well written blocks.*

Because the card's internal write pipeline means multiple blocks can be "in flight" inside the card, neither the card's status register nor the HC can tell you exactly where the failure boundary is — only ACMD22 gives a definitive answer.

### What ACMD22 Returns

| Property | Value |
|----------|-------|
| Command type | `adtc` (addressed data transfer, card→host) |
| Argument | All stuff bits (no parameters) |
| Response | R1 + **32-bit data block** (+ CRC16) |
| Data content | Count of successfully written blocks |
| Unit | Always 512 bytes for SDHC/SDXC (WRITE_BL_PARTIAL=0) |

### Complete Error Recovery Flow

| Step | Actor | Action |
|------|-------|--------|
| 1 | HC | Raises Error Interrupt Status during multi-block write |
| 2 | Driver | Runs error recovery (§3.10.1) — checks error bits |
| 3 | Driver | Issues CMD12 abort (or Auto CMD12 error recovery per §3.10.2) |
| 4 | Driver | Software Reset for CMD + DAT lines |
| 5 | Driver | Issues CMD55 + ACMD22 (normal command path through Command Register) |
| 6 | Card | Responds with R1 + 32-bit data = number of well-written blocks |
| 7 | Driver | Reads 32-bit value from Buffer Data Port (like any single-block read) |
| 8 | Driver | Calculates: `remaining = total_intended - well_written` |
| 9 | Driver | Retries write starting from `start_address + well_written × block_size` |

> *If error occurs during memory write transfer, strongly recommend using ACMD22 and then in the following recovery sequence, retry to send remaining blocks not written.*
> — §3.10 Error Recovery

### Key Insight

The HC is completely uninvolved in ACMD22 interpretation. It:
1. Serializes CMD55 onto the bus (as instructed by driver)
2. Serializes ACMD22 onto the bus (as instructed by driver)
3. Receives 32 bits of data into Buffer Data Port
4. Raises Buffer Read Ready interrupt

The driver reads the value and decides what to do. The HC never looks at it.

---

## Spec References

| Chunk / Section | Topic |
|----------------|-------|
| §2.2.6 Command Register | Command Index [13:08] and Command Type [07:06] fields |
| §2.2.5 Transfer Mode Register | Auto CMD12 Enable, note about HC not checking command index |
| §1.11 Auto CMD12 | HC hardcoded auto-CMD12 generation |
| §3.7.1.1 | Command issuance sequence — abort skips DAT inhibit check |
| §3.8.1 Asynchronous Abort | Direct abort without block gap stop |
| §3.8.2 Synchronous Abort | Block gap stop → Transfer Complete → abort sequence |
| §3.10 Error Recovery | ACMD22 recommendation for write errors |
| §3.10.2 Auto CMD12 Error Recovery | 20-step recovery procedure |
| Physical Layer §4.3.4 | SEND_NUM_WR_BLOCKS definition and pipeline rationale |
| Physical Layer Table 4-28 | ACMD22 command definition (adtc, R1, 32-bit data) |
| Physical Layer Table 4-29 | Card state: ACMD22 from `tran` → `data` |
