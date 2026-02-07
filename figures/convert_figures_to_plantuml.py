#!/usr/bin/env python3
"""
Convert all figure images to PlantUML diagrams using Claude API.

This script:
1. Reads all figure images from figures/images/
2. Uses Claude API to generate PlantUML representation
3. Validates the PlantUML against original image
4. Retries up to MAX_RETRIES times if validation fails
5. Saves PlantUML files to figures/plantuml/

Requirements:
    pip install anthropic

Environment Variables:
    ANTHROPIC_API_KEY - Your Claude API key (required)

Usage:
    python convert_figures_to_plantuml.py [--figure FIG_1_1] [--max-retries 3]
"""

import os
import sys
import json
import base64
import argparse
import logging
from pathlib import Path
from typing import Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import anthropic
except ImportError:
    print("ERROR: anthropic library not installed. Run: pip install anthropic")
    sys.exit(1)

# Configuration
SCRIPT_DIR = Path(__file__).parent
IMAGES_DIR = SCRIPT_DIR / "images"
PLANTUML_DIR = SCRIPT_DIR / "plantuml"
FIGURES_MAP_PATH = SCRIPT_DIR / "figures_page_map.json"

# Claude model selection
MODEL_HAIKU = "claude-haiku-4-5-20251001"    # 0: Fastest/cheapest
MODEL_SONNET = "claude-sonnet-4-5-20250929"  # 1: Balanced (default for attempts 1-2)
MODEL_OPUS = "claude-opus-4-5-20251101"      # 2: Most capable (used for final attempt)

MAX_TOKENS = 4096
MAX_RETRIES = 3
DEFAULT_MODEL_INDEX = 1  # Sonnet
FINAL_ATTEMPT_MODEL_INDEX = 2  # Opus


