# SDMMC Boot Operation & Debug Status Registers — RAG Research

> Auto-generated from SDMMC RAG API queries on 2026-02-23

---

## 1. Boot Operation Features

### F_BOOT_OP — Boot Operation (P1, groups: boot, mmc)

Based on the SDMMC Controller (3MCR) specification for the SPC58 H-Line, the Boot Operation feature enables the host controller to support MMC boot mode, allowing the system to boot directly from an eMMC/MMC device. This functionality permits the controller to read boot data from the MMC card's boot partition during system initialization, typically using a pre-boot or alternative boot sequence defined by the MMC specification. The feature is essential for embedded systems requiring fast, reliable boot-from-flash capability without requiring a separate boot ROM or external memory interface.

### F_ALT_BOOT — Alternative Boot Mode (P2, parent: F_BOOT_OP, groups: boot, mmc)

Alternative Boot Mode provides a secondary boot mechanism for eMMC devices that differs from the mandatory boot mode, allowing the host controller to initiate boot operations using a different command sequence where CMD0 with argument 0xFFFFFFFA is used instead of holding CMD low.

In Alternative Boot Mode, the SDMMC controller initiates the boot sequence by sending a specific boot command rather than using the continuous CMD line assertion method. This mode is configured through the HOSTCONTROL2 register's boot-related fields and the MMCBOOT register, enabling the controller to read boot data from the eMMC device's boot partition using standard command/response protocols while still supporting boot acknowledgment detection and boot data transfer completion signaling.

### F_MMC_4_51 — MMC 4.51 Support (P0, groups: core, compliance)

Includes support for boot operations as part of MMC 4.51 compliance. Implements required command set, timing modes, and protocol extensions.

---

## 2. Block Gap Control Register (BLOCKGAPCONTROL) — 0x002A (8-bit, R/W)

**Spec section:** 57.3.2.13  
**Register layout (Figure 1843):**

| Bit | Field | Reset | Description |
|-----|-------|-------|-------------|
| 0 | BLKGAPCTRL_BOOTACKENA | 1 | To check for the boot acknowledge in boot operation. **1** = Wait for boot ack from eMMC card. **0** = Will not wait for boot ack from eMMC card. |
| 1 | BLKGAPCTRL_ALTBOOTMODE | 0 | To start boot code access in alternative mode. **1** = To start alternate boot mode access. **0** = To stop alternate boot mode access. |
| 2 | BLKGAPCTRL_BOOTENABLE | 0 | To start boot code access. **1** = To start boot code access. **0** = To stop boot code access. |
| 3 | BLKGAPCTRL_SPIMODE | 0 | SPI mode enable bit. **1** = SPI mode. **0** = SDMMC mode. |
| 4 | BLKGAPCTRL_INTERRUPT | 0 | Valid only in 4-bit mode of SDIO card. Setting to 1 enables interrupt detection at the block gap for a multiple block transfer. |
| 5 | BLKGAPCTRL_RDWAITCTRL | 0 | Read Wait function control. **1** = Enable Read Wait control. **0** = Disable Read Wait control. If set to 0, Suspend/Resume cannot be supported. |
| 6 | BLKGAPCTRL_CONTINUE | 0 | Continue request. Used to restart a transaction stopped using Stop at block gap. HC automatically clears this bit when DAT Line Active or Write transfer active changes 0→1. |
| 7 | BLKGAPCTRL_STOPATBLKGAP | 0 | Stop at block gap request. Used to stop executing a transaction at the next block gap for non-DMA, SDMA, and ADMA transfers. **1** = Stop. **0** = Transfer. |

---

## 3. Normal Interrupt Status Register (NORMALINTRSTS) — 0x0030 (16-bit, R/W, w1c)

**Spec section:** 57.3.2.18, Table 1829  
**Register layout (Figure 1848):**

