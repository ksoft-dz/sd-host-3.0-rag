#!/usr/bin/env python3
"""
Generate metadata.json for Ux500 MSP I2S Controller from Linux driver sources.

This script builds a knowledge graph in the same schema as the PDF-based RAGs
(SD Host, SDIO, eMMC, SD Physical Layer) but sourced entirely from driver code.

Source files analyzed:
  - ux500-msp-i2s.h  (register offsets, bit masks, shifts, enums)
  - ux500-msp-i2s.c  (register usage patterns, protocol configs)
  - device-tree-binding.txt  (base addresses, compatible strings)
  - cpu-db8500.c  (MSP instances 0-3 at specific addresses)
"""

import json
import time
from pathlib import Path

OUT = Path(__file__).parent.parent / "metadata" / "metadata.json"


# =============================================================================
# REGISTER DEFINITIONS
# =============================================================================

def _f(reg_id, idx, name, bits, high, low, width, access, desc, values=None):
    """Build a field dict."""
    return {
        "id": f"{reg_id}_F{idx}",
        "name": name,
        "bits": bits,
        "bit_high": high,
        "bit_low": low,
        "width": width,
        "access": access,
        "original_attrib": access,
        "raw": desc,
        "abstract": desc,
        "values": values or []
    }


def build_registers():
    regs = []

    # =========================================================================
    # REG_000 — MSP_DR (0x00) Data Register
    # =========================================================================
    r = _reg("REG_000", "MSP_DR", "000h", "Data Register",
             "Transmit/receive data register. Write to transmit, read to receive. "
             "In 8-bit element mode only bits [7:0] are significant; in 16-bit mode "
             "bits [15:0]; in 32-bit mode full [31:0]. Data is shifted MSB-first by "
             "default (configurable via ENDN in TCF/RCF).",
             "6.9", 0)
    r["fields"] = [
        _f(r["id"], 0, "DATA", "31:0", 31, 0, 32, "R/W",
           "Transmit/receive data word. Width depends on element length setting.")
    ]
    regs.append(r)

    # =========================================================================
    # REG_004 — MSP_GCR (0x04) Global Configuration Register
    # =========================================================================
    r = _reg("REG_004", "MSP_GCR", "004h", "Global Configuration Register",
             "Master control register for the MSP. Controls RX/TX enable, FIFO enable, "
             "clock selection and polarity, frame sync, loopback mode, sample rate "
             "generator, frame generator, and SPI mode settings.",
             "6.9", 0)
    r["fields"] = [
        _f(r["id"], 0, "RXEN", "0", 0, 0, 1, "R/W",
           "Receive Enable. 1=RX path enabled, 0=disabled."),
        _f(r["id"], 1, "RFFEN", "1", 1, 1, 1, "R/W",
           "Receive FIFO Enable. 1=RX FIFO enabled, 0=disabled (direct DR access)."),
        _f(r["id"], 2, "RFSPOL", "2", 2, 2, 1, "R/W",
           "Receive Frame Sync Polarity. 0=active high, 1=active low."),
        _f(r["id"], 3, "DCM", "3", 3, 3, 1, "R/W",
           "Direct Companding Mode. 1=hardware companding/expansion active, "
           "0=linear mode."),
        _f(r["id"], 4, "RFSSEL", "4", 4, 4, 1, "R/W",
           "Receive Frame Sync Selection. Selects frame sync source for RX. "
           "0=external, 1=internal (from SRG)."),
        _f(r["id"], 5, "RCKPOL", "5", 5, 5, 1, "R/W",
           "Receive Clock Polarity. 0=data sampled on falling edge, "
           "1=data sampled on rising edge."),
        _f(r["id"], 6, "RCKSEL", "6", 6, 6, 1, "R/W",
           "Receive Clock Selection. 0=external clock, 1=clock from SRG."),
        _f(r["id"], 7, "LBM", "7", 7, 7, 1, "R/W",
           "Loopback Mode. 1=TX output is looped back to RX input internally. "
           "Used for diagnostics."),
        _f(r["id"], 8, "TXEN", "8", 8, 8, 1, "R/W",
           "Transmit Enable. 1=TX path enabled, 0=disabled."),
        _f(r["id"], 9, "TFFEN", "9", 9, 9, 1, "R/W",
           "Transmit FIFO Enable. 1=TX FIFO enabled, 0=disabled (direct DR access)."),
        _f(r["id"], 10, "TFSPOL", "10", 10, 10, 1, "R/W",
           "Transmit Frame Sync Polarity. 0=active high, 1=active low."),
        _f(r["id"], 11, "TFSSEL", "12:11", 12, 11, 2, "R/W",
           "Transmit Frame Sync Selection. 00=external FSYNC, 01=from SRG (prog), "
           "10=from SRG (auto), 11=reserved.",
           [{"value": "00", "meaning": "External frame sync"},
            {"value": "01", "meaning": "Frame sync from SRG (programmed)"},
            {"value": "10", "meaning": "Frame sync from SRG (automatic)"}]),
        _f(r["id"], 12, "TCKPOL", "13", 13, 13, 1, "R/W",
           "Transmit Clock Polarity. 0=data driven on falling edge, "
           "1=data driven on rising edge."),
        _f(r["id"], 13, "TCKSEL", "14", 14, 14, 1, "R/W",
           "Transmit Clock Selection. 0=external clock, 1=clock from SRG."),
        _f(r["id"], 14, "TXDDL", "15", 15, 15, 1, "R/W",
           "TX Extra Delay. 1=one extra bit-clock delay added to TX data path. "
           "Used to compensate for pipeline delays in certain protocols."),
        _f(r["id"], 15, "SGEN", "16", 16, 16, 1, "R/W",
           "Sample Rate Generator Enable. 1=SRG clock output active, 0=stopped. "
           "Must be enabled before FGEN."),
        _f(r["id"], 16, "SCKPOL", "17", 17, 17, 1, "R/W",
           "SRG Clock Polarity. Selects polarity of sample rate generated clock."),
        _f(r["id"], 17, "SCKSEL", "19:18", 19, 18, 2, "R/W",
           "SRG Clock Selection. Selects the input clock source for the SRG. "
           "00=APB clock (default)."),
        _f(r["id"], 18, "FGEN", "20", 20, 20, 1, "R/W",
           "Frame Generator Enable. 1=frame sync generation active. "
           "SRG must be enabled first (SGEN=1)."),
        _f(r["id"], 19, "SPICKM", "22:21", 22, 21, 2, "R/W",
           "SPI Clock Mode. Selects SPI clock phase/polarity when MSP is used "
           "in SPI-compatible mode. 00=normal."),
        _f(r["id"], 20, "SPIBME", "23", 23, 23, 1, "R/W",
           "SPI Burst Mode Enable. 1=SPI burst transfer mode enabled."),
    ]
    regs.append(r)

    # =========================================================================
    # REG_008 — MSP_TCF (0x08) Transmit Configuration Register
    # =========================================================================
    r = _reg("REG_008", "MSP_TCF", "008h", "Transmit Configuration Register",
             "Configures the transmit protocol: element and frame lengths for both "
             "phases, data type (companding), endianness, data delay, frame sync "
             "behavior, and byte swap mode. Supports single or dual phase operation.",
             "6.9", 0)
    r["fields"] = _proto_config_fields(r["id"], "TX")
    regs.append(r)

    # =========================================================================
    # REG_00C — MSP_RCF (0x0C) Receive Configuration Register
    # =========================================================================
    r = _reg("REG_00C", "MSP_RCF", "00Ch", "Receive Configuration Register",
             "Configures the receive protocol: element and frame lengths for both "
             "phases, data type (expansion), endianness, data delay, frame sync "
             "behavior, and byte swap mode. Mirrors TCF layout for RX path.",
             "6.9", 0)
    r["fields"] = _proto_config_fields(r["id"], "RX")
    regs.append(r)

    # =========================================================================
    # REG_010 — MSP_SRG (0x10) Sample Rate Generator Register
    # =========================================================================
    r = _reg("REG_010", "MSP_SRG", "010h", "Sample Rate Generator Register",
             "Configures the sample rate generator which produces the bit clock and "
             "frame sync. SCKDIV divides the input clock. FRWID sets the active "
             "frame sync width. FRPER sets the total frame period in clock cycles.",
             "6.9", 0)
    r["fields"] = [
        _f(r["id"], 0, "SCKDIV", "9:0", 9, 0, 10, "R/W",
           "Sample Clock Divider. The input clock (APB or external) is divided by "
           "(SCKDIV+1) to produce the bit clock. Range: 0-1023. Bit clock = "
           "f_input / (SCKDIV+1). Default APB clock is 48 MHz."),
        _f(r["id"], 1, "FRWID", "15:10", 15, 10, 6, "R/W",
           "Frame Width. Sets the number of bit-clock cycles during which frame "
           "sync is active. For I2S: 15 (16 cycles), for PCM: 0 (1 cycle)."),
        _f(r["id"], 2, "FRPER", "28:16", 28, 16, 13, "R/W",
           "Frame Period. Total number of bit-clock cycles per frame. "
           "For I2S stereo: 31 (32 cycles), for PCM: 255 (256 cycles). "
           "Frame frequency = bit_clock / (FRPER+1)."),
    ]
    regs.append(r)

    # =========================================================================
    # REG_014 — MSP_FLR (0x14) Flag Register
    # =========================================================================
    r = _reg("REG_014", "MSP_FLR", "014h", "Flag Register",
             "Read-only status flags showing RX/TX busy states and FIFO fullness. "
             "Used by the driver to poll FIFO status during flush operations.",
             "6.9", 0)
    r["fields"] = [
        _f(r["id"], 0, "RBUSY", "0", 0, 0, 1, "R",
           "Receive Busy. 1=RX is currently active receiving data."),
        _f(r["id"], 1, "RFE", "1", 1, 1, 1, "R",
           "Receive FIFO Empty. 1=RX FIFO is empty, no data available to read."),
        _f(r["id"], 2, "RFU", "2", 2, 2, 1, "R",
           "Receive FIFO Full. 1=RX FIFO is full, no room for new data."),
        _f(r["id"], 3, "TBUSY", "3", 3, 3, 1, "R",
           "Transmit Busy. 1=TX is currently active transmitting data."),
        _f(r["id"], 4, "TFE", "4", 4, 4, 1, "R",
           "Transmit FIFO Empty. 1=TX FIFO is empty. Used during flush to confirm "
           "all data has been transmitted."),
        _f(r["id"], 5, "TFU", "5", 5, 5, 1, "R",
           "Transmit FIFO Full. 1=TX FIFO is full, cannot accept more data."),
    ]
    regs.append(r)

    # =========================================================================
    # REG_018 — MSP_DMACR (0x18) DMA Control Register
    # =========================================================================
    r = _reg("REG_018", "MSP_DMACR", "018h", "DMA Control Register",
             "Enables DMA request generation for RX and TX paths. When enabled, "
             "the MSP asserts DMA request lines instead of generating CPU interrupts "
             "for data transfer.",
             "6.9", 0)
    r["fields"] = [
        _f(r["id"], 0, "RDMAE", "0", 0, 0, 1, "R/W",
           "Receive DMA Enable. 1=DMA requests generated for RX data available."),
        _f(r["id"], 1, "TDMAE", "1", 1, 1, 1, "R/W",
           "Transmit DMA Enable. 1=DMA requests generated for TX FIFO space available."),
    ]
    regs.append(r)

    # =========================================================================
    # REG_020 — MSP_IMSC (0x20) Interrupt Mask Set/Clear Register
    # =========================================================================
    r = _reg("REG_020", "MSP_IMSC", "020h", "Interrupt Mask Set/Clear Register",
             "Controls which interrupt sources are enabled (unmasked). Writing 1 to a "
             "bit enables the corresponding interrupt; writing 0 masks it. The driver "
             "uses this to enable RX/TX service and error interrupts.",
             "6.9", 0)
    r["fields"] = _interrupt_fields(r["id"])
    regs.append(r)

    # =========================================================================
    # REG_024 — MSP_RIS (0x24) Raw Interrupt Status Register
    # =========================================================================
    r = _reg("REG_024", "MSP_RIS", "024h", "Raw Interrupt Status Register",
             "Shows raw (pre-mask) interrupt status for all 8 interrupt sources. "
             "Each bit indicates whether the corresponding event occurred, regardless "
             "of the IMSC mask setting.",
             "6.9", 0)
    r["fields"] = _interrupt_fields(r["id"])
    regs.append(r)

    # =========================================================================
    # REG_028 — MSP_MIS (0x28) Masked Interrupt Status Register
    # =========================================================================
    r = _reg("REG_028", "MSP_MIS", "028h", "Masked Interrupt Status Register",
             "Shows masked interrupt status: RIS AND IMSC. Only bits corresponding "
             "to enabled (unmasked) interrupts will be set. This is what the interrupt "
             "handler should read to determine the cause of an interrupt.",
             "6.9", 0)
    r["fields"] = _interrupt_fields(r["id"])
    regs.append(r)

    # =========================================================================
    # REG_02C — MSP_ICR (0x2C) Interrupt Clear Register
    # =========================================================================
    r = _reg("REG_02C", "MSP_ICR", "02Ch", "Interrupt Clear Register",
             "Write-only register to clear pending interrupts. Writing 1 to a bit "
             "clears the corresponding interrupt. Must be written in the ISR to "
             "acknowledge handled interrupts.",
             "6.9", 0)
    fields = _interrupt_fields(r["id"])
    for f in fields:
        f["access"] = "W"
        f["original_attrib"] = "W"
    r["fields"] = fields
    regs.append(r)

    # =========================================================================
    # REG_030 — MSP_MCR (0x30) Multichannel Control Register
    # =========================================================================
    r = _reg("REG_030", "MSP_MCR", "030h", "Multichannel Control Register",
             "Controls multichannel (TDM) operation for RX and TX. Enables per-channel "
             "selection and RX comparison mode. Multichannel is only supported in "
             "single-phase mode. Up to 4x32=128 channels can be enabled via TCE/RCE.",
             "6.9", 0)
    r["fields"] = [
        _f(r["id"], 0, "RMCEN", "0", 0, 0, 1, "R/W",
           "Receive Multichannel Enable. 1=RX multichannel mode active. "
           "Only valid in single-phase mode."),
        _f(r["id"], 1, "RMCSF", "2:1", 2, 1, 2, "R/W",
           "Receive Multichannel Sub-frame. Selects RX multichannel start phase "
           "configuration."),
        _f(r["id"], 2, "RCMPM", "4:3", 4, 3, 2, "R/W",
           "Receive Comparison Mode. Controls data comparison on received channels. "
           "00=disabled, 10=match on non-equal, 11=match on equal.",
           [{"value": "00", "meaning": "Comparison disabled"},
            {"value": "10", "meaning": "Interrupt on non-equal match"},
            {"value": "11", "meaning": "Interrupt on equal match"}]),
        _f(r["id"], 3, "TMCEN", "5", 5, 5, 1, "R/W",
           "Transmit Multichannel Enable. 1=TX multichannel mode active. "
           "Only valid in single-phase mode."),
        _f(r["id"], 4, "TNCSF", "7:6", 7, 6, 2, "R/W",
           "Transmit Next Channel Sub-frame. Selects TX multichannel start phase "
           "configuration."),
    ]
    regs.append(r)

    # =========================================================================
    # REG_034 — MSP_RCV (0x34) Receive Comparison Value
    # =========================================================================
    r = _reg("REG_034", "MSP_RCV", "034h", "Receive Comparison Value Register",
             "32-bit comparison value for multichannel RX data matching. When RCMPM "
             "is enabled, incoming data is compared against (data & RCM) == RCV. "
             "Cleared to 0 on MSP close.",
             "6.9", 0)
    r["fields"] = [
        _f(r["id"], 0, "CVAL", "31:0", 31, 0, 32, "R/W",
           "Comparison Value. Data received on enabled channels is compared to this "
           "value (masked by RCM) to determine match/non-match condition.")
    ]
    regs.append(r)

    # =========================================================================
    # REG_038 — MSP_RCM (0x38) Receive Comparison Mask
    # =========================================================================
    r = _reg("REG_038", "MSP_RCM", "038h", "Receive Comparison Mask Register",
             "32-bit mask for the receive comparison operation. Only bits set to 1 "
             "in this register participate in the comparison with RCV. "
             "Cleared to 0 on MSP close.",
             "6.9", 0)
    r["fields"] = [
        _f(r["id"], 0, "CMASK", "31:0", 31, 0, 32, "R/W",
           "Comparison Mask. Bit-level mask applied before comparing received data "
           "against the comparison value in RCV.")
    ]
    regs.append(r)

    # =========================================================================
    # REG_040..04C — MSP_TCE0..3 (0x40-0x4C) TX Channel Enable 0-3
    # =========================================================================
    for i in range(4):
        off = 0x40 + i * 4
        r = _reg(f"REG_{off:03X}", f"MSP_TCE{i}", f"{off:03X}h",
                 f"Transmit Channel Enable {i} Register",
                 f"32-bit channel enable mask for TX multichannel group {i}. Each bit "
                 f"enables one of 32 channels (channels {i*32}-{i*32+31}). Only effective "
                 f"when TMCEN=1 in MCR. Cleared on MSP close.",
                 "6.9", 0)
        r["fields"] = [
            _f(r["id"], 0, f"TCE{i}", "31:0", 31, 0, 32, "R/W",
               f"TX channel enable bits for channels {i*32}-{i*32+31}. "
               f"1=channel active, 0=channel muted.")
        ]
        regs.append(r)

    # =========================================================================
    # REG_060..06C — MSP_RCE0..3 (0x60-0x6C) RX Channel Enable 0-3
    # =========================================================================
    for i in range(4):
        off = 0x60 + i * 4
        r = _reg(f"REG_{off:03X}", f"MSP_RCE{i}", f"{off:03X}h",
                 f"Receive Channel Enable {i} Register",
                 f"32-bit channel enable mask for RX multichannel group {i}. Each bit "
                 f"enables one of 32 channels (channels {i*32}-{i*32+31}). Only effective "
                 f"when RMCEN=1 in MCR. Cleared on MSP close.",
                 "6.9", 0)
        r["fields"] = [
            _f(r["id"], 0, f"RCE{i}", "31:0", 31, 0, 32, "R/W",
               f"RX channel enable bits for channels {i*32}-{i*32+31}. "
               f"1=channel active, 0=channel ignored.")
        ]
        regs.append(r)

    # =========================================================================
    # REG_070 — MSP_IODLY (0x70) I/O Delay Register
    # =========================================================================
    r = _reg("REG_070", "MSP_IODLY", "070h", "I/O Delay Register",
             "Configures I/O pad delay for the MSP data and clock lines. Written "
             "during MSP open/enable sequence. The value is provided by the platform "
             "configuration.",
             "6.9", 0)
    r["fields"] = [
        _f(r["id"], 0, "IODLY", "31:0", 31, 0, 32, "R/W",
           "I/O delay configuration value. Platform-specific. Controls signal "
           "timing at the pad level.")
    ]
    regs.append(r)

    # =========================================================================
    # REG_080 — MSP_ITCR (0x80) Integration Test Control Register
    # =========================================================================
    r = _reg("REG_080", "MSP_ITCR", "080h", "Integration Test Control Register",
             "Controls integration test mode. When ITEN is set, normal operation is "
             "overridden and the test logic takes control. TESTFIFO enables direct "
             "FIFO access via the test data register (TSTDR). Used during TX FIFO flush.",
             "6.9", 0)
    r["fields"] = [
        _f(r["id"], 0, "ITEN", "0", 0, 0, 1, "R/W",
           "Integration Test Enable. 1=test mode active, normal operation suspended."),
        _f(r["id"], 1, "TESTFIFO", "1", 1, 1, 1, "R/W",
           "Test FIFO. 1=FIFO test mode, allows read/write via TSTDR register. "
           "Driver sets both ITEN+TESTFIFO to flush TX FIFO during close."),
    ]
    regs.append(r)

    # =========================================================================
    # REG_084 — MSP_ITIP (0x84) Integration Test Input Register
    # =========================================================================
    r = _reg("REG_084", "MSP_ITIP", "084h", "Integration Test Input Register",
             "Provides test input data when integration test mode is active (ITEN=1). "
             "Not used by the Linux driver in normal operation.",
             "6.9", 0)
    r["fields"] = [
        _f(r["id"], 0, "ITIP", "31:0", 31, 0, 32, "R",
           "Integration test input data.")
    ]
    regs.append(r)

    # =========================================================================
    # REG_088 — MSP_ITOP (0x88) Integration Test Output Register
    # =========================================================================
    r = _reg("REG_088", "MSP_ITOP", "088h", "Integration Test Output Register",
             "Provides test output data when integration test mode is active (ITEN=1). "
             "Not used by the Linux driver in normal operation.",
             "6.9", 0)
    r["fields"] = [
        _f(r["id"], 0, "ITOP", "31:0", 31, 0, 32, "R/W",
           "Integration test output data.")
    ]
    regs.append(r)

    # =========================================================================
    # REG_08C — MSP_TSTDR (0x8C) Test Data Read Register
    # =========================================================================
    r = _reg("REG_08C", "MSP_TSTDR", "08Ch", "Test Data Read Register",
             "Provides direct access to the TX FIFO contents when ITCR.TESTFIFO=1. "
             "The driver reads this register in a loop during flush_fifo_tx() to drain "
             "the TX FIFO.",
             "6.9", 0)
    r["fields"] = [
        _f(r["id"], 0, "TDATA", "31:0", 31, 0, 32, "R",
           "Test data read from TX FIFO. Only valid when ITCR.TESTFIFO=1.")
    ]
    regs.append(r)

    # =========================================================================
    # REG_FE0..FEC — MSP_PID0..3 Peripheral ID Registers
    # =========================================================================
    pid_descs = [
        ("Peripheral Identification 0", "Part Number [7:0]. Identifies the MSP peripheral."),
        ("Peripheral Identification 1", "Part Number [11:8] and Designer [3:0]."),
        ("Peripheral Identification 2", "Designer [7:4] and Revision [3:0]."),
        ("Peripheral Identification 3", "Configuration and ECO revision."),
    ]
    for i, (name, desc) in enumerate(pid_descs):
        off = 0xFE0 + i * 4
        r = _reg(f"REG_{off:03X}", f"MSP_PID{i}", f"{off:03X}h",
                 f"{name} Register",
                 f"ARM PrimeCell identification register. {desc} Read-only.",
                 "6.9", 0)
        r["fields"] = [
            _f(r["id"], 0, f"PID{i}", "7:0", 7, 0, 8, "R", desc)
        ]
        regs.append(r)

    # =========================================================================
    # REG_FF0..FFC — MSP_CID0..3 Component ID Registers
    # =========================================================================
    cid_vals = [0x0D, 0xF0, 0x05, 0xB1]  # Standard ARM PrimeCell component ID
    for i in range(4):
        off = 0xFF0 + i * 4
        r = _reg(f"REG_{off:03X}", f"MSP_CID{i}", f"{off:03X}h",
                 f"Component Identification {i} Register",
                 f"ARM PrimeCell component ID byte {i}. Standard value is 0x{cid_vals[i]:02X}. "
                 f"Together CID0-3 form the 32-bit PrimeCell component ID.",
                 "6.9", 0)
        r["fields"] = [
            _f(r["id"], 0, f"CID{i}", "7:0", 7, 0, 8, "R",
               f"Component ID byte {i}. Expected value: 0x{cid_vals[i]:02X}.")
        ]
        regs.append(r)

    return regs