def get_model_name(model_index: int) -> str:
    """Get model name from index: 0=Haiku, 1=Sonnet, 2=Opus."""
    models = [MODEL_OPUS, MODEL_OPUS, MODEL_OPUS]
    if 0 <= model_index < len(models):
        return models[model_index]
    return MODEL_OPUS  # Default fallback

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(SCRIPT_DIR / 'conversion.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Keywords that indicate the figure is a register/table (not a real diagram)
REGISTER_TABLE_KEYWORDS = [
    "register", "bit field", "bit positions", "table structure", 
    "column alignment", "32-bit", "16-bit", "8-bit", "bit wide",
    "D31", "D00", "bits", "field diagram", "layout"
]


def is_register_table_feedback(feedback: str) -> bool:
    """
    Detect if validation feedback indicates this is a register/table diagram.
    
    Returns:
        True if feedback suggests register/table format
    """
    feedback_lower = feedback.lower()
    matches = sum(1 for kw in REGISTER_TABLE_KEYWORDS if kw.lower() in feedback_lower)
    return matches >= 2  # At least 2 keywords suggest register/table


def load_image_as_base64(image_path: Path) -> str:
    """Load image and encode as base64."""
    with open(image_path, 'rb') as f:
        return base64.standard_b64encode(f.read()).decode('utf-8')


def generate_plantuml(client: anthropic.Anthropic, image_path: Path, is_register_table: bool = False, previous_feedback: str = "", model_index: int = 1) -> Tuple[str, dict]:
    """
    Generate PlantUML from image using Claude API.
    
    Args:
        client: Anthropic client
        image_path: Path to the image file
        is_register_table: If True, use simplified prompt for register/table diagrams
        previous_feedback: Validation feedback from previous attempt (for retries)
        model_index: Model to use - 0: Haiku, 1: Sonnet (default), 2: Opus
    
    Returns:
        Tuple of (plantuml_code, usage_stats)
    """
    model_name = get_model_name(model_index)
    model_label = ["Opus", "Opus", "Opus"][model_index] if 0 <= model_index <= 2 else "Sonnet"
    logger.info(f"Generating PlantUML for {image_path.name} (model={model_label}, register_table={is_register_table}, has_feedback={bool(previous_feedback)})")
    
    # Load and encode image
    image_data = load_image_as_base64(image_path)
    
    # Choose prompt based on diagram type
    if is_register_table:
        # Simplified prompt for register/table diagrams
        base_prompt = """This image shows a REGISTER LAYOUT or TABLE diagram (not a flowchart or state machine).

**IMPORTANT: This is tabular data, NOT a complex diagram. Keep it simple!**

**Requirements:**
- Generate ONLY PlantUML code, no explanations
- Use a simple TABLE format with proper columns
- DO NOT use arrows, state machines, or complex diagrams
- Extract ALL text data exactly as shown (bit names, positions, values, descriptions)
- Focus on DATA EXTRACTION, not visual representation

**For Register Bit Field Diagrams:**
Use this simple table format:
```plantuml
@startuml
skinparam monochrome true

title Register Name (Offset 0xXX)

|= Bits |= Field Name |= Access |= Description |
| 31:24 | FIELD1 | RW | Description text |
| 23:16 | FIELD2 | RO | Description text |
| 15:0 | FIELD3 | RW | Description text |

@enduml
```

**For Data Tables:**
Use this format:
```plantuml
@startuml
skinparam monochrome true

title Table Title

|= Column1 |= Column2 |= Column3 |
| data | data | data |
| data | data | data |

@enduml
```

**KEY RULES:**
1. Extract ALL visible text/data from the image
2. Use simple tables - NO arrows, NO boxes, NO state diagrams
3. Preserve exact field names, bit positions, and values
4. If bit positions are shown (like D31-D00), include them as a header row"""
    else:
        # Standard prompt for complex diagrams
        base_prompt = """Analyze this technical diagram and convert it to PlantUML code.

**Requirements:**
- Generate ONLY the PlantUML code, no explanations
- Start with @startuml and end with @enduml
- Preserve all text labels, arrows, boxes, and relationships exactly as shown
- Use appropriate PlantUML syntax (sequence, component, state, class, etc.)
- For register diagrams: use tables or component diagrams
- For state machines: use state diagrams
- For sequences: use sequence diagrams
- Include all bit positions, field names, and values visible in the diagram

**Output format:**
```plantuml
@startuml
... your code here ...
@enduml
```"""
    
    # Add previous feedback if this is a retry
    if previous_feedback:
        prompt = f"""{base_prompt}

**IMPORTANT - PREVIOUS ATTEMPT HAD ISSUES:**
The previous PlantUML generation was rejected with this feedback:

"{previous_feedback}"

**Please fix these specific issues in your new generation.**

Generate the improved PlantUML code now:"""
    else:
        prompt = f"{base_prompt}\n\nGenerate the PlantUML code now:"

    try:
        response = client.messages.create(
            model=model_name,
            max_tokens=MAX_TOKENS,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_data
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        )
        
        # Extract PlantUML code
        content = response.content[0].text
        
        # Extract code between ```plantuml and ``` or @startuml and @enduml
        if "```plantuml" in content:
            code = content.split("```plantuml")[1].split("```")[0].strip()
        elif "@startuml" in content:
            # Extract from @startuml to @enduml
            start = content.find("@startuml")
            end = content.find("@enduml", start) + len("@enduml")
            code = content[start:end].strip()
        else:
            # Use entire content
            code = content.strip()
        
        # Ensure @startuml/@enduml tags
        if not code.startswith("@startuml"):
            code = "@startuml\n" + code
        if not code.endswith("@enduml"):
            code = code + "\n@enduml"
        
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens
        }
        
        logger.info(f"Generated {len(code)} chars (tokens: in={usage['input_tokens']}, out={usage['output_tokens']})")
        return code, usage
        
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        raise


