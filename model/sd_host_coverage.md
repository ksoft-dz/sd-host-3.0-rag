# xxx Model ↔ SD Host Controller 3.00 Coverage

This document maps features from `xxx.md` to SD Host Controller 3.00 specification.

---

## Feature Coverage Summary

| SD Host 3.00 Feature | xxx.md Source | Coverage | Spec Reference |
|----------------------|---------------|----------|----------------|
| **Command Generation** | | | |
| SD Command/Response handling | Lines 52-55 (Registers: Argument, Command, Response) | ✅ | §1.5, §2.2.4-2.2.7 (p25-31) |
| Block Size/Count configuration | Lines 50-51 (Registers 004h, 006h) | ✅ | §2.2.2-2.2.3 (p22-25) |
| Auto CMD12/CMD23 | Line 71 (Register 03Ch: Auto CMD12 Error Status) | ✅ | §1.11, §2.2.23 (p12, p68) |
| | | | |
| **Data Transfer** | | | |
| PIO Mode (Buffer Data Port) | Line 9: `programmed IO method...Buffer data port register`; Line 56 (Register 020h) | ✅ | §1.7, §2.2.8 (p5, p32) |
| SDMA | Line 9: `supports both SDMA and ADMA2`; Line 49 (Register 000h) | ✅ | §1.4, §2.2.1, §3.7.2.2 (p3, p21, p113) |
| ADMA2 | Line 9: `ADMA2 is enabled by user using programming bit`; Lines 78-79 (Registers 054h, 058h) | ✅ | §1.13, §2.2.29-2.2.30 (p14, p83-85) |
| | | | |
| **Bus Width** | | | |
| 1-bit / 4-bit SD mode | Line 34: `Transfers the data in 1 bit and 4 bit SD modes`; Line 58 (Host Control 1) | ✅ | §3.4, §2.2.10 (p98, p40) |
| SPI mode | Line 34: `and SPI mode` | ❌ Not in spec | — |
| | | | |
| **Speed Modes** | | | |
| Default Speed | Line 35: `Default speed modes` | ✅ | §3.9 (p119) |
| High Speed (50MHz) | Line 35: `High and Default speed modes`; Line 36: `25 Mbytes per second` | ✅ | §3.9 (p119) |
| UHS-I Modes (SDR50/104/DDR50) | Line 72 (Host Control 2 register present) | ⚠️ Register exists, not in features | §2.2.24 (p35) |
| | | | |
| **Clock Control** | | | |
| SDCLK frequency control | Line 33: `Host clock rate variable between 0 and 50 Mhz`; Line 62 (Register 02Ch) | ✅ | §1.12, §2.2.14, §3.2 (p13, p46, p94) |
| Clock gating on FIFO error | Line 45: `Handle the FIFO overrun and underrun condition by stopping eMMC card clock` | ✅ | §1.12 (p13) |
| Sampling Clock Tuning | Line 72 (Host Control 2 has Execute Tuning field) | ⚠️ Register exists | §1.16, §2.2.24 (p18, p35) |
| | | | |
| **Power Control** | | | |
| Bus Power / Voltage Select | Line 59 (Register 029h: Power Control) | ✅ | §3.3, §2.2.11 (p96, p42) |
| 1.8V Signaling | Line 72 (Host Control 2 has 1.8V Signaling Enable) | ⚠️ Register exists | §3.6.1, §2.2.24 (p104, p35) |
| | | | |
| **Interrupt System** | | | |
| Normal/Error Interrupts | Lines 65-70 (All 6 interrupt registers present) | ✅ | §1.8, §2.2.17-2.2.22 (p8, p52-66) |
| | | | |
| **SDIO Features** | | | |
| Read Wait / Block Gap | Line 39: `Performs Read Wait control`; Line 60 (Register 02Ah) | ✅ | §3.12, §2.2.12 (p130, p43) |
| Suspend/Resume | Line 41: `Supports Read Wait control, Suspend/Resume operation` | ✅ | §3.12 (p130) |
| Card Interrupt | Line 65 (Normal Interrupt Status has Card Interrupt bit) | ✅ | §2.2.17 (p52) |
| | | | |
| **Card Management** | | | |
| Card Detection | Line 57 (Present State Register); Line 65 (Card Insertion/Removal interrupts) | ✅ | §3.1, §2.2.9 (p92, p33) |
| Write Protection | Line 57 (Present State Register has WP bit) | ✅ | §2.2.9 (p33) |
| Wakeup Control | Line 61 (Register 02Bh) | ✅ | §3.11, §2.2.13 (p128, p45) |
| | | | |
| **Error Handling & Reset** | | | |
| Error Detection (CRC, Timeout) | Line 7: `checking for transaction format correctness`; Line 66 (Error Int Status) | ✅ | §3.10, §2.2.18 (p121, p57) |
| Software Reset | Line 64 (Register 02Fh) | ✅ | §2.2.16 (p50) |
| Timeout Control | Line 63 (Register 02Eh) | ✅ | §3.5, §2.2.15 (p99, p49) |
| | | | |
| **Configuration & Capabilities** | | | |
| Capabilities reporting | Lines 73-76 (Registers 040h-04Ch) | ✅ | §2.2.25-2.2.26 (p74, p80) |
| Preset Values | Line 80 (Register 060h) | ✅ | §2.2.31 (p86) |
| Force Event (Testing) | Lines 77-78 (Registers 050h, 052h) | ✅ | §1.14, §2.2.27-2.2.28 (p18, p51-63) |
| Host Controller Version | Line 83 (Register 0FEh) | ✅ | §2.2.34 (p91) |
| | | | |
| **Multi-Slot / Shared Bus** | | | |
| Slot Interrupt Status | Line 82 (Register 0FCh) | ✅ | §2.2.33 (p91) |
| Shared Bus Control | — | ❌ Missing (0E0h not in xxx.md) | §2.2.32, Appendix D (p88, p146) |
| | | | |
| **MMC 4.51 Features (xxx model only)** | | | |
| MMC Compliance | Line 15: `MMC specification version 4.51` | ✅ xxx | (Not in SD Host 3.00) |
| 8-bit Data Bus | Line 28: `8 bit parallel data lines`; Line 30: `1 bit, 4 bit and 8 bit modes` | ✅ xxx | (Not in SD Host 3.00) |
| MMC SDR Mode (50 MB/s) | Line 28: `50 Mbytes per second...mmc8 bit SDR mode` | ✅ xxx | (Not in SD Host 3.00) |
| MMC DDR Mode (100 MB/s) | Line 29: `100 MBytes per second...mmc8 bit DDR mode` | ✅ xxx | (Not in SD Host 3.00) |
| eMMC Clock (50 MHz) | Line 27: `EMMC card clock frequency is 50 Mhz` | ✅ xxx | (Not in SD Host 3.00) |
| MMC Plus / MMC Mobile | Line 32: `Supports MMC plus and MMC mobile` | ✅ xxx | (Not in SD Host 3.00) |
| SPI Mode | Lines 30, 34: `SPI mode` | ✅ xxx | (Not in SD Host 3.00) |
| | | | |
| **System Interface (xxx model)** | | | |
| Host Bus Clock (100 MHz) | Line 24: `System/Host interface clock frequency is 100 Mhz` | ✅ xxx | (Implementation-specific) |