def _reg(reg_id, name, offset, title, desc, section, page):
    """Build a register node dict."""
    return {
        "id": reg_id,
        "name": f"{name} — {title}",
        "offset": offset,
        "spec_section": section,
        "spec_table": "",
        "class_id": "REGCLASS_ID" if int(offset.replace("h", ""), 16) >= 0xFE0 else "REGCLASS_CORE",
        "fields": [],
        "source": {
            "page": page,
            "definition_page": page,
            "driver_file": "ux500-msp-i2s.h"
        },
        "description": desc
    }


def _proto_config_fields(reg_id, direction):
    """Build fields for TCF or RCF protocol configuration register."""
    d = "transmit" if direction == "TX" else "receive"
    compress = "compression" if direction == "TX" else "expansion"
    return [
        _f(reg_id, 0, "P1ELEN", "2:0", 2, 0, 3, "R/W",
           f"Phase 1 Element Length. Encodes the {d} data element width. "
           "000=8-bit, 001=10-bit, 010=12-bit, 011=14-bit, 100=16-bit, "
           "101=20-bit, 110=24-bit, 111=32-bit.",
           [{"value": "000", "meaning": "8 bits"},
            {"value": "001", "meaning": "10 bits"},
            {"value": "010", "meaning": "12 bits"},
            {"value": "011", "meaning": "14 bits"},
            {"value": "100", "meaning": "16 bits"},
            {"value": "101", "meaning": "20 bits"},
            {"value": "110", "meaning": "24 bits"},
            {"value": "111", "meaning": "32 bits"}]),
        _f(reg_id, 1, "P1FLEN", "9:3", 9, 3, 7, "R/W",
           f"Phase 1 Frame Length. Number of elements per frame in phase 1 minus 1. "
           f"E.g., 0=1 element, 15=16 elements, 63=64 elements."),
        _f(reg_id, 2, "DTYP", "11:10", 11, 10, 2, "R/W",
           f"Data Type / {compress.title()} Mode. Controls hardware companding. "
           "00=linear (no companding), 10=µ-law, 11=A-law. Bit 10 may also encode "
           "frame sync polarity in certain configurations (driver ambiguity).",
           [{"value": "00", "meaning": "Linear (no companding)"},
            {"value": "10", "meaning": "µ-law companding"},
            {"value": "11", "meaning": "A-law companding"}]),
        _f(reg_id, 3, "ENDN", "12", 12, 12, 1, "R/W",
           f"Endianness / Bit Order. 0=MSB first (big-endian), 1=LSB first "
           f"(little-endian) for {d} data."),
        _f(reg_id, 4, "DDLY", "14:13", 14, 13, 2, "R/W",
           f"Data Delay. Number of bit-clock cycles between frame sync and first "
           f"data bit for {d}. 00=0 cycles, 01=1 cycle (I2S uses 1), "
           f"10=2 cycles, 11=3 cycles.",
           [{"value": "00", "meaning": "0 clock delay"},
            {"value": "01", "meaning": "1 clock delay (I2S standard)"},
            {"value": "10", "meaning": "2 clock delay"},
            {"value": "11", "meaning": "3 clock delay"}]),
        _f(reg_id, 5, "FSIG", "15", 15, 15, 1, "R/W",
           "Frame Sync Ignore. Controls behavior on unexpected frame sync edge. "
           "0=abort current transfer on unexpected FSYNC, "
           "1=ignore unexpected FSYNC and continue."),
        _f(reg_id, 6, "P2ELEN", "18:16", 18, 16, 3, "R/W",
           f"Phase 2 Element Length. Same encoding as P1ELEN. Only used when "
           f"P2EN=1 (dual-phase mode)."),
        _f(reg_id, 7, "P2FLEN", "25:19", 25, 19, 7, "R/W",
           f"Phase 2 Frame Length. Number of elements per frame in phase 2 minus 1. "
           f"Only used when P2EN=1."),
        _f(reg_id, 8, "P2SM", "26", 26, 26, 1, "R/W",
           "Phase 2 Start Mode. 0=phase 2 starts immediately after phase 1, "
           "1=phase 2 starts on next frame sync edge.",
           [{"value": "0", "meaning": "Immediate start after phase 1"},
            {"value": "1", "meaning": "Start on frame sync"}]),
        _f(reg_id, 9, "P2EN", "27", 27, 27, 1, "R/W",
           "Phase 2 Enable (dual-phase mode). 0=single-phase protocol, "
           "1=dual-phase protocol. PCM typically uses dual-phase; I2S uses "
           "single-phase.",
           [{"value": "0", "meaning": "Single-phase mode"},
            {"value": "1", "meaning": "Dual-phase mode"}]),
        _f(reg_id, 10, "TBSWAP", "29:28", 29, 28, 2, "R/W",
           f"Byte/Half-word Swap for {d} data. Controls byte ordering within "
           f"data words.",
           [{"value": "00", "meaning": "No swap"},
            {"value": "01", "meaning": "Swap bytes within each word"},
            {"value": "10", "meaning": "Swap bytes within each half-word"},
            {"value": "11", "meaning": "Swap half-words within each word"}]),
    ]