| Bit | Field | Access | Description |
|-----|-------|--------|-------------|
| 0 | REG_ERRORINTRSTS | R | Error interrupt. Reflects combined status of all bits in Error Interrupt Status register. **0** = No error. **1** = Error. |
| 1 | NORMALINTRSTS_BOOTCOMPLETE | w1c | **Boot terminate interrupt.** This status is set if the boot operation get terminated. **0** = Boot operation is not terminated. **1** = Boot operation is terminated. Note: SoC does not support Execute In Place from eMMC. |
| 2 | NORMALINTRSTS_RCVBOOTACK | w1c | **Boot ack rcv.** This status is set if the boot acknowledge is received from device. **0** = Boot ack is not received. **1** = Boot ack is received. Note: SoC does not support Execute In Place from eMMC. |
| 3 | NORMALINTRSTS_RETUNINGEVENT | w1c | Re-tuning event. Set if Re-tuning request in Present State register changes from 0 to 1. Note: Re-tuning is not supported. |
| 4 | NORMALINTRSTS_INTC | — | INT_C. Not supported. |
| 5 | NORMALINTRSTS_INTB | — | INT_B. Not supported. |
| 6 | NORMALINTRSTS_INTA | — | INT_A. Not supported. |
| 7 | NORMALINTRSTS_CARDINTSTS | R | Card interrupt. Writing 1 does not clear; cleared when card stops asserting interrupt. |
| 8 | NORMALINTRSTS_CARDREMSTS | w1c | Card removal. Set when card inserted changes 1→0. |
| 9 | NORMALINTRSTS_CARDINSSTS | w1c | Card insertion. Set when card inserted changes 0→1. |
| 10 | NORMALINTRSTS_BUFRDREADY | w1c | Buffer read ready. Set when Buffer Read Enable changes 0→1. |
| 11 | NORMALINTRSTS_BUFWRREADY | w1c | Buffer write ready. Set when Buffer Write Enable changes 0→1. |
| 12 | NORMALINTRSTS_DMAINTERRUPT | w1c | DMA interrupt. Set if HC detects host DMA buffer boundary in Block Size register. |
| 13 | NORMALINTRSTS_BLKGAPEVENT | w1c | Block gap event. Set when Stop at block gap request is set and transaction stops. |
| 14 | NORMALINTRSTS_XFERCOMPLETE | w1c | Transfer complete. Set when Read/Write transaction is completed. Higher priority than data timeout error. |
| 15 | NORMALINTRSTS_CMDCOMPLETE | w1c | Command complete. Set at end bit of command response (except Auto CMD12/23). |

**IMPORTANT NOTE ON BIT ORDERING:** In this SDMMC IP, the Normal Interrupt Status register has the **boot bits at positions [1:2]** and standard bits reversed from typical SD Host spec (where bit 15=error, bit 0=cmd complete). Here bit 0=error, bit 15=cmd complete. This is a non-standard bit layout.

---

## 4. Normal Interrupt Status Enable Register (NORMALINTRSTSENA) — 0x0034 (16-bit, R/W)

**Spec section:** 57.3.2.20, Table 1834

| Bit | Field | Description |
|-----|-------|-------------|
| 0 | NORMALINTRSTS_ENABLEREGBIT15 | Fixed to 0. HC controls error interrupts via Error Interrupt Status Enable register. |
| 1 | NORMALINTRSTS_ENABLEREGBIT14 | **Boot terminate interrupt enable.** 0=Masked, 1=Enabled. |
| 2 | NORMALINTRSTS_ENABLEREGBIT13 | **Boot ack rcv enable.** 0=Masked, 1=Enabled. |
| 3 | NORMALINTRSTS_ENABLEREGBIT12 | Re-tuning event status enable. 0=Masked, 1=Enabled. (Not supported) |
| 4 | NORMALINTRSTS_ENABLEREGBIT11 | INT_C status enable. (Not supported) |
| 5 | NORMALINTRSTS_ENABLEREGBIT10 | INT_B status enable. (Not supported) |
| 6 | NORMALINTRSTS_ENABLEREGBIT9 | INT_A status enable. (Not supported) |
| 7 | SDHCREGSET_CARDINTSTSENA | Card interrupt status enable. 0=Masked, 1=Enabled. |
| 8 | SDHCREGSET_CARDREMSTSENA | Card removal status enable. 0=Masked, 1=Enabled. |
| 9+ | (remaining bits) | Card insertion, buffer read/write ready, DMA, block gap, transfer complete, command complete enables |

