# Figures Extraction Pipeline

This folder contains tools and outputs for extracting and transcribing figures from the SD Host 3.0 specification PDF.

## Quick Start

```powershell
# 1. Extract figure inventory from PDF
python extract_figures_map.py

# 2. Extract figure images
python extract_figure_images.py

# 3. Convert figures to PlantUML using LLM vision
python convert_figures_to_plantuml.py --workers 4

# 4. Generate abstracts for all figures
python generate_figure_abstracts.py
```

## Scripts

### `extract_figures_map.py`
Scans the PDF and builds an inventory of all 83 figures with their locations.

**Output**: `figures_page_map.json`

```powershell
python extract_figures_map.py
```

### `extract_figure_images.py`
Extracts figure images from PDF pages.

**Output**: `images/FIG_X_Y.png`

```powershell
python extract_figure_images.py
```

### `convert_figures_to_plantuml.py`
Uses Claude LLM with vision to convert figure images to PlantUML text format.

**Arguments**:
- `--workers N` - Number of parallel workers (default: 4)
- `--skip-existing` - Skip figures that already have PlantUML files
- `--figure FIG_ID` - Process specific figure only

**Output**: `plantuml/FIG_X_Y.puml`

```powershell
# Convert all figures with 4 workers
python convert_figures_to_plantuml.py --workers 4

# Skip already converted figures
python convert_figures_to_plantuml.py --skip-existing --workers 4

# Convert specific figure
python convert_figures_to_plantuml.py --figure FIG_1_4
```

### `generate_figure_abstracts.py`
Generates text abstracts/summaries for each figure using LLM.

**Output**: Updates `figures_page_map.json` with abstracts

```powershell
python generate_figure_abstracts.py
```

## Output Files

| File | Description |
|------|-------------|
| `figures_page_map.json` | Index of all 83 figures with metadata |
| `plantuml/FIG_X_Y.puml` | PlantUML transcriptions |
| `images/FIG_X_Y.png` | Extracted figure images |
| `conversion.log` | Conversion process log |
| `abstract_generation.log` | Abstract generation log |
| `failed_figures.md` | Figures that failed conversion |

## Schema: figures_page_map.json

```json
{
  "_metadata": {
    "source_pdf": "sd_host_3_00.pdf",
    "total_figures": 83,
    "page_offset": 11,
    "transcription_progress": {
      "completed": 75,
      "in_progress": 0,
      "not_started": 5,
      "skipped": 3
    }
  },
  "figures": [
    {
      "id": "FIG_1_4",
      "spec_reference": "Figure 1-4",
      "title": "Suspend and Resume Mechanism",
      "spec_page": 14,
      "definition_page": 25,
      "transcription": {
        "status": "COMPLETED",
        "text_file": "plantuml/FIG_1_4.puml",
        "image_file": "images/FIG_1_4.png",
        "format": "plantuml",
        "validated": false
      },
      "abstract": "State diagram showing suspend/resume transitions..."
    }
  ]
}
```

## Figure Types

| Type | Description | Example |
|------|-------------|---------|
| Block Diagram | System architecture views | FIG_1_1 |
| State Diagram | State machine flows | FIG_1_4 |
| Register Layout | Bit field layouts | FIG_2_15 |
| Timing Diagram | Signal timing relationships | FIG_2_40 |
| Flowchart | Process flows | FIG_3_1 |

## Notes

- Page offset: `pdf_page = spec_page + 11`
- Figures are numbered as `FIG_X_Y` where X is section, Y is sequence
- PlantUML files can be rendered at https://www.plantuml.com/plantuml/
- Some complex figures may need manual review - check `failed_figures.md`