def _interrupt_fields(reg_id):
    """Build the 8 interrupt bit fields (shared by IMSC, RIS, MIS, ICR)."""
    return [
        _f(reg_id, 0, "RSIP", "0", 0, 0, 1, "R/W",
           "Receive Service Interrupt. Set when RX FIFO has data ready to be read "
           "(FIFO threshold reached)."),
        _f(reg_id, 1, "ROEI", "1", 1, 1, 1, "R/W",
           "Receive Overrun Error Interrupt. Set when RX FIFO overflows — new data "
           "arrives but FIFO is full. Indicates data loss."),
        _f(reg_id, 2, "RFEI", "2", 2, 2, 1, "R/W",
           "Receive Frame Sync Error Interrupt. Set on unexpected frame sync during "
           "receive, if FSIG=0 (abort mode)."),
        _f(reg_id, 3, "RFSI", "3", 3, 3, 1, "R/W",
           "Receive Frame Sync Interrupt. Set on each receive frame sync edge."),
        _f(reg_id, 4, "TSIP", "4", 4, 4, 1, "R/W",
           "Transmit Service Interrupt. Set when TX FIFO has space available "
           "(below threshold)."),
        _f(reg_id, 5, "TUEI", "5", 5, 5, 1, "R/W",
           "Transmit Underrun Error Interrupt. Set when TX FIFO is empty but "
           "transmission is active. Indicates the output data may be corrupted."),
        _f(reg_id, 6, "TFEI", "6", 6, 6, 1, "R/W",
           "Transmit Frame Sync Error Interrupt. Set on unexpected frame sync "
           "during transmit, if FSIG=0 (abort mode)."),
        _f(reg_id, 7, "TFSI", "7", 7, 7, 1, "R/W",
           "Transmit Frame Sync Interrupt. Set on each transmit frame sync edge."),
    ]


