#!/usr/bin/env python3
"""
Generate concise abstracts for all figures using Claude API.

This script:
1. Reads figures_page_map.json
2. Verifies figure entry exists BEFORE calling API
3. Uses Claude API to generate 120-char abstract from image
4. Updates figures_page_map.json with "abstract" key
5. Fatal error if figure entry not found

Requirements:
    pip install anthropic

Environment Variables:
    ANTHROPIC_API_KEY - Your Claude API key (required)

Usage:
    python generate_figure_abstracts.py [--figure FIG_1_1] [--skip-existing]
"""

import os
import sys
import json
import base64
import argparse
import logging
from pathlib import Path
from typing import Optional

try:
    import anthropic
except ImportError:
    print("ERROR: anthropic library not installed. Run: pip install anthropic")
    sys.exit(1)

# Configuration
SCRIPT_DIR = Path(__file__).parent
IMAGES_DIR = SCRIPT_DIR / "images"
FIGURES_MAP_PATH = SCRIPT_DIR / "figures_page_map.json"

# Claude model selection (cost-effective)
MODEL = "claude-sonnet-4-5-20250929"  # Cheapest model with vision (~$0.80/1M input, ~$4/1M output)
MAX_TOKENS = 256  # Short abstracts only
MAX_ABSTRACT_LENGTH = 120  # characters

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(SCRIPT_DIR / 'abstract_generation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_image_as_base64(image_path: Path) -> str:
    """Load image and encode as base64."""
    with open(image_path, 'rb') as f:
        return base64.standard_b64encode(f.read()).decode('utf-8')


def generate_abstract(client: anthropic.Anthropic, image_path: Path, figure_title: str) -> tuple[str, dict]:
    """
    Generate a concise abstract from figure image.
    
    Returns:
        Tuple of (abstract_text, usage_stats)
    """
    logger.info(f"Generating abstract for {image_path.name}")
    
    # Load and encode image
    image_data = load_image_as_base64(image_path)
    
    # Prompt for abstract generation
    prompt = f"""Analyze this technical diagram and write a VERY concise abstract.

**Figure Title:** {figure_title}

**Requirements:**
- Maximum {MAX_ABSTRACT_LENGTH} characters (strict limit)
- Describe WHAT the diagram shows (not what it's for)
- Focus on key components and relationships
- Use technical terminology
- No introductory phrases like "This diagram shows..."
- Start directly with the content description

**Examples:**
- "Block diagram showing host controller architecture with DMA engines, interrupt logic, and register interfaces"
- "Register layout with bit fields for control flags, status bits, and configuration parameters"
- "State machine transitions between idle, active, busy, and error states with trigger conditions"

Generate the abstract (max {MAX_ABSTRACT_LENGTH} chars):"""

    try:
        response = client.messages.create(
            model=MODEL,
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
        
        # Extract abstract text
        abstract = response.content[0].text.strip()
        
        # Remove quotes if present
        if abstract.startswith('"') and abstract.endswith('"'):
            abstract = abstract[1:-1]
        
        # Truncate if too long
        if len(abstract) > MAX_ABSTRACT_LENGTH:
            abstract = abstract[:MAX_ABSTRACT_LENGTH-3] + "..."
            logger.warning(f"Abstract truncated to {MAX_ABSTRACT_LENGTH} chars")
        
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens
        }
        
        logger.info(f"Generated abstract ({len(abstract)} chars)")
        logger.debug(f"Abstract: {abstract}")
        logger.debug(f"Tokens: in={usage['input_tokens']}, out={usage['output_tokens']}")
        
        return abstract, usage
        
    except Exception as e:
        logger.error(f"Abstract generation failed: {e}")
        raise


def process_figure(client: anthropic.Anthropic, figures_data: dict, figure_id: str, skip_existing: bool = False) -> bool:
    """
    Process a single figure: generate abstract and update JSON.
    
    Returns:
        True if successful, False otherwise
    """
    logger.info(f"{'='*60}")
    logger.info(f"Processing {figure_id}")
    logger.info(f"{'='*60}")
    
    # Find figure entry in JSON
    figure_entry = None
    figure_index = None
    for idx, fig in enumerate(figures_data["figures"]):
        if fig["id"] == figure_id:
            figure_entry = fig
            figure_index = idx
            break
    
    # FATAL ERROR: Figure not found
    if figure_entry is None:
        logger.error(f"FATAL ERROR: Figure '{figure_id}' not found in figures_page_map.json!")
        logger.error(f"Available figures: {[f['id'] for f in figures_data['figures'][:5]]}...")
        logger.error(f"Please verify the figure ID is correct.")
        return False
    
    logger.info(f"Found figure: {figure_entry['spec_reference']} - {figure_entry['title']}")
    
    # Check if abstract already exists
    if skip_existing and "abstract" in figure_entry and figure_entry["abstract"]:
        logger.info(f"Skipping {figure_id} (abstract already exists)")
        return True
    
    # Verify image exists
    image_path = IMAGES_DIR / f"{figure_id}.jpg"
    if not image_path.exists():
        logger.error(f"FATAL ERROR: Image not found: {image_path}")
        logger.error(f"Please run extract_figure_images.py first.")
        return False
    
    try:
        # Generate abstract
        abstract, usage = generate_abstract(client, image_path, figure_entry["title"])
        
        # Update figure entry
        figures_data["figures"][figure_index]["abstract"] = abstract
        
        logger.info(f"✓ SUCCESS: Generated abstract ({len(abstract)} chars)")
        logger.info(f"Abstract: {abstract}")
        logger.info(f"Usage: in={usage['input_tokens']}, out={usage['output_tokens']} tokens")
        
        return True
        
    except Exception as e:
        logger.error(f"FATAL ERROR processing {figure_id}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Generate abstracts for figures using Claude API")
    parser.add_argument("--figure", help="Process specific figure (e.g., FIG_1_1). If omitted, process all.")
    parser.add_argument("--skip-existing", action="store_true", help="Skip figures that already have abstracts")
    parser.add_argument("--dry-run", action="store_true", help="Don't save changes to JSON (test only)")
    args = parser.parse_args()
    
    # Check API key
    # TODO: Put in environment variable setup instructions in docs/CLAUDE_API_SETUP.md
    # Example key for testing purposes only; replace with your own key.
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("FATAL ERROR: ANTHROPIC_API_KEY environment variable not set")
        logger.error("Get your API key from: https://console.anthropic.com/settings/keys")
        logger.error("Then set it: $env:ANTHROPIC_API_KEY='your-key-here'  (PowerShell)")
        logger.error("           or export ANTHROPIC_API_KEY='your-key-here'  (Linux/Mac)")
        sys.exit(1)
    
    # Initialize Claude client
    client = anthropic.Anthropic(api_key=api_key)
    
    logger.info(f"Using model: {MODEL}")
    logger.info(f"Max abstract length: {MAX_ABSTRACT_LENGTH} characters")
    logger.info(f"Skip existing: {args.skip_existing}")
    logger.info(f"Dry run: {args.dry_run}")
    
    # Load figures map
    if not FIGURES_MAP_PATH.exists():
        logger.error(f"FATAL ERROR: figures_page_map.json not found at {FIGURES_MAP_PATH}")
        logger.error("Please run extract_figures_map.py first.")
        sys.exit(1)
    
    with open(FIGURES_MAP_PATH, 'r', encoding='utf-8') as f:
        figures_data = json.load(f)
    
    logger.info(f"Loaded {len(figures_data['figures'])} figures from JSON")
    
    # Determine which figures to process
    if args.figure:
        figures_to_process = [args.figure]
    else:
        figures_to_process = [fig["id"] for fig in figures_data["figures"]]
    
    logger.info(f"Processing {len(figures_to_process)} figures")
    logger.info("="*60)
    
    # Process figures
    success_count = 0
    failed_figures = []
    total_usage = {"input_tokens": 0, "output_tokens": 0}
    
    for fig_id in figures_to_process:
        if process_figure(client, figures_data, fig_id, args.skip_existing):
            success_count += 1
        else:
            failed_figures.append(fig_id)
            # Fatal error: stop processing
            logger.error(f"FATAL: Stopping due to error with {fig_id}")
            break
    
    # Save updated JSON (unless dry run or failures occurred)
    if not args.dry_run and not failed_figures:
        # Backup original
        backup_path = FIGURES_MAP_PATH.with_suffix('.json.backup')
        if not backup_path.exists():
            with open(FIGURES_MAP_PATH, 'r', encoding='utf-8') as f:
                backup_data = f.read()
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(backup_data)
            logger.info(f"Created backup: {backup_path.name}")
        
        # Save updated JSON
        with open(FIGURES_MAP_PATH, 'w', encoding='utf-8') as f:
            json.dump(figures_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✓ Saved updates to {FIGURES_MAP_PATH.name}")
    elif args.dry_run:
        logger.info("DRY RUN: Changes NOT saved to JSON")
    elif failed_figures:
        logger.error("FATAL: Changes NOT saved due to errors")
    
    # Summary
    logger.info("="*60)
    logger.info("GENERATION SUMMARY")
    logger.info("="*60)
    logger.info(f"Total processed: {len(figures_to_process)}")
    logger.info(f"Successful: {success_count}")
    logger.info(f"Failed: {len(failed_figures)}")
    
    if failed_figures:
        logger.error("FATAL: Failed figures:")
        for fig_id in failed_figures:
            logger.error(f"  - {fig_id}")
        logger.error("")
        logger.error("Please check the log above for detailed error information.")
        logger.error("Common issues:")
        logger.error("  1. Figure ID not found in figures_page_map.json")
        logger.error("  2. Image file missing from figures/images/")
        logger.error("  3. API key invalid or insufficient credits")
        sys.exit(1)
    else:
        logger.info("✓ All abstracts generated successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main()
