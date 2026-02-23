# shared — Common Utilities

## Purpose

Shared modules used by all pipeline phases. No script is run directly — these are imported by Phase 1/2/3 scripts.

## Modules

| Module | What It Does |
|--------|-------------|
| `config.py` | Loads `spec_config.yaml`, provides typed accessors for every config section (register offsets, table hints, validation rules, etc.). Defines `PIPELINE_ROOT`. |
| `llm_client.py` | Unified Anthropic Claude API wrapper. Handles retries (exponential backoff), rate limiting (configurable delay), vision/text calls, and consistent error handling. All LLM calls in the pipeline go through this. |
| `pdf_utils.py` | PyMuPDF (fitz) wrappers: page text extraction, image rendering, multi-page image stitching (vertical concat), image downscale for API limits (max 7500px). |
| `data_classes.py` | Node/Relation data classes mirroring v1 schema for backward compatibility. |
| `utils.py` | General helpers: JSON load/save, keyword extraction, offset normalization (`001h` → `001`), formatted printing (`print_step`, `print_banner`), duration formatting. |

## Key Config Accessors (config.py)

| Function | Returns |
|----------|---------|
| `load_config()` | Full parsed YAML dict |
| `get_pdf_path()` | Path to source PDF |
| `get_register_offsets(config)` | Dict of offset → {name, section, table?} |
| `get_register_classes(config)` | List of register class defs |
| `get_exclude_tables(config)` | Set of table IDs to skip for register extraction |
| `get_table_multi_page_config(config)` | Multi-page detection settings |
| `find_matching_hint(config, title)` | Find extraction hint matching a table title |
| `get_validation_config(config)` | Validation rules and thresholds |
| `get_tables_csv_dir()` | Path to `intermediates/tables_csv/` |
| `get_intermediates_dir()` | Path to `intermediates/` |

## LLM Client Features

- **Rate limiting**: Configurable delay between calls (default 1.5s)
- **Retries**: 3 attempts with exponential backoff on API errors
- **Vision support**: Sends base64-encoded images for table/figure extraction
- **Stats tracking**: Tracks call counts, tokens, errors per session
- **Model override**: CLI `--model` flag propagates through to all LLM calls

## Spec-Specific Notes

- **Page offset**: 12 (spec_page + 12 = PDF page 1-indexed)
- **PDF**: `sd_phy_rag/Part_1_Physical_Layer_Simplified_Specification_Ver_3.01_Final_100518.pdf`