---

## 5. Normal Interrupt Signal Enable Register (NORMALINTRSIGENA) — 0x0038 (16-bit, R/W)

**Spec section:** 57.3.2.22, Table 1836

| Bit | Field | Description |
|-----|-------|-------------|
| 0 | NORMALINTRSTS_ENABLEREGBIT15 | Fixed to 0. HD controls error interrupts via Error Interrupt Signal Enable register. |
| 1 | NORMALINTRSTS_ENABLEREGBIT14 | **Boot terminate interrupt signal enable.** 0=Masked, 1=Enabled. |
| 2 | NORMALINTRSTS_ENABLEREGBIT13 | **Boot ack rcv signal enable.** 0=Masked, 1=Enabled. |
| 3 | NORMALINTRSTS_ENABLEREGBIT12 | Re-tuning event signal enable. 0=Masked, 1=Enabled. (Not supported) |
| 4-6 | ENABLEREGBIT11/10/9 | INT_C/B/A signal enable. (Not supported) |
| 7 | SDHCREGSET_CARDINTSTSENA | Card interrupt signal enable. 0=Masked, 1=Enabled. |

---

## 6. Boot Timeout Control Register (BOOTTIMEOUTCNT) — 0x0070 (32-bit, R/W)

**Spec section:** 57.3.2.37, Table 1854, Figure 1867

| Bits | Field | Reset | Description |
|------|-------|-------|-------------|
| 0:31 | BOOT_TIMEOUTCNT | 0x00000000 | Boot data timeout counter value. This value determines the interval by which DAT line timeouts are detected during boot operation for eMMC card. **The value is in number of sdmmccard_clk clock.** Note: SoC does not support Execute In Place from eMMC. |

---

## 7. Error Interrupt Status Register (ERRORINTRSTS) — 0x0032 (16-bit, R/W, w1c)

**Spec section:** 57.3.2.19, Table 1825  
**Boot-relevant error bits:**

| Bit | Field | Description |
|-----|-------|-------------|
| 3 | ERRORINTRSTS_HOSTERROR | Target response error during DMA transaction |
| 6 | ERRORINTRSTS_ADMAERROR | DMA error during ADMA-based data transfer |
| 7 | ERRORINTRSTS_AUTOCMDERROR | Auto CMD error (CMD12/CMD23) |
| 9 | ERRORINTRSTS_DATAENDBITERROR | Data end bit error — detecting 0 at end bit of read data or CRC status |
| 10 | ERRORINTRSTS_DATACRCERROR | Data CRC error — CRC mismatch during data transfer |
| 11 | ERRORINTRSTS_DATATIMEOUTERROR | Data timeout error — busy timeout, write CRC status timeout, read data timeout |
| 12 | ERRORINTRSTS_CMDINDEXERROR | Command index error in response |
| 13 | ERRORINTRSTS_CMDENDBITERROR | Command end bit error |

---

## 8. Boot Operation Sequences (Spec §57.4.5)

### 8.1 Normal Boot Operation (§57.4.5.1)

**Setup:**
1. Host driver writes boot timeout value into Boot Timeout Control register (per eMMC4.3+ spec)
2. Host driver sets `boot_en` (BLKGAPCTRL_BOOTENABLE) to 1 in Block Gap Control register
3. Host driver sets `data_trans_direction` (XFERMODE_DATAXFERDIR) bit to 1 (Read) in Transfer Mode register

