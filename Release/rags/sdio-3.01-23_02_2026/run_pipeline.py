#!/usr/bin/env python3
"""
RAG V2 Pipeline Orchestrator

Config-driven extraction pipeline for any PDF specification.
All spec-specific values come from spec_config.yaml.

Usage:
    python run_pipeline.py discover          # Phase 1: free, deterministic
    python run_pipeline.py extract-sections  # Phase 2a: LLM chunking
    python run_pipeline.py extract-tables    # Phase 2b: LLM table→CSV
    python run_pipeline.py extract-figures   # Phase 2c: LLM figure→PlantUML
    python run_pipeline.py extract-domain    # Phase 2d: registers + features
    python run_pipeline.py merge             # Phase 3: deterministic assembly
    python run_pipeline.py all               # Run full pipeline
    python run_pipeline.py status            # Show pipeline status
"""

import sys
import argparse
import time
from pathlib import Path

# Add _rag_v2 root to path
PIPELINE_ROOT = Path(__file__).parent
sys.path.insert(0, str(PIPELINE_ROOT))

from shared.config import load_config, get_pdf_path
from shared.utils import print_banner, print_step, print_done, format_duration


def cmd_discover(config: dict, args: argparse.Namespace):
    """Phase 1: Discover PDF structure (free, no LLM)."""
    print_banner("Phase 1: Discovery")
    from phase1_discovery.analyze_pdf import analyze_pdf_structure
    from phase1_discovery.extract_toc import extract_all_tocs
    
    t0 = time.time()
    
    print_step("1/2", "Analyzing PDF structure...")
    pdf_path = get_pdf_path(config)
    structure = analyze_pdf_structure(config, pdf_path)
    
    print_step("2/2", "Extracting table of contents...")
    toc_data = extract_all_tocs(config, pdf_path)
    
    # Merge into discovery.json
    from shared.utils import save_json
    discovery = {
        "pdf_structure": structure,
        "toc": toc_data,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")
    }
    output_path = PIPELINE_ROOT / "intermediates" / "discovery.json"
    save_json(discovery, output_path)
    
    print_done(f"Discovery complete in {format_duration(time.time() - t0)}")
    print(f"  Tables found: {len(toc_data.get('tables', []))}")
    print(f"  Figures found: {len(toc_data.get('figures', []))}")
    print(f"  Sections found: {len(toc_data.get('sections', []))}")


def cmd_extract_sections(config: dict, args: argparse.Namespace):
    """Phase 2a: Extract and chunk spec text."""
    print_banner("Phase 2a: Section Extraction")
    from phase2_extraction.extract_sections import extract_sections
    
    t0 = time.time()
    pdf_path = get_pdf_path(config)
    extract_sections(
        config, pdf_path,
        skip_existing=args.skip_existing,
        model=args.model,
        workers=args.workers
    )
    print_done(f"Section extraction complete in {format_duration(time.time() - t0)}")


def cmd_extract_tables(config: dict, args: argparse.Namespace):
    """Phase 2b: Extract tables as CSV."""
    print_banner("Phase 2b: Table Extraction")
    from phase2_extraction.extract_tables import extract_tables
    
    t0 = time.time()
    pdf_path = get_pdf_path(config)
    extract_tables(
        config, pdf_path,
        skip_existing=args.skip_existing,
        model=args.model,
        workers=args.workers
    )
    print_done(f"Table extraction complete in {format_duration(time.time() - t0)}")


def cmd_extract_figures(config: dict, args: argparse.Namespace):
    """Phase 2c: Extract figures as PlantUML."""
    print_banner("Phase 2c: Figure Extraction")
    from phase2_extraction.extract_figures import extract_figures
    
    t0 = time.time()
    pdf_path = get_pdf_path(config)
    extract_figures(
        config, pdf_path,
        skip_existing=args.skip_existing,
        model=args.model,
        workers=args.workers
    )
    print_done(f"Figure extraction complete in {format_duration(time.time() - t0)}")


def cmd_extract_domain(config: dict, args: argparse.Namespace):
    """Phase 2d: Extract domain-specific nodes (registers, features)."""
    print_banner("Phase 2d: Domain Extraction")
    from phase2_extraction.extract_domain import extract_domain_nodes
    
    t0 = time.time()
    extract_domain_nodes(
        config,
        skip_existing=args.skip_existing,
        model=args.model,
        workers=args.workers
    )
    print_done(f"Domain extraction complete in {format_duration(time.time() - t0)}")