# =============================================================================
# REGISTER CLASSES
# =============================================================================

def build_register_classes():
    return [
        {
            "id": "REGCLASS_CORE",
            "type": "REG_CLASS",
            "name": "Core MSP Registers",
            "address_start": "000h",
            "address_end": "08Ch",
            "table_1_1_name": "MSP Core Register Block",
            "registers": [],
            "description": "Core operational registers: data, configuration, "
                           "sample rate, flags, DMA, interrupts, multichannel, "
                           "channel enables, I/O delay, and test registers."
        },
        {
            "id": "REGCLASS_ID",
            "type": "REG_CLASS",
            "name": "Identification Registers",
            "address_start": "FE0h",
            "address_end": "FFCh",
            "table_1_1_name": "ARM PrimeCell ID Block",
            "registers": [],
            "description": "ARM PrimeCell peripheral and component identification "
                           "registers. Read-only, factory-programmed. Used to "
                           "identify the IP block type and revision."
        }
    ]


# =============================================================================
# FEATURES (derived from driver capabilities)
# =============================================================================

def build_features():
    defs = [
        # Protocol modes
        ("F_I2S_MODE", "I2S Protocol Mode", ["protocol", "audio"], "P0", None,
         "I2S (Inter-IC Sound) protocol support. Single-phase, MSB-first, "
         "1-bit data delay, frame sync active-low. Default element length 32-bit, "
         "stereo frame of 32 bit clocks. This is the primary audio protocol mode."),
        ("F_PCM_MODE", "PCM Protocol Mode", ["protocol", "audio"], "P0", None,
         "PCM (Pulse Coded Modulation) protocol support. Dual-phase, MSB-first, "
         "0 data delay, frame sync active-high. Default 16-bit elements, "
         "256-clock frame period."),
        ("F_PCM_COMPAND", "PCM Companded Mode", ["protocol", "audio", "companding"], "P1", "F_PCM_MODE",
         "Companded PCM mode with hardware µ-law or A-law compression/expansion. "
         "Single-phase, 8-bit elements. Used for voice-band telephony."),

        # Companding
        ("F_COMPANDING", "Hardware Companding", ["companding"], "P1", None,
         "Hardware companding support via the DTYP field in TCF/RCF. "
         "Supports linear, µ-law, and A-law modes. Controlled by DCM bit in GCR."),

        # Data transfer
        ("F_DMA", "DMA Transfer", ["data_transfer", "dma"], "P0", None,
         "DMA-based data transfer using the DMACR register. TX and RX DMA can be "
         "enabled independently. The driver enables DMA for both directions during "
         "the open sequence. DMA base address is MSP_DR (offset 0x00)."),
        ("F_FIFO", "TX/RX FIFO", ["data_transfer"], "P0", None,
         "Transmit and receive FIFOs. 32 entries deep (based on flush loop limit). "
         "FIFO enable controlled via RFFEN/TFFEN in GCR. Status available via "
         "FLR register (empty/full flags)."),
        ("F_DATA_SIZES", "Configurable Data Sizes", ["data_transfer"], "P0", None,
         "Supports 8, 10, 12, 14, 16, 20, 24, and 32-bit element sizes. "
         "Configured via P1ELEN/P2ELEN in TCF/RCF. Data size affects DR access width."),

        # Clock and sync
        ("F_CLOCK_GEN", "Clock Generation", ["clock"], "P0", None,
         "Built-in sample rate generator (SRG) produces bit clock and frame sync. "
         "Input clock is APB (48 MHz default). Bit clock = f_input / (SCKDIV+1). "
         "Frame sync generated with configurable width and period."),
        ("F_FRAME_SYNC", "Frame Synchronization", ["clock", "protocol"], "P0", "F_CLOCK_GEN",
         "Frame sync generation and detection. Configurable polarity (active high/low), "
         "width (FRWID), and period (FRPER). Unexpected frame sync can abort transfer "
         "or be ignored (FSIG bit)."),
        ("F_EXT_CLOCK", "External Clock Input", ["clock"], "P1", "F_CLOCK_GEN",
         "MSP can use external bit clock and frame sync instead of internal SRG. "
         "Selected via RCKSEL/TCKSEL and RFSSEL/TFSSEL bits in GCR."),

        # Multichannel
        ("F_MULTICHANNEL", "Multichannel / TDM", ["multichannel"], "P1", None,
         "Time-Division Multiplexing (TDM) support. Up to 128 channels (4 x 32-bit "
         "enable masks in TCE0-3 and RCE0-3). Only supported in single-phase mode. "
         "Per-channel enable/disable for both TX and RX independently."),
        ("F_RX_COMPARISON", "RX Data Comparison", ["multichannel"], "P2", "F_MULTICHANNEL",
         "Receive data comparison mode. Compares incoming data against RCV value "
         "(masked by RCM). Can generate interrupt on match or non-match. "
         "Used for channel identification in TDM applications."),

        # Bus modes
        ("F_DUAL_PHASE", "Dual Phase Protocol", ["protocol"], "P1", None,
         "Dual-phase protocol support via P2EN bit. Phase 1 and phase 2 can have "
         "independent element/frame lengths. Phase 2 can start immediately after "
         "phase 1 or wait for next frame sync (P2SM bit)."),
        ("F_LOOPBACK", "Loopback Mode", ["test", "diagnostics"], "P2", None,
         "Internal loopback mode (LBM bit in GCR). TX output is routed back to "
         "RX input internally. Used for self-test and diagnostics without external "
         "connections. Also used transiently during shutdown to drain FIFOs."),
        ("F_SPI_COMPAT", "SPI Compatibility", ["protocol"], "P2", None,
         "SPI-compatible mode with configurable clock mode (SPICKM) and burst "
         "mode (SPIBME). Allows MSP to communicate with SPI peripherals."),

        # Interrupt
        ("F_INTERRUPT", "Interrupt System", ["interrupt"], "P0", None,
         "8 interrupt sources: RX/TX service, RX overrun, TX underrun, RX/TX "
         "frame sync, RX/TX frame sync error. Controlled by IMSC register. "
         "Status in RIS (raw) and MIS (masked). Clear via ICR."),

        # Power and instances
        ("F_MULTI_INSTANCE", "Multiple MSP Instances", ["platform"], "P1", None,
         "DB8500 SoC has 4 MSP instances: MSP0 at 0x80123000, MSP1 at 0x80124000, "
         "MSP2 at 0x80117000, MSP3 at 0x80125000. Each is independently configurable. "
         "The driver manages a per-instance state machine (IDLE→CONFIGURED→RUNNING)."),
        ("F_IO_DELAY", "I/O Delay Configuration", ["platform", "timing"], "P2", None,
         "Configurable I/O pad delay via IODLY register. Platform-specific value "
         "written during open sequence."),
        ("F_ENDIANNESS", "Configurable Endianness", ["data_transfer"], "P1", None,
         "Byte order configurable per direction (TX/RX) via ENDN bit in TCF/RCF. "
         "Also supports byte/half-word swap via TBSWAP field."),
        ("F_TEST_MODE", "Integration Test Mode", ["test"], "P2", None,
         "Integration test control via ITCR register. Test mode enables direct "
         "FIFO access through TSTDR and test I/O via ITIP/ITOP. Used by driver "
         "to flush TX FIFO during shutdown sequence."),
    ]
    
    features = []
    for fid, fname, groups, prio, parent, desc in defs:
        features.append({
            "id": fid,
            "type": "FEATURE",
            "name": fname,
            "description": desc,
            "source": {"driver_file": "ux500-msp-i2s.c"},
            "extras": {
                "groups": groups,
                "priority": prio,
                "parent_id": parent or "",
                "tables": [],
                "figures": [],
                "registers": [],
                "spec_sections": []
            }
        })
    return features


