# Figures Extraction Context

## Purpose
This folder contains extracted figures/diagrams from the source PDF specification.

## Files
- `figures_page_map.json` - Metadata about all figures (location, status, references)
- `plantuml/` - PlantUML transcriptions of diagrams
- `images/` - Extracted figure images (optional)

## JSON Structure

### Figure Entry
```json
{
  "id": "FIG_1_1",
  "spec_reference": "Figure 1-1",
  "title": "Architecture Overview",
  "spec_page": 1,
  "definition_page": 12,
  "referenced_on_pages": [12, 50],
  "abstract": "LLM-generated summary for embeddings",
  "transcription": {
    "status": "COMPLETED",
    "text_file": "plantuml/FIG_1_1.puml",
    "format": "plantuml"
  }
}
```

### Multi-Page Figures
Figures can span multiple pages (e.g., large diagrams, state machines). Use these fields:
- `spec_page`: First page where figure appears
- `spec_page_end`: Last page (if multi-page)
- `definition_page`: First PDF page
- `definition_page_end`: Last PDF page (if multi-page)

```json
{
  "id": "FIG_2_10",
  "spec_page": 15,
  "spec_page_end": 17,
  "definition_page": 26,
  "definition_page_end": 28
}
```

### Status Values
- `NOT_STARTED` - Figure identified but not transcribed
- `IN_PROGRESS` - Transcription underway
- `COMPLETED` - Successfully transcribed
- `SKIPPED` - Figure not suitable for transcription

### Transcription Formats
- `plantuml` - PlantUML diagram code
- `mermaid` - Mermaid diagram code
- `text` - Plain text description
- `ascii` - ASCII art representation

## Figure Types
- **Block Diagrams** - System architecture, components
- **State Machines** - State transition diagrams
- **Timing Diagrams** - Signal timing relationships
- **Flowcharts** - Process flows, algorithms
- **Register Maps** - Memory/register layouts

## Workflow
1. Extract figure locations from PDF
2. Populate figures_page_map.json with metadata
3. Transcribe diagrams to code format (PlantUML/Mermaid)
4. Validate transcription matches source
5. Generate abstracts for embedding

## Naming Convention
- `FIG_{chapter}_{number}.puml`
- Example: `FIG_1_1.puml`, `FIG_2_10.puml`
