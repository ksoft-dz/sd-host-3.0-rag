#!/usr/bin/env python3
"""
Phase 2c: Extract figures from PDF as PlantUML diagrams.

For each figure found in discovery.json:
1. Render the PDF page as an image
2. Send to LLM vision to transcribe as PlantUML
3. Generate abstract
4. Save PlantUML + update figures_page_map.json

Depends on: Phase 1 discovery.json
Output: intermediates/figures_page_map.json + intermediates/figures_plantuml/*.puml
"""

import json
import re
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.config import (
    get_page_offset, get_llm_config, get_intermediates_dir,
    get_figures_output_dir, get_figures_images_dir
)
from shared.pdf_utils import open_pdf, render_page_to_image
from shared.llm_client import LLMClient
from shared.utils import load_json, save_json, print_step


def extract_figures(config: dict, pdf_path: Path,
                    skip_existing: bool = False,
                    model: str = None,
                    workers: int = None):
    """Main entry point for figure extraction."""
    intermediates = get_intermediates_dir()
    plantuml_dir = get_figures_output_dir()
    images_dir = get_figures_images_dir()
    output_path = intermediates / "figures_page_map.json"
    
    # Load discovery
    discovery_path = intermediates / "discovery.json"
    if not discovery_path.exists():
        print("ERROR: Run 'discover' phase first")
        return
    discovery = load_json(discovery_path)
    figures = discovery.get("toc", {}).get("figures", [])
    
    if not figures:
        print("  No figures found in discovery.json")
        return
    
    # Load existing map
    existing_map = {}
    if skip_existing and output_path.exists():
        existing_data = load_json(output_path)
        for f in existing_data.get("figures", []):
            existing_map[f["id"]] = f
    
    # Setup
    page_offset = get_page_offset(config)
    llm_config = get_llm_config(config)
    num_workers = workers or llm_config.get("max_workers", 4)
    
    doc = open_pdf(pdf_path)
    llm = LLMClient(config, model_override=model)
    
    # Render page images
    print_step("1/2", f"Rendering {len(figures)} figure pages as images...")
    page_images = {}
    for figure in figures:
        pdf_page = figure["definition_page"] - 1
        if pdf_page not in page_images:
            img_bytes = render_page_to_image(doc, pdf_page, dpi=200)
            page_images[pdf_page] = img_bytes
            
            img_path = images_dir / f"page_{pdf_page + 1}.png"
            if not img_path.exists():
                img_path.write_bytes(img_bytes)
    
    doc.close()
    
    # Convert figures
    print_step("2/2", f"Converting figures to PlantUML via LLM vision ({num_workers} workers)...")
    
    results = []
    completed = 0
    total = len(figures)
    
    for figure in figures:
        fig_id = figure["id"]
        
        # Skip if already done
        if skip_existing and fig_id in existing_map:
            existing = existing_map[fig_id]
            if existing.get("transcription", {}).get("status") == "COMPLETED":
                results.append(existing)
                completed += 1
                continue
        
        pdf_page = figure["definition_page"] - 1
        img_bytes = page_images.get(pdf_page, b"")
        
        if not img_bytes:
            figure["transcription"] = {"status": "FAILED", "error": "No image"}
            results.append(figure)
            completed += 1
            continue
        
        try:
            plantuml_text, abstract = _convert_figure_to_plantuml(llm, figure, img_bytes)
            
            # Save PlantUML
            puml_path = plantuml_dir / f"{fig_id}.puml"
            puml_path.write_text(plantuml_text, encoding='utf-8')
            
            figure["transcription"] = {
                "status": "COMPLETED",
                "plantuml_file": str(puml_path.relative_to(intermediates.parent)),
                "model": llm.model
            }
            figure["abstract"] = abstract
            
        except Exception as e:
            figure["transcription"] = {
                "status": "FAILED",
                "error": str(e)[:200]
            }
        
        results.append(figure)
        completed += 1
        if completed % 5 == 0 or completed == total:
            print(f"    Figures: {completed}/{total}")
    
    # Build output
    success = sum(1 for f in results if f.get("transcription", {}).get("status") == "COMPLETED")
    output = {
        "_metadata": {
            "source": config["spec"]["name"],
            "extraction_date": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "total_figures": len(results),
            "transcribed": success,
            "failed": len(results) - success,
            "llm_stats": llm.stats
        },
        "figures": results
    }
    
    save_json(output, output_path)
    print(f"  Figures: {success}/{len(results)} transcribed to PlantUML")


def _convert_figure_to_plantuml(llm: LLMClient, figure: dict, image_data: bytes) -> tuple:
    """Convert a figure image to PlantUML using LLM vision.
    
    Returns:
        (plantuml_text, abstract)
    """
    title = figure.get("title", figure["spec_reference"])
    
    system_prompt = """You are a diagram transcription specialist. Given an image of a figure from a hardware specification:

1. Identify the diagram type (state diagram, timing diagram, block diagram, flowchart, register layout, etc.)
2. Transcribe it as PlantUML
3. Provide a 1-sentence abstract

Rules:
- Use appropriate PlantUML diagram type (@startuml/@enduml)
- For state diagrams: use [*] for initial/final states
- For timing diagrams: use @starttiming/@endtiming  
- For block diagrams: use rectangle/component notation
- For flowcharts: use activity diagram syntax
- Preserve all labels, transitions, and annotations
- Use meaningful names for states/blocks

Respond in this exact format:
```plantuml
<PlantUML content here>
```

ABSTRACT: <1-sentence description of what the figure shows>"""

    prompt = f"Transcribe '{figure['spec_reference']}' ({title}) from this page image."
    
    response = llm.call_with_image(
        system_prompt,
        prompt,
        image_data,
        max_tokens=4096
    )
    
    # Parse PlantUML from response
    puml_match = re.search(r'```(?:plantuml)?\s*\n(.*?)```', response, re.DOTALL)
    if puml_match:
        plantuml_text = puml_match.group(1).strip()
    else:
        plantuml_text = response.strip()
    
    # Ensure @startuml/@enduml wrapper
    if not plantuml_text.startswith("@start"):
        plantuml_text = f"@startuml\n{plantuml_text}\n@enduml"
    
    # Parse abstract
    abstract_match = re.search(r'ABSTRACT:\s*(.+)', response)
    abstract = abstract_match.group(1).strip() if abstract_match else ""
    
    return plantuml_text, abstract