# =============================================================================
# HD SEQUENCES (derived from driver functions)
# =============================================================================

def build_hd_sequences():
    seqs = [
        ("HDS_MSP_OPEN", "MSP Open / Configure",
         ["initialization"],
         "Full MSP initialization: configure GCR (clocks, FIFO, loopback, "
         "sync selection), set protocol descriptors (TCF/RCF), configure SRG "
         "(bit clock divider, frame width/period), optionally configure multichannel "
         "(MCR, TCE0-3, RCE0-3, RCV, RCM), enable DMA (DMACR), set IODLY, "
         "enable frame generator, flush both FIFOs, set state to CONFIGURED.",
         ["F_I2S_MODE", "F_PCM_MODE", "F_CLOCK_GEN", "F_DMA", "F_FIFO"]),
        ("HDS_MSP_TRIGGER", "MSP Trigger Start/Stop",
         ["data_transfer"],
         "ALSA trigger handler. On START/RESUME/PAUSE_RELEASE: sets TXEN or RXEN "
         "in GCR to begin data flow. On STOP/SUSPEND/PAUSE_PUSH: calls "
         "disable_msp_tx/rx which clears enable bits, disables DMA, and masks "
         "interrupts.",
         ["F_DMA", "F_INTERRUPT"]),
        ("HDS_MSP_CLOSE", "MSP Close / Shutdown",
         ["shutdown"],
         "MSP shutdown sequence. Disables TX/RX (with loopback-assisted drain if "
         "both directions active), disables DMA and interrupts. If both directions "
         "now idle: disables SRG + frame gen, zeroes GCR, TCF, RCF, DMACR, SRG, "
         "MCR, RCM, RCV, and all TCE/RCE registers. Sets state to IDLE.",
         ["F_FIFO", "F_LOOPBACK"]),
        ("HDS_FLUSH_TX", "TX FIFO Flush",
         ["data_transfer", "shutdown"],
         "Drains TX FIFO using integration test mode. Enables TX, then sets "
         "ITCR (ITEN+TESTFIFO), reads TSTDR in a loop until TFE flag is set "
         "or limit (32 reads) reached, then clears ITCR and restores GCR.",
         ["F_FIFO", "F_TEST_MODE"]),
        ("HDS_FLUSH_RX", "RX FIFO Flush",
         ["data_transfer", "shutdown"],
         "Drains RX FIFO by temporarily enabling RX, then reading DR in a loop "
         "until RFE (RX FIFO Empty) flag is set or limit (32 reads) reached, "
         "then restores original GCR value.",
         ["F_FIFO"]),
        ("HDS_SETUP_BITCLK", "Bit Clock Setup",
         ["clock", "initialization"],
         "Configures the sample rate generator. Disables SRG, calculates SCKDIV "
         "from f_inputclk / (frame_freq * clocks_per_frame), sets FRWID and FRPER, "
         "writes SRG register, waits 100µs, enables SRG, waits another 100µs. "
         "The 100µs delays allow the PLL to stabilize.",
         ["F_CLOCK_GEN", "F_FRAME_SYNC"]),
    ]
    
    hd_seqs = []
    for sid, sname, groups, desc, uses in seqs:
        hd_seqs.append({
            "id": sid,
            "type": "HD_SEQUENCE",
            "name": sname,
            "description": desc,
            "source": {"driver_file": "ux500-msp-i2s.c"},
            "extras": {
                "groups": groups + ["host_driver_sequence"],
                "uses_features": uses,
                "tables": [],
                "figures": [],
                "spec_sections": []
            }
        })
    return hd_seqs