def validate_plantuml(client: anthropic.Anthropic, image_path: Path, plantuml_code: str, model_index: int = 1) -> Tuple[bool, str, dict]:
    """
    Validate PlantUML against original image.
    
    Args:
        client: Anthropic client
        image_path: Path to the image file
        plantuml_code: PlantUML code to validate
        model_index: Model to use - 0: Haiku, 1: Sonnet (default), 2: Opus
    
    Returns:
        Tuple of (is_valid, feedback, usage_stats)
    """
    model_name = get_model_name(model_index)
    logger.info(f"Validating PlantUML for {image_path.name}")
    
    # Load and encode image
    image_data = load_image_as_base64(image_path)
    
    prompt = f"""Compare this diagram image with the PlantUML code below. 

**PlantUML Code:**
```plantuml
{plantuml_code}
```

**Validation Criteria:**
1. All visible text labels are captured
2. All arrows/connections are represented
3. All boxes/components are included
4. Relationships match the diagram
5. Structure and layout are logically equivalent

**Response Format:**
{{
  "valid": true/false,
  "score": 0-100,
  "issues": ["list of missing or incorrect elements"],
  "feedback": "specific improvements needed"
}}

Provide ONLY valid JSON, no other text:"""

    try:
        response = client.messages.create(
            model=model_name,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_data
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        )
        
        content = response.content[0].text.strip()
        
        # Extract JSON from response
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        # Parse validation result
        result = json.loads(content)
        
        is_valid = result.get("valid", False) and result.get("score", 0) >= 70
        feedback = result.get("feedback", "No feedback provided")
        
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens
        }
        
        logger.info(f"Validation: valid={is_valid}, score={result.get('score', 0)}")
        if not is_valid:
            logger.warning(f"Issues: {result.get('issues', [])}")
        
        return is_valid, feedback, usage
        
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        # If validation fails, assume invalid and provide error as feedback
        return False, f"Validation error: {str(e)}", {"input_tokens": 0, "output_tokens": 0}


def process_figure(api_key: str, figure_id: str, max_retries: int = MAX_RETRIES) -> bool:
    """
    Process a single figure: generate and validate PlantUML.
    
    Each invocation creates its own API client for thread safety.
    If validation feedback suggests register/table format, switches to simplified prompt.
    
    Args:
        api_key: Anthropic API key
        figure_id: Figure ID to process (e.g., FIG_1_1)
        max_retries: Maximum retry attempts
    
    Returns:
        True if successful, False otherwise
    """
    # Create client instance for this thread
    client = anthropic.Anthropic(api_key=api_key)
    image_path = IMAGES_DIR / f"{figure_id}.jpg"
    output_path = PLANTUML_DIR / f"{figure_id}.puml"
    
    if not image_path.exists():
        logger.error(f"Image not found: {image_path}")
        return False
    
    logger.info(f"{'='*60}")
    logger.info(f"Processing {figure_id}")
    logger.info(f"{'='*60}")
    
    total_usage = {"input_tokens": 0, "output_tokens": 0}
    use_register_table_mode = False  # Will be set True if feedback indicates register/table
    feedback = ""
    
    for attempt in range(1, max_retries + 1):
        # Choose model: Sonnet for attempts 1-2, Opus for final attempt
        model_index = FINAL_ATTEMPT_MODEL_INDEX if attempt == max_retries else DEFAULT_MODEL_INDEX
        
        logger.info(f"Attempt {attempt}/{max_retries} (register_table_mode={use_register_table_mode})")
        
        try:
            # Generate PlantUML (with mode based on previous feedback, and pass feedback for improvements)
            plantuml_code, gen_usage = generate_plantuml(
                client, 
                image_path, 
                is_register_table=use_register_table_mode,
                previous_feedback=feedback if attempt > 1 else "",  # Pass feedback on retries
                model_index=model_index
            )
            total_usage["input_tokens"] += gen_usage["input_tokens"]
            total_usage["output_tokens"] += gen_usage["output_tokens"]
            
            # Validate PlantUML
            is_valid, feedback, val_usage = validate_plantuml(client, image_path, plantuml_code, model_index=model_index)
            total_usage["input_tokens"] += val_usage["input_tokens"]
            total_usage["output_tokens"] += val_usage["output_tokens"]
            
            if is_valid:
                # Save successful PlantUML
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(plantuml_code)
                
                logger.info(f"[OK] SUCCESS: Saved to {output_path.name}")
                logger.info(f"Total usage: {total_usage}")
                return True
            else:
                logger.warning(f"[FAIL] Validation failed (attempt {attempt})")
                logger.warning(f"Feedback: {feedback}")
                
                # Check if feedback indicates register/table diagram
                if not use_register_table_mode and is_register_table_feedback(feedback):
                    use_register_table_mode = True
                    logger.info(">>> DETECTED: Register/table diagram - switching to simplified mode")
                
                if attempt < max_retries:
                    logger.info("Retrying with feedback...")
                
        except Exception as e:
            logger.error(f"Error in attempt {attempt}: {e}")
            if attempt == max_retries:
                break
    
    # All retries exhausted
    logger.error(f"FATAL: Failed after {max_retries} attempts")
    logger.error(f"Total usage: {total_usage}")
    logger.error(f"Image: {image_path}")
    logger.error(f"Last feedback: {feedback if 'feedback' in locals() else 'N/A'}")
    
    return False