---

## Feature Descriptions (from SD Host 3.00 Spec)

### Command Generation (§1.5)
The Host Controller generates SD commands by programming registers from offset 000h to 00Fh sequentially. Writing to the upper byte of the Command Register (00Fh) triggers issuance of the SD command. The Block Size, Block Count, and Transfer Mode registers are write-protected while Command Inhibit (DAT) is set.

- **SD Command/Response handling**: Host Driver programs Argument and Command registers; response is captured in Response Register (010h-01Fh).
- **Block Size/Count configuration**: Defines transfer size per block and number of blocks for data transfers.
- **Auto CMD12/CMD23**: Automatically issues CMD12 (stop) or CMD23 (set block count) after multi-block transfers, eliminating software intervention.

### Data Transfer (§1.4, §1.7, §1.13)
Three methods for transferring data between host memory and SD card:

- **PIO Mode**: CPU reads/writes data through the 32-bit Buffer Data Port register (020h). Simple but CPU-intensive.
- **SDMA (Single Operation DMA)**: One SD command per DMA operation. Interrupts at every page boundary to reprogram system address. Supported since v1.00.
- **ADMA2 (Advanced DMA)**: Scatter-gather DMA using descriptor tables. No CPU interruption needed; supports 32/64-bit addressing. Recommended for v3.00.

