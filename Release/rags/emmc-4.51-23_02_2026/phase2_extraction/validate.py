#!/usr/bin/env python3
"""
Phase 2e: Validate extracted data — fast rule-based sanity checks.

Runs config-driven checks on extracted data:
- Register fields: name length, missing bits/access, zero fields
- Tables: empty CSV, single-row
- Figures: empty PlantUML, missing @startuml

Depends on: Phase 2b-2d intermediates
Output: intermediates/validation_report.json
"""

import csv
import time
from pathlib import Path
from typing import List, Dict, Any

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.config import get_validation_config, get_intermediates_dir
from shared.utils import load_json, save_json, print_step


def validate_extraction(config: dict, model: str = None):
    """Main entry point for validating extracted data."""
    val_config = get_validation_config(config)
    if not val_config.get("enabled", False):
        print("  Validation disabled in config")
        return

    intermediates = get_intermediates_dir()
    issues = []

    checks = val_config.get("checks", {})

    # Register checks
    if checks.get("registers", {}).get("enabled", False):
        reg_issues = _validate_registers(intermediates, checks["registers"])
        issues.extend(reg_issues)

    # Table checks
    if checks.get("tables", {}).get("enabled", False):
        tbl_issues = _validate_tables(intermediates, checks["tables"])
        issues.extend(tbl_issues)

    # Figure checks
    if checks.get("figures", {}).get("enabled", False):
        fig_issues = _validate_figures(intermediates, checks["figures"])
        issues.extend(fig_issues)

    # Summary
    errors = [i for i in issues if i["severity"] == "error"]
    warnings = [i for i in issues if i["severity"] == "warning"]

    report = {
        "_metadata": {
            "validation_date": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "total_issues": len(issues),
            "errors": len(errors),
            "warnings": len(warnings)
        },
        "issues": issues
    }

    output_path = intermediates / "validation_report.json"
    save_json(report, output_path)

    print(f"  Validation: {len(errors)} errors, {len(warnings)} warnings")
    for issue in errors[:10]:
        print(f"    ERROR: [{issue['node_id']}] {issue['check']}: {issue['message']}")
    for issue in warnings[:10]:
        print(f"    WARN:  [{issue['node_id']}] {issue['check']}: {issue['message']}")
    if len(issues) > 20:
        print(f"    ... and {len(issues) - 20} more (see validation_report.json)")


def _validate_registers(intermediates: Path, reg_checks: dict) -> List[dict]:
    """Validate register fields."""
    issues = []
    rules = {r["check"]: r for r in reg_checks.get("rules", [])}

    reg_path = intermediates / "registers.json"
    if not reg_path.exists():
        return issues

    print_step("VAL 1/3", "Checking registers...")

    data = load_json(reg_path)
    registers = data.get("registers", [])

    for reg in registers:
        reg_id = reg["id"]
        fields = reg.get("fields", [])

        # Check: zero_fields
        if "zero_fields" in rules and len(fields) == 0:
            issues.append({
                "node_id": reg_id,
                "check": "zero_fields",
                "severity": rules["zero_fields"].get("severity", "error"),
                "message": "Register has 0 extracted fields"
            })

        for field in fields:
            field_id = field.get("id", "")

            # Check: field_name_length
            if "field_name_length" in rules:
                max_chars = rules["field_name_length"].get("max_chars", 80)
                name = field.get("name", "")
                if len(name) > max_chars:
                    issues.append({
                        "node_id": field_id,
                        "check": "field_name_length",
                        "severity": "error",
                        "message": f"Field name is {len(name)} chars (max {max_chars}): '{name[:60]}...'"
                    })

            # Check: missing_bits
            if "missing_bits" in rules:
                if not field.get("bits", "").strip():
                    issues.append({
                        "node_id": field_id,
                        "check": "missing_bits",
                        "severity": rules["missing_bits"].get("severity", "warning"),
                        "message": f"Field '{field.get('name', '')}' has empty bit range"
                    })

            # Check: missing_access
            if "missing_access" in rules:
                if not field.get("access", "").strip():
                    issues.append({
                        "node_id": field_id,
                        "check": "missing_access",
                        "severity": rules["missing_access"].get("severity", "warning"),
                        "message": f"Field '{field.get('name', '')}' has empty access type"
                    })

    return issues


def _validate_tables(intermediates: Path, tbl_checks: dict) -> List[dict]:
    """Validate extracted table CSVs."""
    issues = []
    rules = {r["check"]: r for r in tbl_checks.get("rules", [])}
    csv_dir = intermediates / "tables_csv"

    tables_path = intermediates / "tables_page_map.json"
    if not tables_path.exists():
        return issues

    print_step("VAL 2/3", "Checking tables...")

    data = load_json(tables_path)
    for table in data.get("tables", []):
        table_id = table["id"]
        csv_file = csv_dir / f"{table_id}.csv"

        if not csv_file.exists():
            continue

        size = csv_file.stat().st_size

        # Check: empty_csv
        if "empty_csv" in rules and size < 10:
            issues.append({
                "node_id": table_id,
                "check": "empty_csv",
                "severity": rules["empty_csv"].get("severity", "error"),
                "message": f"CSV file is only {size} bytes"
            })
            continue

        # Check: single_row
        if "single_row" in rules:
            try:
                with open(csv_file, 'r', encoding='utf-8') as f:
                    lines = [l.strip() for l in f if l.strip()]
                if len(lines) <= 1:
                    issues.append({
                        "node_id": table_id,
                        "check": "single_row",
                        "severity": rules["single_row"].get("severity", "warning"),
                        "message": "CSV has only header row, no data"
                    })
            except Exception:
                pass

    return issues


def _validate_figures(intermediates: Path, fig_checks: dict) -> List[dict]:
    """Validate extracted figures."""
    issues = []
    rules = {r["check"]: r for r in fig_checks.get("rules", [])}
    puml_dir = intermediates / "figures_plantuml"

    figures_path = intermediates / "figures_page_map.json"
    if not figures_path.exists():
        return issues

    print_step("VAL 3/3", "Checking figures...")

    data = load_json(figures_path)
    for fig in data.get("figures", []):
        fig_id = fig["id"]
        puml_file = puml_dir / f"{fig_id}.puml"

        if not puml_file.exists():
            continue

        content = puml_file.read_text(encoding='utf-8')

        # Check: empty_plantuml
        if "empty_plantuml" in rules and len(content.strip()) < 10:
            issues.append({
                "node_id": fig_id,
                "check": "empty_plantuml",
                "severity": rules["empty_plantuml"].get("severity", "error"),
                "message": "PlantUML file is empty or near-empty"
            })
            continue

        # Check: no_startuml
        if "no_startuml" in rules:
            if "@startuml" not in content.lower():
                issues.append({
                    "node_id": fig_id,
                    "check": "no_startuml",
                    "severity": rules["no_startuml"].get("severity", "warning"),
                    "message": "PlantUML file missing @startuml directive"
                })

    return issues