**Boot Sequence:**
4. Host controller drives CMD line to **"0"** (low) to initiate boot operation
5. If `boot_ack_chk` (BLKGAPCTRL_BOOTACKENA) is configured:
   - Controller waits for boot acknowledgment from eMMC4.3+ device
   - On receipt: asserts **NORMALINTRSTS_RCVBOOTACK** (boot_ack_rcv) interrupt
   - On timeout: asserts **ERRORINTRSTS_DATATIMEOUTERROR** (data timeout error) interrupt
6. After servicing boot ack interrupt or timeout, driver programs Boot Timeout Control register with boot data timeout value
7. eMMC device starts sending boot data on DAT line
8. Host controller sends data to system whenever a block is received

**Termination (Normal):**
9. HC terminates boot when programmed number of blocks transferred to system
10. Driver writes `boot_en` = 0 in Block Gap Control register
11. Driver waits for **NORMALINTRSTS_BOOTCOMPLETE** (boot terminate interrupt)
12. After boot termination interrupt: driver issues **soft reset for DATA line** to reset data state machines to idle

**Termination (Mid-transfer):**
- Program Stop at block gap request while transfer is going on
- Wait for **NORMALINTRSTS_XFERCOMPLETE** (Transfer Complete) interrupt
- Clear boot_en
- Issue soft reset for DATA line

**Error Handling During Boot:**
- **Data timeout:** No need to perform error recovery sequence (ignore sending Abort command, soft reset — just clear the timeout interrupt and proceed with the boot flow)
- **Wrong acknowledgment (CRC):** Host controller asserts **ERRORINTRSTS_DATACRCERROR** (data_crc_err). Driver must stop boot by setting boot_en=0, then soft reset for CMD and DATA line
- **End bit error in ack:** Host controller asserts **ERRORINTRSTS_DATAENDBITERROR** (data_end_bit_err). Driver stops boot by setting boot_en=0, then soft reset for CMD and DATA line

**IMPORTANT:** Enable the `boot_ack_chk` bit during boot operation. If not enabled, the controller will not wait for boot acknowledge from the card and will send out data CRC error when the card sends boot ack first followed by boot data.

### 8.2 Alternate Boot Operation (§57.4.5.2)

**Setup:**
1. Host driver writes boot timeout value per eMMC4.3+ spec into Boot Timeout Control register
2. Set `alt_boot_en` (BLKGAPCTRL_ALTBOOTMODE) AND `boot_en` (BLKGAPCTRL_BOOTENABLE) to 1 in Block Gap Control register
3. Set `data_trans_direction` bit to 1 (Read) in Transfer Mode register

**Boot Sequence:**
4. Host controller drives **CMD0 (0xFFFFFFFA)** on the CMD line (instead of holding CMD low)
5. System waits for **Command Complete Interrupt** before `boot_ack_rcv` interrupt
6. If configured to wait for boot ack: controller receives acknowledgment, asserts `boot_ack_rcv` interrupt
7. eMMC device starts sending boot data on DAT line

**Termination (Normal):**
8. HC terminates when programmed number of blocks transferred
9. Driver programs `boot_en` AND `alt_boot_en` as "0" in Block Gap Control register
10. Wait for boot terminate interrupt
11. Driver sends **CMD0 (argument 0x00000000, CMDTYPE=Abort)** to inform device boot operation complete
12. Wait for Command Complete
13. Issue soft reset for DATA line

**Termination (Mid-transfer):**
- Program Stop at block gap request
- Wait for Transfer Complete Interrupt
- Clear boot_en and alt_boot_en
- Send CMD0 (0x00000000, CMDTYPE=Abort), wait for Command Complete
- Issue soft reset for DATA line

**Timeout handling:** Same as normal boot — no need for error recovery on data timeout.

**CRC/End bit errors:** Same as normal boot — clear boot_en and alt_boot_en, soft reset CMD and DATA.

### 8.3 Boot Code Chunk Read Operation (§57.4.5.3)

The driver can read boot data as chunks (2 KB, 4 KB, 1 KB, 8 KB) instead of 128 KB at a time. The flow is the same as alternate boot with chunk-sized block counts.

### 8.4 Boot Code Access Flow (Figure 1880)