### Bus Width (§3.4)
SD cards support 1-bit (DAT0 only) or 4-bit (DAT0-DAT3) data bus:

- **1-bit / 4-bit SD mode**: Changed via ACMD6 for memory cards or CCCR register for SDIO. Host Control 1 register (028h) Data Transfer Width bit selects the mode.
- **SPI mode**: Legacy serial interface — **not part of SD Host Controller 3.00 specification**.

### Speed Modes (§3.9)
Bus speed modes determine maximum clock frequency and data rate:

- **Default Speed**: Up to 25 MHz clock, 12.5 MB/s (4-bit).
- **High Speed**: Up to 50 MHz clock, 25 MB/s (4-bit). Enabled via CMD6 switch command.
- **UHS-I Modes**: SDR50 (100 MB/s), SDR104 (208 MB/s), DDR50 (50 MB/s). Require 1.8V signaling and tuning.

### Clock Control (§1.12, §1.16)
SDCLK generation and frequency control:

- **SDCLK frequency control**: Clock Control Register (02Ch) sets frequency via divider. Clock must maintain 45-55% duty cycle.
- **Clock gating on FIFO error**: Clock is stopped immediately when card state changes or on FIFO errors to prevent data corruption.
- **Sampling Clock Tuning**: Required for UHS-I SDR104/SDR50 modes. Host Controller adjusts sampling point to compensate for signal timing variations.

### Power Control (§3.3, §3.6.1)
SD bus voltage and power management:

- **Bus Power / Voltage Select**: Power Control Register (029h) enables bus power and selects voltage (3.3V, 3.0V, or 1.8V).
- **1.8V Signaling**: Required for UHS-I modes. Signal Voltage Switch procedure changes from 3.3V to 1.8V signaling.

### Interrupt System (§1.8)
Two-level interrupt architecture with status, enable, and signal registers:

- **Normal Interrupts**: Command Complete, Transfer Complete, Buffer Ready, Card Insertion/Removal, DMA, Block Gap, Card Interrupt.
- **Error Interrupts**: Command/Data Timeout, CRC, End Bit, Index errors, ADMA errors.
- Interrupts are cleared by writing 1 to the status bit (RW1C). Card Interrupt clears when the card de-asserts.

### SDIO Features (§3.12)
Features specific to SDIO (I/O) cards:

- **Read Wait / Block Gap**: Pauses data transfer at block boundaries. Used for Suspend/Resume and multi-function card arbitration.
- **Suspend/Resume**: Allows interrupting one card operation to service another, then resuming. Requires Read Wait support.
- **Card Interrupt**: SDIO cards can assert interrupt to request host attention (e.g., data ready, event occurred).

### Card Management (§3.1, §3.11)
Card presence and state management:

- **Card Detection**: Monitors SDCD# pin for card insertion/removal. State machine handles debouncing. Generates interrupts on state change.
- **Write Protection**: Reads physical write-protect switch state via SDWP# pin (Present State Register bit 19). Read-only status.
- **Wakeup Control**: Enables system wakeup from sleep on Card Interrupt, Card Insertion, or Card Removal events.

### Error Handling & Reset (§3.10)
Error detection and recovery mechanisms:

- **Error Detection**: CRC errors, timeout errors, end bit errors detected and reported in Error Interrupt Status Register.
- **Software Reset**: Three reset types — Reset All (full reset), Reset CMD Line, Reset DAT Line. Used for error recovery.
- **Timeout Control**: Data Timeout Counter Value (02Eh) sets maximum wait time for data transfers (TMCLK × 2^(13+value)).

### Configuration & Capabilities (§2.2.25-2.2.31)
Hardware capabilities and configuration:

- **Capabilities reporting**: Read-only registers (040h-04Ch) report supported features: voltages, speeds, DMA modes, max current.
- **Preset Values**: Pre-configured clock divider and driver strength values for each speed mode (060h-06Fh).
- **Force Event**: Test registers (050h, 052h) to artificially trigger error conditions for driver testing.
- **Host Controller Version**: Reports specification version compliance (0FEh).

### Multi-Slot / Shared Bus (§1.3, Appendix D)
Support for multiple cards:

- **Multiple Slot Support**: Each slot has independent register set. Common registers at 0F0h-0FFh accessible from any slot.
- **Slot Interrupt Status**: Aggregates interrupt status from all slots into single register (0FCh).
- **Shared Bus Control**: Allows multiple devices on shared SD bus, selected by individual clock pins. Reduces power by stopping clocks to unselected devices.

### MMC 4.51 Features (xxx model only — NOT in SD Host 3.00)
These features are part of the xxx model's MMC 4.51 compliance, not SD Host Controller 3.00:

- **8-bit Data Bus**: Extends data bus from 4-bit (SD) to 8-bit for doubled throughput. Uses DAT0-DAT7 lines.
- **MMC SDR Mode**: Single Data Rate mode at 50 MHz clock, achieving 50 MB/s with 8-bit bus.
- **MMC DDR Mode**: Double Data Rate mode samples data on both clock edges, achieving 100 MB/s with 8-bit bus at 50 MHz.
- **eMMC Clock**: Dedicated eMMC clock up to 50 MHz for embedded MMC devices.
- **MMC Plus / MMC Mobile**: Support for high-capacity MMC cards and mobile-optimized MMC variants.
- **SPI Mode**: Legacy Serial Peripheral Interface mode for simple 1-bit serial communication (also not in SD Host 3.00).

### System Interface (xxx model specific)
Implementation-specific system bus parameters:

- **Host Bus Clock**: System/host interface operates at up to 100 MHz for high-speed register access and DMA.

---

## Feature Quick Reference (Excel-friendly)

