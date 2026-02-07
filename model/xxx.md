# Features

General description

xxx controller is an advanced host controller compliant with mmc 4.51 and sdhost 3.0.

Handles mmc/sd/sdio protocols at transmission level, packing data, adding cyclic redundancy check (CRC), start/end bit, and checking for transaction format correctness.

Controlelr provides programmed IO method and DMA data transfer method. In programmed IO method, the host processor transfers data using the Buffer data port register. Host controller supports both SDMA and ADMA2. ADMA2 is enabled by user using programming bit. DMA allows a peripheral to read or write memory without interention from the CPU. The controllers host controller system address register points to the first data address, and data is then accessed sequencually from that address.

Key features

* Compliance
    * MMC specification version 4.51
    * SD Host Controller Standard specification version 3.00
    * SDIO Card specification version 3.0
    * SD Memory Card specification version 3.01
    * SD Memory Card Security specification version 1.01

* System/Host interface
    * Data transfer using PIO mode on the host bus slave interface, using DMA mode on the host bus master interface
    * System/Host interface clock frequency is 100 Mhz (max)

* MMC card interface
    * EMMC card clock frequency is 50 Mhz
    * Up to 400 Mbits (50 Mbytes) per second data rate usng 8 bit parallel data lines (mmc8 bit SDR mode)
    * Up to 800 Mbits (100 MBytes) per second data rate using 8 bit parallel data lines (mmc8 bit DDR mode)
    * Transfers the data in 1 bit, 4 bit and 8 bit modes and SPI mode.
    * Cyclic redundancy check CRC7 for command and CRC16 for data integrity
    * Supports MMC plus and MMC mobile

* SD/SDIO card interface
    * Host clock rate variable between 0 and 50 Mhz
    * Transfers the data in 1 bit and 4 bit SD modes and SPI mode
    * Transfers the data in High and Default speed modes
    * Up to 200 Mbits (25 Mbytes) per second data rate in High speed mode
    * Cyclic Redundancy Check CRC7 for command and CRC16 for data integrity
    * Variable-length data transfers
    * Performs Read Wait control, Suspend/Resume operation SDIO CARD
    * Designed to work with I/O cards, Read Only cards and Read/Write cards
    * Supports Read Wait control, Suspend/Resume operation

* Miscellaneous
    * Handle the FIFO overrun and underrun condition by stopping eMMC card clock

# Registers

0x000: SDMA System address / Argument 2 Register
0x004: Block Size Register
0x006: Block Count Register
0x008: Argument 1 Register
0x00C: Transfer Mode Register
0x00E: Command Register
0x010 + n *0x2: Response Register n (n = 0 to 7 )
0x020: Data Port Register
0x024: Present State Register
0x028: Host Control 1 Register
0x029: Power Control Register
0x02A: Block Gap Control Register
0x02B: Wakeup Control Register
0x02C: Clock Control Register
0x02E: Timeout Control Register
0x02F: Software Reset Register
0x030: Normal Interrupt Status Register
0x032: Error Interrupt Status Register
0x034: Normal Interrupt Status Enable Register
0x036: Error Interrupt Status Enable Register
0x038: Normal Interrupt Signal Enable Register
0x03A: Error Interrupt Signal Enable Register
0x03C: Auto CMD12 Error Status Register
0x03E: Host Control 2 Register
0x040: Capabilities Register
0x044: Capabilities Upper Register
0x048: Maximum Current Capabilities Register
0x04C: Maximum Current Capabilities Upper Register
0x050: Force Event for auto CMD error status Register
0x052: Force Event for error interrupt status Register
0x054: ADMA Error Status Register
0x058 + n*0x2: ADMA System Address Register (n 0 to 3)
0x060 + n*0x2: Preset Value for CMD Register (n 0 to 7)
