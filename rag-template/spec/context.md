# Specification Sections Context

## Purpose
This folder contains the document structure and text chunks from the source PDF.

## Files
- `sections.json` - Document structure, hierarchy, and text chunks

## JSON Structure

### Section Entry
```json
{
  "id": "SEC_1_2",
  "section_number": "1.2",
  "title": "Section Title",
  "level": 2,
  "hierarchy": {
    "parent": "SEC_1",
    "children": ["SEC_1_2_1", "SEC_1_2_2"]
  },
  "source": {
    "spec_page_start": 5,
    "spec_page_end": 8,
    "pdf_page_start": 16,
    "pdf_page_end": 19
  },
  "references": {
    "tables": ["TABLE_1_3"],
    "figures": ["FIG_1_5"],
    "related": ["SEC_2_1"]
  },
  "chunks": [...]
}
```

### Chunk Entry
```json
{
  "id": "SEC_1_2_C1",
  "chunk_index": 0,
  "text": "Raw text extracted from PDF...",
  "abstract": "LLM-generated summary for embedding...",
  "word_count": 195,
  "embedding_ready": true
}
```

## Chunking Strategy
- Target: 200 words per chunk
- Maximum: 250 words per chunk
- Preserve paragraph boundaries
- Keep related content together

## Hierarchy Levels
- Level 1: Main chapters (1, 2, 3...)
- Level 2: Major sections (1.1, 1.2...)
- Level 3: Subsections (1.1.1, 1.1.2...)
- Level 4+: Deep subsections

## ID Conventions
- Section: `SEC_{number}` where number uses underscores (e.g., SEC_1_2_3)
- Chunk: `SEC_{section}_C{index}` (e.g., SEC_1_2_C0, SEC_1_2_C1)

## Workflow
1. Extract Table of Contents from PDF
2. Build section hierarchy
3. Extract text content for each section
4. Chunk text into embedding-sized pieces
5. Generate abstracts for each chunk
6. Identify cross-references to tables/figures