| Category | Feature | One-Line Description |
|----------|---------|---------------------|
| Command Generation | SD Command/Response | Programs Argument/Command registers to issue SD commands; captures response in Response Register |
| Command Generation | Block Size/Count | Configures data block size (004h) and number of blocks (006h) for transfers |
| Command Generation | Auto CMD12/CMD23 | Automatically issues stop (CMD12) or block count (CMD23) command after multi-block transfers |
| Data Transfer | PIO Mode | CPU transfers data via 32-bit Buffer Data Port register (020h); simple but CPU-intensive |
| Data Transfer | SDMA | Single-operation DMA; interrupts at page boundaries to reprogram address; one command per operation |
| Data Transfer | ADMA2 | Scatter-gather DMA with descriptor tables; no CPU interruption; supports 32/64-bit addressing |
| Bus Width | 1-bit / 4-bit mode | Selects DAT0-only (1-bit) or DAT0-DAT3 (4-bit) bus via Host Control 1 register bit |
| Bus Width | SPI mode | Legacy serial interface — NOT part of SD Host Controller 3.00 specification |
| Speed Modes | Default Speed | Up to 25 MHz clock, 12.5 MB/s throughput in 4-bit mode |
| Speed Modes | High Speed | Up to 50 MHz clock, 25 MB/s throughput; enabled via CMD6 switch command |
| Speed Modes | UHS-I Modes | SDR50/SDR104/DDR50 modes; require 1.8V signaling and sampling clock tuning |
| Clock Control | SDCLK frequency | Clock Control Register (02Ch) sets frequency via programmable divider; 45-55% duty cycle |
| Clock Control | Clock gating | Stops clock on FIFO error or card state change to prevent data corruption |
| Clock Control | Sampling Tuning | Adjusts sampling point for UHS-I modes to compensate for signal timing variations |
| Power Control | Bus Power/Voltage | Power Control Register (029h) enables power and selects 3.3V/3.0V/1.8V |
| Power Control | 1.8V Signaling | Voltage switch procedure from 3.3V to 1.8V required for UHS-I modes |
| Interrupt System | Normal/Error Int | Two-level architecture; cleared by writing 1 (RW1C); 6 registers total |
| SDIO Features | Read Wait/Block Gap | Pauses data transfer at block boundaries for suspend/resume or function arbitration |
| SDIO Features | Suspend/Resume | Interrupts one operation to service another, then resumes; requires Read Wait |
| SDIO Features | Card Interrupt | SDIO card asserts interrupt to request host attention; cleared when card de-asserts |
| Card Management | Card Detection | Monitors SDCD# pin with debouncing state machine; generates insert/remove interrupts |
| Card Management | Write Protection | Reads physical WP switch state via SDWP# pin; read-only status in Present State reg |
| Card Management | Wakeup Control | Enables system wakeup from sleep on card interrupt, insertion, or removal |
| Error Handling | Error Detection | Detects CRC, timeout, end bit, index errors; reported in Error Interrupt Status reg |
| Error Handling | Software Reset | Three types: Reset All, Reset CMD Line, Reset DAT Line; used for error recovery |
| Error Handling | Timeout Control | Sets max wait time for data via counter value; timeout = TMCLK × 2^(13+value) |
| Config/Capabilities | Capabilities | Read-only registers report supported voltages, speeds, DMA modes, max current |
| Config/Capabilities | Preset Values | Pre-configured divider and driver strength for each speed mode (060h-06Fh) |
| Config/Capabilities | Force Event | Test registers to artificially trigger errors for driver testing (050h, 052h) |
| Config/Capabilities | HC Version | Reports spec version compliance in Host Controller Version register (0FEh) |
| Multi-Slot | Slot Int Status | Aggregates interrupt status from all slots into single register (0FCh) |
| Multi-Slot | Shared Bus Control | Multiple devices on shared bus selected by individual clocks; power saving feature |
| MMC 4.51 (xxx only) | MMC Compliance | xxx model compliant with MMC 4.51 spec (NOT in SD Host 3.00) |
| MMC 4.51 (xxx only) | 8-bit Data Bus | 8-bit parallel data mode for higher throughput (NOT in SD Host 3.00) |
| MMC 4.51 (xxx only) | MMC SDR Mode | 8-bit SDR mode at 50 MB/s using 50 MHz clock (NOT in SD Host 3.00) |
| MMC 4.51 (xxx only) | MMC DDR Mode | 8-bit DDR mode at 100 MB/s double data rate (NOT in SD Host 3.00) |
| MMC 4.51 (xxx only) | eMMC Clock 50 MHz | eMMC card clock frequency up to 50 MHz (NOT in SD Host 3.00) |
| MMC 4.51 (xxx only) | MMC Plus/Mobile | Support for MMC plus and MMC mobile card types (NOT in SD Host 3.00) |
| MMC 4.51 (xxx only) | SPI Mode | Legacy serial peripheral interface mode (NOT in SD Host 3.00) |
| System (xxx only) | Host Bus 100 MHz | System/host interface clock frequency max 100 MHz (Implementation-specific) |

---

## Lines NOT in SD Host 3.00

| Line # | Raw Text | Category |
|--------|----------|----------|
| 15 | `MMC specification version 4.51` | MMC spec |
| 27-31 | MMC card interface section (8-bit, DDR, MMC plus/mobile) | MMC-only |
| 29, 34 | `SPI mode` | Not in SD Host 3.00 |
| 81 | `0x070: Boot timeout Control Register` | eMMC-specific |
| 86 | `0x0208: Core configuration register` | Vendor-specific |
| 87 | `0x0210: Feedback clock selection register` | Vendor-specific |
| 88 | `0x0220: Debug status registers` | Vendor-specific |

---

## Summary

| Metric | Value |
|--------|-------|
| SD Host 3.00 registers in xxx.md | **31 / 32** |
| Missing register | Shared Bus Control (0E0h) |
| Features beyond SD Host 3.00 | SPI mode, 8-bit mode, DDR (MMC), Boot timeout, vendor debug regs |

### Legend
- ✅ Covered (feature + register present)
- ⚠️ Register exists but feature not explicitly documented
- ❌ Missing or not in SD Host 3.00 spec