Sequence from the flowchart:
1. Power on Reset
2. Initialize the Host Controller
3. Wait for card insertion interrupt
4. Write Clock Control Register
5. Program Block Size, Block Count Register
6. Program System Address Register
7. Program Block Gap Control register: Set boot_en and boot_ack_chk
8. Set dma_en, blk_cnt_en, data transfer direction, multi_block_select in Transfer Mode register
9. Host Controller pulls CMD line low and reads boot data from device
10. Host Controller decrements block count on receiving block of data from device
11. Host Controller stops SD clock when block count reaches zero
12. Asserts boot termination interrupt when FIFO gets empty (once all bytes written to system memory)
13. If Host driver wants to read more data: program block count register again → HC resumes SD clock
14. If driver done with boot code read: set boot_enable to 0 in Block Gap Control register → HC pulls CMD line to High

---

## 9. Boot Timing Parameters

From timing diagrams (Figures 1883-1886):

| Parameter | Description |
|-----------|-------------|
| t_BA | Boot acknowledge timing |
| t_BD | Boot data timing |
| N_AC | Access cycles |
| N_ST | Setup cycles |
| N_CD | Card detection cycles |
| N_CP | Clock period |

**Boot data blocks:** 512 bytes + CRC each  
**Boot data width:** DAT0-7 (up to 8-bit wide)

### Normal Boot Timing (Figures 1883, 1884):
- CMD line held low → Boot request recognized → Optional boot ack (pattern: `010`) → N_AC gap → Data blocks (512B + CRC) → Boot request complete → CMD1

### Alternative Boot Timing (Figures 1885, 1886):
- CMD0 with argument 0xFFFFFFFA → Boot request recognized → Optional boot ack → Data blocks → CMD0/CMD1 to terminate

---

## 10. Transfer Mode Register (TRANSFERMODE) — 0x00C (16-bit, R/W)

**Spec section:** 57.3.2.6  
**Boot-relevant fields:**

| Bit | Field | Description |
|-----|-------|-------------|
| 10 | XFERMODE_MULTIBLKSEL | Multi/Single block select. **0**=Single, **1**=Multiple (use Multiple for boot) |
| 11 | XFERMODE_DATAXFERDIR | Data transfer direction. **0**=Write (host to card), **1**=Read (card to host) — **must be 1 for boot** |

Additional fields (from boot flow): dma_en, blk_cnt_en should also be set.

---

## 11. Debug Status Registers (Wrapper Registers, Read-Only)

**Note:** There is a delay from generating the status signals inside the SDMMC core to update of the related status register bits due to **clock domain crossing**.

**IMPORTANT — Dual Offset Mapping:**
The spec shows two offset schemes:
- **Standard (used in metadata):** 0x10C, 0x110, 0x114, 0x118, 0x11C
- **Actual spec offsets (from full_text):** 0x0220 (DBG_STA1), 0x0224 (DBG_STA2), 0x0228 (DBG_STA3), 0x022C (DBG_STA4), 0x0230 (DBG_STA5)

The metadata uses the "remapped" offsets. The spec memory map at §57.3.1 clearly shows: DBG_STA1=0x0220, DBG_STA2=0x0224, DBG_STA3=0x0228, DBG_STA4=0x022C (not 0x10C etc). The model should use the actual spec offsets.

### 11.1 Debug Status 1 (DBG_STA1) — 0x0220 (metadata: 0x10C)

**Spec section:** 57.3.2.40, Table 1857, Figure 1870  
**Purpose:** 16-bit wide DMA_CTRL debug bus for software debugging

| Bits | Field | Description |
|------|-------|-------------|
| 0:15 | Reserved | All zeros |
| 16:31 | DMADEBUGBUS | DMA_CTRL debug bus signals |

**DMADEBUGBUS sub-fields (bits 16:31):**

