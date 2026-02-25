# Ux500 MSP I2S RAG — Change History

## 2026-02-24 ~18:05 UTC — Linux Driver Coverage Analysis (Phase 2 + Phase 3)

### Phase 2: metadata.json — Feature coverage status & tagging

- Added `coverage` field to all 20 FEATURE nodes with `status`, `notes` (evidence), and `implemented_in` (driver functions)
- Added `not_implemented_in_linux_driver` boolean tag to every feature's `extras`
- Populated `registers` arrays (previously empty) with correct register IDs for each feature

**Coverage results** (from analyzing `ux500-msp-i2s.c`, `ux500_msp_dai.c`, `ux500-msp-i2s.h`, `ux500_msp_dai.h`):

| Status           | Count | Features |
|------------------|-------|----------|
| IMPLEMENTED      | 16    | F_I2S_MODE, F_PCM_MODE, F_DMA, F_FIFO, F_DATA_SIZES, F_CLOCK_GEN, F_FRAME_SYNC, F_EXT_CLOCK, F_MULTICHANNEL, F_DUAL_PHASE, F_LOOPBACK, F_INTERRUPT, F_MULTI_INSTANCE, F_IO_DELAY, F_ENDIANNESS, F_TEST_MODE |
| PARTIAL          | 2     | F_PCM_COMPAND (code exists but DAI never triggers it), F_COMPANDING (always LINEAR) |
| NOT_IMPLEMENTED  | 2     | F_SPI_COMPAT (no code in .c files), F_RX_COMPARISON (always disabled in DAI) |

### Phase 3: intermediates/features.json — Created

- Generated `intermediates/features.json` following the SDMMC template structure
- Contents: 20 features, 6 HD sequences, 18 relations (4 PART_OF + 14 USES_FEATURE)
- Each feature includes: id, type, name, description, groups, priority, parent_id, registers, index_keywords, confidence, validation_status, extras (with `not_implemented_in_linux_driver` + `linux_driver_coverage`)

### Phase 3: metadata_api.py — New query functions

Added 3 new methods:

- `list_features_not_implemented_in_driver` — returns features with `not_implemented_in_linux_driver=true`
- `list_features_by_driver_coverage [status]` — filter features by IMPLEMENTED / PARTIAL / NOT_IMPLEMENTED
- `get_feature_registers <feature_id>` — returns resolved register details (id, name, offset) for a feature

### Files modified

- `metadata/metadata.json` — coverage fields, not_implemented tags, register references on all 20 features
- `metadata/metadata_api.py` — 3 new query methods
- `intermediates/features.json` — new file (generated from metadata.json)