def main():
    parser = argparse.ArgumentParser(description="Convert figure images to PlantUML using Claude API")
    parser.add_argument("--figure", help="Process specific figure (e.g., FIG_1_1). If omitted, process all.")
    parser.add_argument("--max-retries", type=int, default=MAX_RETRIES, help=f"Max retry attempts (default: {MAX_RETRIES})")
    parser.add_argument("--skip-existing", action="store_true", help="Skip figures that already have PlantUML files")
    parser.add_argument("--workers", type=int, default=1, help="Number of parallel workers (default: 1, sequential)")
    args = parser.parse_args()
    
    # Check API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ERROR: ANTHROPIC_API_KEY environment variable not set")
        logger.error("Get your API key from: https://console.anthropic.com/settings/keys")
        logger.error("Then set it: $env:ANTHROPIC_API_KEY='your-key-here'  (PowerShell)")
        logger.error("           or export ANTHROPIC_API_KEY='your-key-here'  (Linux/Mac)")
        logger.error("See docs/CLAUDE_API_SETUP.md for detailed instructions")
        sys.exit(1)
    
    # Create output directory
    PLANTUML_DIR.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Using models: Sonnet (attempts 1-2) → Opus (attempt 3)")
    logger.info(f"  - Sonnet: {MODEL_SONNET}")
    logger.info(f"  - Opus: {MODEL_OPUS}")
    logger.info(f"Max retries: {args.max_retries}")
    logger.info(f"Workers: {args.workers} {'(sequential)' if args.workers == 1 else '(parallel)'}")
    logger.info(f"Output directory: {PLANTUML_DIR}")
    
    # Load figures map
    with open(FIGURES_MAP_PATH, 'r', encoding='utf-8') as f:
        figures_data = json.load(f)
    
    # Determine which figures to process
    if args.figure:
        figures_to_process = [args.figure]
    else:
        figures_to_process = [fig["id"] for fig in figures_data["figures"]]
    
    # Filter out figures to skip
    if args.skip_existing:
        figures_to_process = [
            fig_id for fig_id in figures_to_process
            if not (PLANTUML_DIR / f"{fig_id}.puml").exists()
        ]
        skipped_count = len([fig["id"] for fig in figures_data["figures"]]) - len(figures_to_process)
        if skipped_count > 0:
            logger.info(f"Skipping {skipped_count} existing figures")
    
    logger.info(f"Processing {len(figures_to_process)} figures")
    logger.info("="*60)
    
    # Process figures (sequential or parallel)
    success_count = 0
    failed_figures = []
    
    if args.workers == 1:
        # Sequential processing
        for fig_id in figures_to_process:
            if process_figure(api_key, fig_id, args.max_retries):
                success_count += 1
            else:
                failed_figures.append(fig_id)
    else:
        # Parallel processing
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            # Submit all tasks
            future_to_fig = {
                executor.submit(process_figure, api_key, fig_id, args.max_retries): fig_id
                for fig_id in figures_to_process
            }
            
            # Process completed tasks
            for future in as_completed(future_to_fig):
                fig_id = future_to_fig[future]
                try:
                    if future.result():
                        success_count += 1
                    else:
                        failed_figures.append(fig_id)
                except Exception as e:
                    logger.error(f"Unexpected error processing {fig_id}: {e}")
                    failed_figures.append(fig_id)
    
    # Summary
    logger.info("="*60)
    logger.info("CONVERSION SUMMARY")
    logger.info("="*60)
    logger.info(f"Total processed: {len(figures_to_process)}")
    logger.info(f"Successful: {success_count}")
    logger.info(f"Failed: {len(failed_figures)}")
    
    if failed_figures:
        logger.error("Failed figures:")
        for fig_id in failed_figures:
            logger.error(f"  - {fig_id}")
        sys.exit(1)
    else:
        logger.info("[OK] All figures converted successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main()