| Signal | Description |
|--------|-------------|
| hostintf_blocknextcmd | Command Complete indication from CMDCTRL set, next command should be blocked |
| hostintf_abortcmdmode | Set when Abort command is issued |
| hostintf_rdxferactive | Set from command Last Bit issued or Block Gap Continue to last block sent to host |
| hostintf_enddataxfer | Set when end Data Transfer Complete indications from PIO/SDMA and ADMA2 state machines |
| hostintf_stopatblkgap | For write: set from PIO/SDMA and ADMA2 SMs. For read: RegSet generates Stop at BlkGap |
| hostwrdat_state | WriteData state machine — transfers data to host interface |
| hostrddat_state | ReadData state machine — receives data from host interface |
| hosttrans_state[1:0] | Host transfer state machine (2 bits) |
| adma2_state[3:0] | ADMA2 state machine (4 bits) |
| piosdma_state[2:0] | PIO/SDMA state machine (3 bits) |

### 11.2 Debug Status 2 (DBG_STA2) — 0x0224 (metadata: 0x110)

**Spec section:** 57.3.2.41, Table 1858, Figure 1871  
**Purpose:** 16-bit wide CMD_CTRL debug bus for software debugging

| Bits | Field | Description |
|------|-------|-------------|
| 0:15 | Reserved | All zeros |
| 16:31 | CMDDEBUGBUS | CMD_CTRL debug bus signals |

**CMDDEBUGBUS sub-fields (bits 16:31):**

| Signal | Bits | Description |
|--------|------|-------------|
| cmdfsm_state[3:0] | 4 | Command state machine state |
| cmdfsm_cmdout | 1 | CMD output |
| cmdfsm_cmdena | 1 | CMD output enable |
| cmdfsm_cmdcomplete | 1 | Command complete bit |
| cmdfsm_cmdissued | 1 | CMD issued signal |
| cmdfsm_autocmd12 | 1 | Auto CMD12 indication |
| cmdfsm_autocmd23 | 1 | Set when AutoCMD23 qualified with CMD_Data Present |
| sdhcregset_cmdexecute_sdmmcclk | 1 | Double-synchronized cmdexecute signal |
| sdhcregset_bootena_sdmmcclk | 1 | **Double-synchronized boot enable signal** |
| cmdfsm_cmdrespstatus[3:0] | 4 | Command response status |

### 11.3 Debug Status 3 (DBG_STA3) — 0x0228 (metadata: 0x114)

**Spec section:** 57.3.2.42, Table 1859, Figure 1872  
**Purpose:** 16-bit wide TXD_CTRL (transmit data control) debug bus

| Bits | Field | Description |
|------|-------|-------------|
| 0:15 | Reserved | All zeros |
| 16:31 | TXDDEBUGBUS | TXD_CTRL debug bus signals |

**TXDDEBUGBUS sub-fields (bits 16:31):**

| Signal | Description |
|--------|-------------|
| txdfsm_state[3:0] | Transmit data state machine (4 bits) |
| txdfsm_datalineactive | Data line active indication |
| txdfsm_wrxferactive | Write transfer active indication |
| txdfsm_sdmmcdataena | SDMMC data enable |
| txdfsm_readbuffer | Read buffer |
| txdfsm_readeob | Read EOB (end of block) |
| txdfsm_rcvcrcsts | Receive CRC status indication to RXCRC state machine |
| txdfsm_xmitstsvld | Transmit status valid indication |
| txdfsm_xmitstatus[2:0] | Transmit status {ENDBIT err, CRC error, timeout error} (3 bits) |
| txdfsm_stopsdmmccardclk | Stop SDMMC card clock |
| txdfsm_enatimeoutchk | Enable data timeout check |

### 11.4 Debug Status 4 (DBG_STA4) — 0x022C (metadata: 0x118)

**Spec section:** 57.3.2.43, Table 1860, Figure 1873  
**Purpose:** 16-bit wide RXD_CTRL (receive data control) debug bus

| Bits | Field | Description |
|------|-------|-------------|
| 0:23 | Reserved | All zeros (bits 0:15) + zeros (bits 16:23) |
| 24:31 | RXDDEBUGBUS0 | RXD_CTRL debug bus signals (8 bits only) |

