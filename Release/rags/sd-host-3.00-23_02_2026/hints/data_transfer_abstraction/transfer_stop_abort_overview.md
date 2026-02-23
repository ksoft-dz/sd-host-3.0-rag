# Events That Stop/Abort an Ongoing Transfer — Quick Overview

## A. Normal Completion Events

| Event | HC Behavior | SD Card Behavior | Driver Handling |
|-------|------------|-------------------|-----------------|
| **Transfer Complete** (all modes) | Finishes last block, sets Transfer Complete in 030h[1], stops DMA/buffer engine | Sends/receives last block, returns to `tran` state | Reads status, clears interrupt, done |
| **Auto CMD12 Complete** (multi-block) | HC hardcodes CMD12 after last block, stores response at 01Ch | Receives CMD12, flushes pipeline, → `tran` | Nothing extra — HC handled it |

## B. DMA Boundary Events (SDMA only)

| Event | HC Behavior | SD Card Behavior | Driver Handling |
|-------|------------|-------------------|-----------------|
| **DMA Interrupt** (SDMA boundary) | Detects carry-out at boundary bit, pauses DMA, sets 030h[3] | **Unaware** — bus is paused between blocks | Reprograms SDMA System Address (000h), resumes |

## C. ADMA2-Specific Events

| Event | HC Behavior | SD Card Behavior | Driver Handling |
|-------|------------|-------------------|-----------------|
| **ADMA Interrupt** (Int=1 in descriptor) | Sets 030h[3], does **NOT** pause — continues to next descriptor (verified, see §H below) | **Unaware** — transfer continues | Informational/debug only — can update descriptor table ahead of HC |
| **ADMA Error** (invalid descriptor) | Stops, sets 032h[9], logs ADMA Error Status (054h) + address (058h) | Bus stalls — card may timeout | Read 054h for state+LengthMismatch, abort (CMD12), reset DAT+CMD |

## D. Block Gap Event (all modes)

| Event | HC Behavior | SD Card Behavior | Driver Handling |
|-------|------------|-------------------|-----------------|
| **Stop At Block Gap** (driver-initiated) | Finishes current block, pauses, sets 030h[2] Block Gap Event | Waiting — stays in `data` state, no timeout | Either: Continue Request (resume) or CMD12 (abort) |

## E. Error Events (all modes)

| Event | HC Behavior | SD Card Behavior | Driver Handling |
|-------|------------|-------------------|-----------------|
| **Command CRC Error** | Sets 032h[1], stops | Command was corrupted on wire | Retry command (§3.10.1) |
| **Command Timeout** | Sets 032h[0], stops | Never saw the command / no response | Check card presence, retry or abort |
| **Command Index Error** | Sets 032h[3], stops | Card sent wrong response index | Retry command |
| **Data CRC Error** | Sets 032h[5], transfer stops | Read: sent bad data / Write: card sent neg CRC status | Abort (CMD12), reset DAT+CMD. For writes: ACMD22 → retry remaining |
| **Data Timeout** | Sets 032h[4], transfer stops | Read: card stalled / Write: card busy too long | Abort (CMD12), reset DAT+CMD |
| **Data End Bit Error** | Sets 032h[6], transfer stops | Missing end bit on DAT line | Abort (CMD12), reset DAT+CMD |
| **Auto CMD12 Error** | Sets 032h[8], details in Auto CMD Error Status (03Ch) | Card may/may not have received CMD12 | Read 03Ch, issue CMD12 manually if needed, reset, ACMD22 for writes |
| **Current Limit Error** | Sets 032h[7] | Card drawing too much current | Power cycle card, re-init |

## F. PIO-Specific Stalls (not errors, but pauses)

| Event | HC Behavior | SD Card Behavior | Driver Handling |
|-------|------------|-------------------|-----------------|
| **Buffer Read Ready** | One block in buffer, sets 030h[5], pauses until read | Card waiting — bus paused between blocks | Read block from Buffer Data Port (020h), HC auto-resumes |
| **Buffer Write Ready** | Buffer space available, sets 030h[4] | Card waiting for next block | Write block to Buffer Data Port (020h), HC sends it |

## G. Which Events Apply to Which Mode

| Event | PIO | SDMA | ADMA2 |
|-------|-----|------|-------|
| Transfer Complete | x | x | x |
| Buffer Read/Write Ready | x | - | - |
| DMA Interrupt (boundary) | - | x | - |
| ADMA Interrupt (Int=1) | - | - | x |
| ADMA Error | - | - | x |
| Block Gap Event | x | x | x |
| All Error Interrupts | x | x | x |
| Auto CMD12 Error | x | x | x |
| Current Limit Error | x | x | x |

## H. Verified: ADMA2 Int=1 Does NOT Pause the Transfer

The `Int` field in an ADMA2 descriptor generates a DMA Interrupt but does **not** stop or pause the transfer. Evidence from spec:

1. **§2.2.17 Normal Interrupt Status, bit D03 (DMA Interrupt)**:
   > *"In case of ADMA, by setting Int field in the descriptor table, Host Controller generates this interrupt. Suppose that it is used for debugging."*

2. **§1.13.5 ADMA2 State Machine**: The `Int` field does **not** appear in any state transition condition. The only transitions to ST_STOP are `End=1` or `STOP` (Block Gap). Int is completely absent from the state machine.

3. **§3.7.2.3 ADMA2 Transfer Flow**: Says "Wait for Transfer Complete Interrupt and ADMA Error Interrupt" — no mention of handling DMA Interrupt at all. Contrast with SDMA (§3.7.2.2) which explicitly handles DMA Interrupt by reprogramming the system address.

4. **§1.13 ADMA2 Design Rationale**:
   > *"SDMA had disadvantage that DMA Interrupt generated at every page boundary disturbs CPU... ADMA adopts scatter gather DMA algorithm... It enables ADMA to operate without interrupting the Host Driver."*

### Summary of ADMA2 Stop Mechanisms

| Mechanism | Stops Transfer? | Details |
|-----------|----------------|---------|
| Int=1 in descriptor | **NO** | Generates 030h[3], transfer continues. Debug use. |
| End=1 in descriptor | **YES** | Transitions to ST_STOP, generates Transfer Complete |
| Valid=0 in descriptor | **YES** | Generates ADMA Error Interrupt, stops |
| Stop At Block Gap Request | **YES** | Separate mechanism via Block Gap Control register |
| Any Error Interrupt | **YES** | Transfer stops on any error |
