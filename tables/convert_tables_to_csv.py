#!/usr/bin/env python3
"""
Convert all table images to CSV/MD format using Claude API.

This script:
1. Reads all table images from tables/images/
2. Uses Claude API to convert table image to CSV or Markdown table
3. Checks if table is complete (if incomplete, logs to tables_to_check.md)
4. Generates 120-char abstract describing the table
5. Updates tables_page_map.json with conversion status and abstract

Requirements:
    pip install anthropic

Environment Variables:
    ANTHROPIC_API_KEY - Your Claude API key (required)

Usage:
    python convert_tables_to_csv.py [--table TABLE_1_1] [--workers 1]
"""

import os
import sys
import json
import base64
import argparse
import logging
from pathlib import Path
from typing import Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import anthropic
except ImportError:
    print("ERROR: anthropic library not installed. Run: pip install anthropic")
    sys.exit(1)

# Configuration
SCRIPT_DIR = Path(__file__).parent
IMAGES_DIR = SCRIPT_DIR / "images"
CSV_DIR = SCRIPT_DIR / "csv"
TABLES_MAP_PATH = SCRIPT_DIR / "tables_page_map.json"
INCOMPLETE_LOG_PATH = SCRIPT_DIR / "tables_to_check.md"

# Claude model selection
MODEL_HAIKU = "claude-haiku-4-5-20251001"    # 0: Fastest/cheapest
MODEL_SONNET = "claude-sonnet-4-5-20250929"  # 1: Balanced (default for attempts 1-2)
MODEL_OPUS = "claude-opus-4-5-20251101"      # 2: Most capable (used for final attempt)

MAX_TOKENS = 8192
MAX_RETRIES = 3
DEFAULT_MODEL_INDEX = 1  # Sonnet
FINAL_ATTEMPT_MODEL_INDEX = 2  # Opus
MAX_ABSTRACT_LENGTH = 120

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(SCRIPT_DIR / 'table_conversion.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def get_model_name(model_index: int) -> str:
    """Get model name from index: 0=Haiku, 1=Sonnet, 2=Opus."""
    models = [MODEL_HAIKU, MODEL_SONNET, MODEL_OPUS]
    if 0 <= model_index < len(models):
        return models[model_index]
    return MODEL_SONNET  # Default fallback


def load_image_as_base64(image_path: Path) -> str:
    """Load image and encode as base64."""
    with open(image_path, 'rb') as f:
        return base64.standard_b64encode(f.read()).decode('utf-8')


def convert_table(client: anthropic.Anthropic, image_path: Path, table_title: str, previous_feedback: str = "", model_index: int = 1) -> Tuple[bool, str, str, str, dict]:
    """
    Convert table image to CSV/MD format using Claude API.
    
    Args:
        client: Anthropic client
        image_path: Path to the image file
        table_title: Title of the table
        previous_feedback: Validation feedback from previous attempt (for retries)
        model_index: Model to use - 0: Haiku, 1: Sonnet (default), 2: Opus
    
    Returns:
        Tuple of (is_complete, table_content, format, abstract, usage_stats)
        is_complete: False if table is incomplete
        table_content: CSV or Markdown table content
        format: "CSV" or "MD"
        abstract: 120-char description
        usage_stats: Token usage dictionary
    """
    model_name = get_model_name(model_index)
    model_label = ["Haiku", "Sonnet", "Opus"][model_index] if 0 <= model_index <= 2 else "Sonnet"
    logger.info(f"Converting table {image_path.name} (model={model_label}, has_feedback={bool(previous_feedback)})")
    
    # Load and encode image
    image_data = load_image_as_base64(image_path)
    
    base_prompt = f"""Analyze this table image and convert it to CSV format.

**Table Title:** {table_title}

**CRITICAL FIRST STEP - COMPLETENESS CHECK:**
If you see an INCOMPLETE table (cut off, partial, missing rows/columns), respond ONLY with:
INCOMPLETE_TABLE

If the table IS COMPLETE, convert it to CSV format with these requirements:

**Requirements:**
- Generate ONLY the CSV data, no explanations
- First row: column headers
- Subsequent rows: data rows
- Use commas as delimiters
- Quote fields containing commas or special characters
- Preserve all data exactly as shown
- Include ALL visible rows and columns

**Example Output:**
```csv
Column1,Column2,Column3
Value1,Value2,Value3
Value4,Value5,Value6
```

**After the CSV table, provide a 120-character abstract on a new line starting with "ABSTRACT:"**

ABSTRACT: Brief description of what this table contains (max 120 chars)"""
    
    # Add previous feedback if this is a retry
    if previous_feedback:
        prompt = f"""{base_prompt}

**IMPORTANT - PREVIOUS ATTEMPT HAD ISSUES:**
The previous CSV generation was rejected with this feedback:

"{previous_feedback}"

**Please fix these specific issues in your new generation.**

Generate the improved CSV table and abstract now:"""
    else:
        prompt = f"{base_prompt}\n\nGenerate the CSV table and abstract now:"

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
        
        content = response.content[0].text.strip()
        
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens
        }
        
        # Check if incomplete
        if "INCOMPLETE_TABLE" in content:
            logger.warning(f"Table is incomplete: {image_path.name}")
            return False, "", "", "", usage
        
        # Extract CSV and abstract
        if "```csv" in content:
            csv_content = content.split("```csv")[1].split("```")[0].strip()
        elif "```" in content:
            csv_content = content.split("```")[1].split("```")[0].strip()
        else:
            # Try to extract everything before ABSTRACT:
            if "ABSTRACT:" in content:
                csv_content = content.split("ABSTRACT:")[0].strip()
            else:
                csv_content = content.strip()
        
        # Extract abstract
        abstract = ""
        if "ABSTRACT:" in content:
            abstract = content.split("ABSTRACT:")[1].strip()
            # Take only the first line
            abstract = abstract.split('\n')[0].strip()
            # Truncate if too long
            if len(abstract) > MAX_ABSTRACT_LENGTH:
                abstract = abstract[:MAX_ABSTRACT_LENGTH-3] + "..."
        
        if not abstract:
            abstract = f"Table showing {table_title[:80]}"[:MAX_ABSTRACT_LENGTH]
        
        logger.info(f"Converted successfully ({len(csv_content)} chars, abstract: {len(abstract)} chars, tokens: in={usage['input_tokens']}, out={usage['output_tokens']})")
        
        return True, csv_content, "CSV", abstract, usage
        
    except Exception as e:
        logger.error(f"Conversion failed: {e}")
        raise