def cmd_validate(config: dict, args: argparse.Namespace):
    """Phase 2e: Validate extracted data."""
    print_banner("Phase 2e: Validation")
    from phase2_extraction.validate import validate_extraction
    
    t0 = time.time()
    validate_extraction(config, model=args.model)
    print_done(f"Validation complete in {format_duration(time.time() - t0)}")


def cmd_merge(config: dict, args: argparse.Namespace):
    """Phase 3: Merge all intermediates into metadata.json."""
    print_banner("Phase 3: Assembly")
    from phase3_assembly.merge_metadata import merge_all
    
    t0 = time.time()
    merge_all(config, dry_run=args.dry_run, validate_only=args.validate_only)
    print_done(f"Merge complete in {format_duration(time.time() - t0)}")


def cmd_all(config: dict, args: argparse.Namespace):
    """Run complete pipeline."""
    print_banner("Full Pipeline Run")
    t0 = time.time()
    
    cmd_discover(config, args)
    cmd_extract_sections(config, args)
    cmd_extract_tables(config, args)
    cmd_extract_figures(config, args)
    cmd_extract_domain(config, args)
    cmd_validate(config, args)
    cmd_merge(config, args)
    
    print_banner("Pipeline Complete")
    print(f"Total time: {format_duration(time.time() - t0)}")


def cmd_status(config: dict, args: argparse.Namespace):
    """Show pipeline status — what's been extracted so far."""
    print_banner("Pipeline Status")
    
    intermediates = PIPELINE_ROOT / "intermediates"
    
    files_to_check = {
        "Discovery":   intermediates / "discovery.json",
        "Sections":    intermediates / "sections.json",
        "Tables Map":  intermediates / "tables_page_map.json",
        "Figures Map": intermediates / "figures_page_map.json",
        "Registers":   intermediates / "registers.json",
        "Features":    intermediates / "features.json",
        "Metadata":    PIPELINE_ROOT / "metadata" / "metadata.json",
    }
    
    for label, path in files_to_check.items():
        status = "EXISTS" if path.exists() else "MISSING"
        size = f"({path.stat().st_size:,} bytes)" if path.exists() else ""
        icon = "[+]" if path.exists() else "[ ]"
        print(f"  {icon} {label:15s} {status} {size}")


def main():
    parser = argparse.ArgumentParser(
        description="RAG V2 Pipeline — Config-driven spec extraction",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  discover          Phase 1: Analyze PDF structure (free)
  extract-sections  Phase 2a: Chunk spec text (LLM)
  extract-tables    Phase 2b: Tables → CSV (LLM + vision)
  extract-figures   Phase 2c: Figures → PlantUML (LLM + vision)
  extract-domain    Phase 2d: Registers + features (LLM)
  validate            Phase 2e: Validate extraction results
  merge             Phase 3: Assemble metadata.json
  all               Run full pipeline
  status            Show extraction status
        """
    )
    
    parser.add_argument("command", choices=[
        "discover", "extract-sections", "extract-tables", "extract-figures",
        "extract-domain", "validate", "merge", "all", "status"
    ])
    parser.add_argument("--config", default="spec_config.yaml",
                       help="Path to spec_config.yaml (default: spec_config.yaml)")
    parser.add_argument("--skip-existing", action="store_true",
                       help="Skip already-processed items")
    parser.add_argument("--model", default=None,
                       help="Override LLM model (haiku/sonnet/opus)")
    parser.add_argument("--workers", type=int, default=None,
                       help="Number of parallel workers")
    parser.add_argument("--dry-run", action="store_true",
                       help="Preview merge without writing")
    parser.add_argument("--validate-only", action="store_true",
                       help="Only validate existing metadata")
    
    args = parser.parse_args()
    
    # Load config
    config_path = PIPELINE_ROOT / args.config
    if not config_path.exists():
        print(f"ERROR: Config file not found: {config_path}")
        sys.exit(1)
    
    config = load_config(config_path)
    
    # Dispatch
    commands = {
        "discover": cmd_discover,
        "extract-sections": cmd_extract_sections,
        "extract-tables": cmd_extract_tables,
        "extract-figures": cmd_extract_figures,
        "extract-domain": cmd_extract_domain,
        "validate": cmd_validate,
        "merge": cmd_merge,
        "all": cmd_all,
        "status": cmd_status,
    }
    
    commands[args.command](config, args)


if __name__ == "__main__":
    main()
