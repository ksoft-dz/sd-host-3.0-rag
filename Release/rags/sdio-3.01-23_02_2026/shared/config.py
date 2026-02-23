#!/usr/bin/env python3
"""
Config loader — reads spec_config.yaml and provides typed access.
"""

import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional


PIPELINE_ROOT = Path(__file__).parent.parent
WORKSPACE_ROOT = PIPELINE_ROOT.parent  # sdio_rag/


def load_config(config_path: Path = None) -> dict:
    """Load and validate spec_config.yaml."""
    if config_path is None:
        config_path = PIPELINE_ROOT / "spec_config.yaml"
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    _validate_config(config)
    return config


def _validate_config(config: dict):
    """Validate required config sections exist."""
    required_sections = ["spec", "toc", "node_types", "chunking", "llm"]
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing required config section: '{section}'")
    
    if "pdf_file" not in config["spec"]:
        raise ValueError("spec.pdf_file is required")
    if "page_offset" not in config["spec"]:
        raise ValueError("spec.page_offset is required")


# =============================================================================
# ACCESSORS
# =============================================================================

def get_pdf_path(config: dict) -> Path:
    """Get absolute path to PDF file."""
    return WORKSPACE_ROOT / config["spec"]["pdf_file"]


def get_page_offset(config: dict) -> int:
    """Get page offset (spec_page + offset = pdf_page)."""
    return config["spec"]["page_offset"]


def get_toc_pages(config: dict, toc_type: str) -> List[int]:
    """Get 0-indexed PDF page indices for a TOC section.
    
    Args:
        toc_type: "sections", "tables", or "figures"
    """
    return config["toc"][toc_type]["pages"]


def get_toc_pattern(config: dict, toc_type: str) -> str:
    """Get regex pattern for TOC entry matching."""
    return config["toc"][toc_type]["pattern"]


def get_toc_id_format(config: dict, toc_type: str) -> str:
    """Get ID format string for a TOC type (tables/figures)."""
    return config["toc"][toc_type].get("id_format", "")


def get_node_type_config(config: dict, node_type: str) -> dict:
    """Get config for a specific node type."""
    return config["node_types"].get(node_type, {})


def is_node_type_enabled(config: dict, node_type: str) -> bool:
    """Check if a node type is enabled."""
    return config["node_types"].get(node_type, {}).get("enabled", False)


def get_classification_rules(config: dict, node_type: str) -> List[dict]:
    """Get classification rules for a node type (TABLE/FIGURE)."""
    return config["node_types"].get(node_type, {}).get("classification_rules", [])


def get_chunking_config(config: dict) -> dict:
    """Get chunking parameters."""
    return config["chunking"]


def get_llm_model(config: dict, model_override: str = None) -> str:
    """Get LLM model string, with optional override."""
    llm = config["llm"]
    if model_override:
        key = model_override.lower()
        if key in llm["models"]:
            return llm["models"][key]
        return model_override  # Assume direct model ID
    default_key = llm["default_model"]
    return llm["models"][default_key]


def get_llm_config(config: dict) -> dict:
    """Get LLM configuration (rate_limit_delay, max_retries, etc.)."""
    return config["llm"]


def get_register_classes(config: dict) -> List[dict]:
    """Get register class definitions from domain config."""
    return config.get("domain", {}).get("registers", {}).get("classes", [])


def get_register_offsets(config: dict) -> Dict[str, dict]:
    """Get register offset→info mapping."""
    return config.get("domain", {}).get("registers", {}).get("register_offsets", {})


def get_exclude_tables(config: dict) -> List[str]:
    """Get list of table IDs to exclude from register extraction."""
    return config.get("domain", {}).get("registers", {}).get("exclude_tables", [])


def get_feature_definitions(config: dict) -> List[dict]:
    """Get feature definitions from domain config."""
    return config.get("domain", {}).get("features", {}).get("definitions", [])


def get_hd_sequence_definitions(config: dict) -> List[dict]:
    """Get HD sequence definitions from domain config."""
    return config.get("domain", {}).get("features", {}).get("hd_sequences", [])


def get_relation_types(config: dict) -> List[dict]:
    """Get defined relation types."""
    return config.get("relation_types", [])


# =============================================================================
# EXTRACTION SETTINGS
# =============================================================================

def get_table_multi_page_config(config: dict) -> dict:
    """Get multi-page table detection settings."""
    return config.get("extraction", {}).get("tables", {}).get("multi_page", {
        "enabled": False, "max_pages_before": 0, "max_pages_after": 0
    })


def get_table_extraction_hints(config: dict) -> List[dict]:
    """Get table extraction hints (config-driven LLM prompt injection).

    Each hint: {name, match_title, expected_columns, instruction}
    """
    return config.get("extraction", {}).get("tables", {}).get("hints", [])


def find_matching_hint(config: dict, table_title: str) -> Optional[dict]:
    """Find the first extraction hint whose match_title regex matches the table title."""
    import re
    hints = get_table_extraction_hints(config)
    for hint in hints:
        pattern = hint.get("match_title", "")
        if pattern and re.search(pattern, table_title, re.IGNORECASE):
            return hint
    return None


def get_validation_config(config: dict) -> dict:
    """Get validation phase settings."""
    return config.get("validation", {"enabled": False})


# =============================================================================
# PATH HELPERS
# =============================================================================

def get_intermediates_dir() -> Path:
    """Get path to intermediates directory."""
    d = PIPELINE_ROOT / "intermediates"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_output_dir() -> Path:
    """Get path to metadata output directory."""
    d = PIPELINE_ROOT / "metadata"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_tables_csv_dir() -> Path:
    """Get path to tables CSV output directory."""
    d = PIPELINE_ROOT / "intermediates" / "tables_csv"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_figures_output_dir() -> Path:
    """Get path to figures output directory."""
    d = PIPELINE_ROOT / "intermediates" / "figures_plantuml"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_figures_images_dir() -> Path:
    """Get path to figure images directory."""
    d = PIPELINE_ROOT / "intermediates" / "figures_images"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_tables_images_dir() -> Path:
    """Get path to table images directory."""
    d = PIPELINE_ROOT / "intermediates" / "tables_images"
    d.mkdir(parents=True, exist_ok=True)
    return d