def validate_csv(client: anthropic.Anthropic, image_path: Path, csv_content: str, table_title: str, model_index: int = 1) -> Tuple[bool, str, dict]:
    """
    Validate CSV against original image.
    
    Args:
        client: Anthropic client
        image_path: Path to the image file
        csv_content: CSV content to validate
        table_title: Title of the table
        model_index: Model to use - 0: Haiku, 1: Sonnet (default), 2: Opus
    
    Returns:
        Tuple of (is_valid, feedback, usage_stats)
    """
    model_name = get_model_name(model_index)
    logger.info(f"Validating CSV for {image_path.name}")
    
    # Load and encode image
    image_data = load_image_as_base64(image_path)
    
    prompt = f"""Compare this table image with the CSV data below.

**Table Title:** {table_title}

**CSV Data:**
```csv
{csv_content}
```

**Validation Criteria:**
1. All column headers are captured
2. All visible rows are included
3. All data values match the image
4. No missing or incorrect cells
5. Structure matches the table layout

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


def process_table(api_key: str, tables_data: dict, table_id: str, max_retries: int = MAX_RETRIES) -> Tuple[str, bool, str]:
    """
    Process a single table: convert and update JSON.
    
    Args:
        api_key: Anthropic API key
        tables_data: The full tables JSON data
        table_id: Table ID to process
    
    Returns:
        Tuple of (table_id, success, message)
    """
    # Create client instance for this thread
    client = anthropic.Anthropic(api_key=api_key)
    
    logger.info(f"{'='*60}")
    logger.info(f"Processing {table_id}")
    logger.info(f"{'='*60}")
    
    # Find table entry in JSON
    table_entry = None
    table_index = None
    for idx, table in enumerate(tables_data["tables"]):
        if table["id"] == table_id:
            table_entry = table
            table_index = idx
            break
    
    if table_entry is None:
        msg = f"FATAL ERROR: Table '{table_id}' not found in tables_page_map.json"
        logger.error(msg)
        return (table_id, False, msg)
    
    logger.info(f"Found table: {table_entry['spec_reference']} - {table_entry['title']}")
    
    # Verify image exists
    image_path = IMAGES_DIR / f"{table_id}.jpg"
    if not image_path.exists():
        msg = f"FATAL ERROR: Image not found: {image_path}"
        logger.error(msg)
        return (table_id, False, msg)
    
    total_usage = {"input_tokens": 0, "output_tokens": 0}
    feedback = ""
    
    try:
        for attempt in range(1, max_retries + 1):
            # Choose model: Sonnet for attempts 1-2, Opus for final attempt
            model_index = FINAL_ATTEMPT_MODEL_INDEX if attempt == max_retries else DEFAULT_MODEL_INDEX
            
            logger.info(f"Attempt {attempt}/{max_retries}")
            
            # Convert table
            is_complete, table_content, format_type, abstract, usage = convert_table(
                client, image_path, table_entry["title"], previous_feedback=feedback, model_index=model_index
            )
            
            total_usage["input_tokens"] += usage["input_tokens"]
            total_usage["output_tokens"] += usage["output_tokens"]
            
            if not is_complete:
                # Log incomplete table
                msg = f"INCOMPLETE: {table_entry['spec_reference']} - {table_entry['title']}"
                logger.warning(msg)
                
                # Update JSON status
                tables_data["tables"][table_index]["conversion"]["status"] = "INCOMPLETE"
                tables_data["tables"][table_index]["conversion"]["validation_notes"] = "Table appears incomplete or cut off"
                tables_data["tables"][table_index]["conversion"]["attempts"] = attempt
                tables_data["tables"][table_index]["conversion"]["total_tokens"] = total_usage["input_tokens"] + total_usage["output_tokens"]
                
                return (table_id, False, "INCOMPLETE")
            
            # Validate CSV
            is_valid, validation_feedback, val_usage = validate_csv(
                client, image_path, table_content, table_entry["title"], model_index=model_index
            )
            
            total_usage["input_tokens"] += val_usage["input_tokens"]
            total_usage["output_tokens"] += val_usage["output_tokens"]
            
            if is_valid:
                # Success! Save CSV file
                output_filename = f"{table_id}.csv"
                output_path = CSV_DIR / output_filename
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(table_content)
                
                # Update JSON
                tables_data["tables"][table_index]["abstract"] = abstract
                tables_data["tables"][table_index]["conversion"]["status"] = "COMPLETED"
                tables_data["tables"][table_index]["conversion"]["file_format"] = format_type
                tables_data["tables"][table_index]["conversion"]["file_name"] = output_filename
                tables_data["tables"][table_index]["conversion"]["validated"] = True
                tables_data["tables"][table_index]["conversion"]["attempts"] = attempt
                tables_data["tables"][table_index]["conversion"]["total_tokens"] = total_usage["input_tokens"] + total_usage["output_tokens"]
                
                logger.info(f"[OK] SUCCESS: Saved to {output_filename} (attempt {attempt}/{max_retries})")
                logger.info(f"Abstract: {abstract}")
                logger.info(f"Total tokens: {total_usage['input_tokens']} in + {total_usage['output_tokens']} out")
                
                return (table_id, True, "SUCCESS")
            else:
                # Validation failed
                logger.warning(f"[FAIL] Attempt {attempt}/{max_retries} validation failed")
                logger.warning(f"Feedback: {validation_feedback}")
                feedback = validation_feedback
                
                if attempt < max_retries:
                    logger.info(f"Retrying with feedback...")
                else:
                    logger.error(f"Max retries reached. Final feedback: {feedback}")
        
        # Max retries exhausted
        msg = f"FAILED after {max_retries} attempts: {feedback}"
        tables_data["tables"][table_index]["conversion"]["status"] = "FAILED"
        tables_data["tables"][table_index]["conversion"]["validation_notes"] = feedback
        tables_data["tables"][table_index]["conversion"]["attempts"] = max_retries
        tables_data["tables"][table_index]["conversion"]["total_tokens"] = total_usage["input_tokens"] + total_usage["output_tokens"]
        
        return (table_id, False, msg)
        
    except Exception as e:
        msg = f"ERROR: {str(e)}"
        logger.error(msg)
        tables_data["tables"][table_index]["conversion"]["status"] = "FAILED"
        tables_data["tables"][table_index]["conversion"]["validation_notes"] = str(e)
        tables_data["tables"][table_index]["conversion"]["attempts"] = 0
        tables_data["tables"][table_index]["conversion"]["total_tokens"] = total_usage.get("input_tokens", 0) + total_usage.get("output_tokens", 0)
        return (table_id, False, msg)


def main():
    parser = argparse.ArgumentParser(description="Convert table images to CSV using Claude API")
    parser.add_argument("--table", help="Process specific table (e.g., TABLE_1_1). If omitted, process all.")
    parser.add_argument("--skip-existing", action="store_true", help="Skip tables that already have CSV files")
    parser.add_argument("--workers", type=int, default=1, help="Number of parallel workers (default: 1)")
    args = parser.parse_args()
    
    # Check API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ERROR: ANTHROPIC_API_KEY environment variable not set")
        logger.error("See docs/CLAUDE_API_SETUP.md for setup instructions")
        sys.exit(1)
    
    # Create output directory
    CSV_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load tables map
    if not TABLES_MAP_PATH.exists():
        logger.error(f"FATAL ERROR: tables_page_map.json not found at {TABLES_MAP_PATH}")
        logger.error("Please run extract_tables_map.py first.")
        sys.exit(1)
    
    with open(TABLES_MAP_PATH, 'r', encoding='utf-8') as f:
        tables_data = json.load(f)
    
    logger.info(f"Loaded {len(tables_data['tables'])} tables from JSON")
    logger.info(f"Using models: Sonnet (attempts 1-2) -> Opus (attempt 3)")
    logger.info(f"Workers: {args.workers} {'(sequential)' if args.workers == 1 else '(parallel)'}")
    logger.info(f"Output directory: {CSV_DIR}")
    
    # Determine which tables to process
    if args.table:
        tables_to_process = [args.table]
    else:
        tables_to_process = [table["id"] for table in tables_data["tables"]]
    
    # Filter out existing if requested
    if args.skip_existing:
        tables_to_process = [
            t_id for t_id in tables_to_process
            if not (CSV_DIR / f"{t_id}.csv").exists()
        ]
    
    logger.info(f"Processing {len(tables_to_process)} tables")
    logger.info("="*60)
    
    # Process tables (sequential or parallel)
    success_count = 0
    failed_tables = []
    incomplete_tables = []
    
    if args.workers == 1:
        # Sequential processing
        for table_id in tables_to_process:
            table_id_result, success, msg = process_table(api_key, tables_data, table_id, max_retries=MAX_RETRIES)
            if success:
                success_count += 1
            elif msg == "INCOMPLETE":
                incomplete_tables.append(table_id_result)
            else:
                failed_tables.append(table_id_result)
    else:
        # Parallel processing
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            future_to_table = {
                executor.submit(process_table, api_key, tables_data, table_id, MAX_RETRIES): table_id
                for table_id in tables_to_process
            }
            
            for future in as_completed(future_to_table):
                table_id = future_to_table[future]
                try:
                    table_id_result, success, msg = future.result()
                    if success:
                        success_count += 1
                    elif msg == "INCOMPLETE":
                        incomplete_tables.append(table_id_result)
                    else:
                        failed_tables.append(table_id_result)
                except Exception as e:
                    logger.error(f"Unexpected error processing {table_id}: {e}")
                    failed_tables.append(table_id)
    
    # Save updated JSON
    with open(TABLES_MAP_PATH, 'w', encoding='utf-8') as f:
        json.dump(tables_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved updates to {TABLES_MAP_PATH.name}")
    
    # Write incomplete tables log
    if incomplete_tables:
        with open(INCOMPLETE_LOG_PATH, 'w', encoding='utf-8') as f:
            f.write("# Incomplete Tables\n\n")
            f.write("The following tables appear to be incomplete or cut off:\n\n")
            for table_id in incomplete_tables:
                # Find table details
                for table in tables_data["tables"]:
                    if table["id"] == table_id:
                        f.write(f"- **{table['spec_reference']}**: {table['title']} (PDF page {table['definition_page']})\n")
                        break
        logger.info(f"Written incomplete tables log to {INCOMPLETE_LOG_PATH}")
    
    # Summary
    logger.info("="*60)
    logger.info("CONVERSION SUMMARY")
    logger.info("="*60)
    logger.info(f"Total processed: {len(tables_to_process)}")
    logger.info(f"Successful: {success_count}")
    logger.info(f"Incomplete: {len(incomplete_tables)}")
    logger.info(f"Failed: {len(failed_tables)}")
    
    if incomplete_tables:
        logger.warning(f"Incomplete tables: {incomplete_tables}")
        logger.warning(f"See {INCOMPLETE_LOG_PATH} for details")
    
    if failed_tables:
        logger.error(f"Failed tables: {failed_tables}")
        sys.exit(1)
    else:
        logger.info("[OK] All tables processed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
