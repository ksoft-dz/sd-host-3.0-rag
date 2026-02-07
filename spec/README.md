# Spec Sections Extraction Pipeline

This folder contains tools and outputs for extracting hierarchical section content from the SD Host 3.0 specification PDF.

## Quick Start

```powershell
# 1. Extract ToC only (quick scan)
python extract_sections.py --toc-only

# 2. Full extraction with 4 workers
python extract_sections.py --workers 4

# 3. Fill in missing pages from previous run
python extract_sections.py --fill-missing --skip-toc --workers 4

# 4. Process specific pages only
python extract_sections.py --pages 86,108,113 --skip-toc --workers 4
```

## Scripts

### `extract_sections.py`
Main extraction script that processes the PDF to extract hierarchical sections and text chunks.

**Arguments**:
| Argument | Description |
|----------|-------------|
| `--start-page N` | Start at PDF page N |
| `--end-page N` | End at PDF page N |
| `--pages "N,M,..."` | Process specific pages only |
| `--fill-missing` | Only process pages without chunks |
| `--skip-toc` | Skip ToC extraction, use existing |
| `--skip-chunks` | Skip chunk extraction |
| `--toc-only` | Only extract ToC structure |
| `--dry-run` | Don't call LLM |
| `--model haiku\|sonnet\|opus` | LLM model (default: sonnet) |
| `--workers N` | Parallel workers (default: 4) |

**Examples**:

```powershell
# Full extraction from scratch
python extract_sections.py --workers 4

# Just see ToC structure (fast, no LLM costs)
python extract_sections.py --toc-only

# Process pages 50-100 only
python extract_sections.py --start-page 50 --end-page 100 --skip-toc

# Fill in pages that failed in previous run
python extract_sections.py --fill-missing --skip-toc --workers 4

# Retry specific failed pages
python extract_sections.py --pages 86,108,113,114,136 --skip-toc --workers 4

# Use cheaper Haiku model for bulk processing
python extract_sections.py --model haiku --workers 4
```

## Output Files

| File | Description |
|------|-------------|
| `sections.json` | Complete hierarchical sections with chunks |
| `toc_raw.json` | Raw ToC structure (112 sections) |
| `context.md` | Schema documentation |

## Schema: sections.json

```json
{
  "_metadata": {
    "source_pdf": "sd_host_3_00.pdf",
    "total_sections": 112,
    "total_chunks": 287,
    "chunk_target_words": 200,
    "chunk_max_words": 250
  },
  "sections": {
    "2.1.3": {
      "id": "SEC_2_1_3",
      "section_number": "2.1.3",
      "title": "Power Control Register",
      "level": 3,
      "hierarchy": {
        "parent": "SEC_2_1",
        "children": []
      },
      "source": {
        "spec_page_start": 53,
        "spec_page_end": 54,
        "pdf_page_start": 64,
        "pdf_page_end": 65
      },
      "references": {
        "tables": ["TABLE_2_17"],
        "figures": ["FIG_2_15"],
        "related": []
      },
      "index": {
        "keywords": ["power", "voltage", "bus"],
        "technical_terms": ["offset 029h", "RW"]
      },
      "abstract": "Section-level summary...",
      "word_count": 342,
      "chunks": [
        {
          "chunk_id": "SEC_2_1_3_C0",
          "chunk_index": 0,
          "spec_page": 53,
          "word_count": 180,
          "abstract": "Chunk summary...",
          "raw": "Actual extracted text..."
        }
      ],
      "extraction": {
        "status": "COMPLETED",
        "confidence": 0.95,
        "validated": false
      }
    }
  }
}
```

## Section Numbering

| Format | Example | Description |
|--------|---------|-------------|
| Numeric | `1`, `2.1`, `2.1.3` | Regular sections |
| Appendix | `Appendix_A`, `Appendix_B` | Top-level appendices |
| Appendix Sub | `A.1`, `C.3.2` | Appendix subsections |

## Chunk Design

- **Target**: 200 words per chunk
- **Max**: 250 words (hard limit)
- **Split points**: Paragraph boundaries, numbered lists
- **Never split**: Mid-sentence or mid-paragraph
- **Content**: Verbatim text only, no summarization

## Notes

- Page offset: `pdf_page = spec_page + 11`
- Rate limiting: Built-in delays to avoid API limits
- Retries: 3 attempts per page with exponential backoff
- Some pages only have tables/figures (marked as "skipped - only tables/figures")