# =============================================================================
# RELATIONS
# =============================================================================

def build_relations(registers, reg_classes, features, hd_sequences):
    rels = []
    rel_id = 0

    # BELONGS_TO: register → register class
    for reg in registers:
        rel_id += 1
        rels.append({
            "id": f"R{rel_id:04d}",
            "type": "BELONGS_TO",
            "source_node": reg["id"],
            "target_node": reg["class_id"],
            "description": f"{reg['name'].split(' — ')[0]} belongs to register class {reg['class_id']}"
        })

    # PART_OF: child features → parent features
    for feat in features:
        parent = feat["extras"].get("parent_id", "")
        if parent:
            rel_id += 1
            rels.append({
                "id": f"R{rel_id:04d}",
                "type": "PART_OF",
                "source_node": feat["id"],
                "target_node": parent,
                "description": f"{feat['name']} is part of {parent}"
            })

    # USES_FEATURE: HD sequences → features
    for seq in hd_sequences:
        for fid in seq["extras"].get("uses_features", []):
            rel_id += 1
            rels.append({
                "id": f"R{rel_id:04d}",
                "type": "USES_FEATURE",
                "source_node": seq["id"],
                "target_node": fid,
                "description": f"{seq['name']} uses feature {fid}"
            })

    return rels


# =============================================================================
# ASSEMBLE METADATA
# =============================================================================