**RXDDEBUGBUS0 sub-fields (bits 24:31):**

| Signal | Description |
|--------|-------------|
| rxctrl_rcvdata | Receive data indication |
| rxctrl_stopsdcardclk1 | Stop SDMMC clock indication (Normal operation, Buffer full) |
| rxctrl_stopsdcardclk2 | Stop SDMMC clock indication (Stop at block gap) |
| rxctrl_stopafterblk | Stop receiving after this block (Stop at block gap) |
| rxctrl_rcvstsvld | Receive status valid |
| rxctrl_rcvstatus[2:0] | Receive status {EndBit Err, CRC Error, timeout error} (3 bits) |

### 11.5 Debug Status 5 (DBG_STA5) — 0x0230 (metadata: 0x11C)

**Spec section:** 57.3.2.44, Table 1861, Figure 1874  
**Purpose:** 16-bit wide RXD_CTRL debug bus on **feedback clock** domain

| Bits | Field | Description |
|------|-------|-------------|
| 0:23 | Reserved | All zeros |
| 24:31 | RXDDEBUGBUS1 | RXD_CTRL debug bus (RX CLK domain) signals (8 bits only) |

**RXDDEBUGBUS1 sub-fields (bits 24:31):**

| Signal | Bits | Description |
|--------|------|-------------|
| rxdfsm_state[2:0] | 3 | Receive data state machine |
| rxdfsm_wtforblk | 1 | Wait for block indication |
| rxdfsm_datawrite | 1 | Data Byte/Word write |
| rxdfsm_dataeob | 1 | Data Byte/Word is End of block indication |
| rxdfsm_okstopclk | 1 | OK to Stop the clock (End of block flow control) |
| rxdfsm_reachingeob | 1 | Reaching End of block indication |

---

## 12. Core Config Register (CORE_CONFIG) — 0x0208 (metadata: 0x104)

**Spec section:** 57.3.2.38, Table 1855, Figure 1868

| Bits | Field | Reset | Description |
|------|-------|-------|-------------|
| 0:7 | MAXCURRENT_3P3V | 0x00 | Maximum current for 3.3V. Value depends on IO drive strength. |
| 8:11 | Reserved | 0 | |
| 12:13 | CORECFG_SLOTTYPE | 0b00 | 00=Removable card slot, 01=Embedded slot for one device, 10=Shared bus slot, 11=Reserved |
| 14 | CORECFG_ASYNCHINTRSUPPORT | 1 | Enable asynchronous interrupt support. 0=Not supported, 1=Supported. |
| 15 | CORECFG_ADMA2SUPPORT | 0 | Selection for ADMA2 support. |
| 16:23 | Reserved | 0 | |
| 24:31 | BASECLKFREQ_SDMMC_CLK | 0x32 | Base clock frequency for SDMMC clock. 0x32 = 50 MHz. |

---

## 13. FB_CLK_SEL Register — 0x0210 (metadata: 0x108)

**Spec section:** 57.3.2.39, Table 1856

| Bits | Field | Description |
|------|-------|-------------|
| 30:31 | FEEDBACKCLK_SEL | Selects feedback clock from loopback sources. 00=Loopback from output of SDMMC HC IP (delayed Tx clock). 01=OPEN. 10=OPEN. 11=Loopback from external SDMMC device pin (SDMMC_FDBCK_CLK IO PAD). |

---

## 14. Register Offset Mapping Summary

The metadata uses "compact" offsets while the spec uses wrapper-region offsets for vendor-specific registers:

| Register | Metadata Offset | Spec Offset | Size |
|----------|----------------|-------------|------|
| Boot Timeout Control (BOOTTIMEOUTCNT) | 0x100 | 0x0070 | 32-bit |
| Core Config (CORE_CONFIG) | 0x104 | 0x0208 | 32-bit |
| FB_CLK_SEL | 0x108 | 0x0210 | 32-bit |
| Debug Status 1 (DBG_STA1) | 0x10C | 0x0220 | 32-bit (bits 16:31 active) |
| Debug Status 2 (DBG_STA2) | 0x110 | 0x0224 | 32-bit (bits 16:31 active) |
| Debug Status 3 (DBG_STA3) | 0x114 | 0x0228 | 32-bit (bits 16:31 active) |
| Debug Status 4 (DBG_STA4) | 0x118 | 0x022C | 32-bit (bits 24:31 active) |
| Debug Status 5 (DBG_STA5) | 0x11C | 0x0230 | 32-bit (bits 24:31 active) |

Standard SD Host registers (0x000-0x0FE) use their standard offsets.

---

## 15. State Machine Enumerations (from Debug Registers)

### PIO/SDMA State Machine (piosdma_state, 3 bits — DBG_STA1)
Manages PIO and SDMA data transfers. States TBD from RTL.

### ADMA2 State Machine (adma2_state, 4 bits — DBG_STA1)
Manages ADMA2 descriptor-based DMA transfers. States TBD from RTL.

### Host Transfer State Machine (hosttrans_state, 2 bits — DBG_STA1)
Top-level host transfer coordination. States TBD from RTL.

### Command FSM (cmdfsm_state, 4 bits — DBG_STA2)
Command processing state machine. States TBD from RTL.

### Transmit Data FSM (txdfsm_state, 4 bits — DBG_STA3)
Transmit (write) data path state machine. States TBD from RTL.

### Receive Data FSM (rxdfsm_state, 3 bits — DBG_STA5)
Receive (read) data path state machine on RX clock domain. States TBD from RTL.

---

## 16. Implementation Notes for C++/SystemC Model

### Boot Operation Implementation Checklist:

1. **Block Gap Control register** (0x02A): Implement BOOTACKENA (bit 0), ALTBOOTMODE (bit 1), BOOTENABLE (bit 2) with proper reset values (bit 0 resets to 1, rest to 0)

2. **Normal Interrupt Status** (0x030): Implement BOOTCOMPLETE (bit 1) and RCVBOOTACK (bit 2) as w1c bits

3. **Normal Interrupt Status Enable** (0x034): Implement enable bits 1 (boot terminate) and 2 (boot ack rcv)

4. **Normal Interrupt Signal Enable** (0x038): Implement signal enable bits 1 and 2 for boot interrupts

5. **Boot Timeout Control** (0x070/0x100): 32-bit R/W register, counts in sdmmccard_clk cycles

6. **Boot state machine** needs states for:
   - IDLE → WAIT_BOOT_ACK (if BOOTACKENA) → RECEIVING_BOOT_DATA → BOOT_COMPLETE
   - IDLE → SENDING_CMD0_ALT_BOOT → WAIT_CMD_COMPLETE → WAIT_BOOT_ACK → RECEIVING_BOOT_DATA → BOOT_COMPLETE

7. **Error conditions during boot:**
   - Boot ack timeout → DATATIMEOUTERROR interrupt (no error recovery needed)
   - Boot data timeout → DATATIMEOUTERROR interrupt (no error recovery needed)  
   - Wrong ack (CRC) → DATACRCERROR interrupt
   - End bit error in ack → DATAENDBITERROR interrupt

8. **Boot termination:** Setting BOOTENABLE=0 triggers boot termination sequence. HC asserts BOOTCOMPLETE interrupt when FIFO drains.

### Debug Register Implementation:

1. All 5 debug registers are **read-only**
2. They reflect internal state machine states and control signals
3. Subject to clock domain crossing delays
4. DBG_STA1 (bits 16:31): Pack DMA controller status signals
5. DBG_STA2 (bits 16:31): Pack CMD controller status including boot_ena synchronized signal
6. DBG_STA3 (bits 16:31): Pack transmit data path status
7. DBG_STA4 (bits 24:31): Pack receive data path status (8 bits only)
8. DBG_STA5 (bits 24:31): Pack receive data path status on RX clock (8 bits only)