def build_metadata():
    registers = build_registers()
    reg_classes = build_register_classes()
    features = build_features()
    hd_sequences = build_hd_sequences()
    relations = build_relations(registers, reg_classes, features, hd_sequences)

    # Convert registers to node format
    reg_nodes = []
    total_fields = 0
    for reg in registers:
        fields = reg.pop("fields", [])
        desc = reg.pop("description", "")
        total_fields += len(fields)
        node = {
            "id": reg["id"],
            "type": "REGISTER",
            "name": reg["name"],
            "description": desc,
            "source": reg["source"],
            "extras": {
                "offset_hex": reg["offset"],
                "class_id": reg["class_id"],
                "spec_section": reg.get("spec_section", ""),
                "spec_table": reg.get("spec_table", ""),
                "fields": fields
            }
        }
        reg_nodes.append(node)

    # Convert reg classes to node format
    rc_nodes = []
    for rc in reg_classes:
        desc = rc.pop("description", "")
        rc_nodes.append({
            "id": rc["id"],
            "type": "REG_CLASS",
            "name": rc["name"],
            "description": desc,
            "source": {},
            "extras": {
                "address_start": rc["address_start"],
                "address_end": rc["address_end"],
                "table_1_1_name": rc.get("table_1_1_name", ""),
                "registers": [r["id"] for r in reg_nodes if r["extras"]["class_id"] == rc["id"]]
            }
        })

    # All nodes
    nodes = reg_nodes + rc_nodes + features + hd_sequences

    # Compute stats
    by_type = {}
    for n in nodes:
        t = n["type"]
        by_type[t] = by_type.get(t, 0) + 1
    # Add empty types for schema compatibility
    for t in ["TABLE", "FIGURE", "SPEC_CHUNK"]:
        by_type.setdefault(t, 0)

    rels_by_type = {}
    for rel in relations:
        t = rel["type"]
        rels_by_type[t] = rels_by_type.get(t, 0) + 1

    metadata = {
        "metadata_version": "2.0.0",
        "spec_info": {
            "name": "Ux500 MSP I2S Controller",
            "version": "DB8500",
            "page_offset": 0
        },
        "extraction_info": {
            "extracted_date": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pipeline": "driver_source_analysis",
            "sources": {
                "driver_header": "driver_sources/ux500-msp-i2s.h",
                "driver_source": "driver_sources/ux500-msp-i2s.c",
                "device_tree": "driver_sources/device-tree-binding.txt",
                "platform_data": "driver_sources/cpu-db8500.c"
            },
            "statistics": {
                "total_nodes": len(nodes),
                "by_type": by_type,
                "total_relations": len(relations),
                "relations_by_type": rels_by_type,
                "total_registers": by_type.get("REGISTER", 0),
                "total_fields": total_fields,
                "total_features": by_type.get("FEATURE", 0),
                "total_hd_sequences": by_type.get("HD_SEQUENCE", 0)
            }
        },
        "nodes": nodes,
        "relations": relations
    }
    return metadata


def main():
    metadata = build_metadata()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    stats = metadata["extraction_info"]["statistics"]
    print(f"Generated: {OUT}")
    print(f"  Nodes:     {stats['total_nodes']}")
    print(f"  Relations: {stats['total_relations']}")
    print(f"  Registers: {stats['total_registers']} ({stats['total_fields']} fields)")
    print(f"  Features:  {stats['total_features']}")
    print(f"  HD Seqs:   {stats['total_hd_sequences']}")
    print(f"  By type:   {stats['by_type']}")
    print(f"  Rels:      {stats['relations_by_type']}")


if __name__ == "__main__":
    main()
