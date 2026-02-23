#!/usr/bin/env python3
"""
Phase 2d: Extract domain-specific nodes (registers, features, HD sequences).

Reads config for register classes, feature definitions, etc.
Uses table CSVs to extract register fields with LLM abstracts.

Depends on: Phase 1 discovery.json, Phase 2b tables_page_map.json + CSVs
Output: intermediates/registers.json, intermediates/features.json
"""

import json
import csv
import re
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.config import (
    get_register_classes, get_register_offsets, get_exclude_tables,
    get_feature_definitions, get_hd_sequence_definitions,
    get_llm_config, get_intermediates_dir, get_tables_csv_dir,
    find_matching_hint, PIPELINE_ROOT
)
from shared.llm_client import LLMClient
from shared.utils import (
    load_json, save_json, extract_keywords, normalize_offset,
    format_offset, print_step
)


def extract_domain_nodes(config: dict,
                         skip_existing: bool = False,
                         model: str = None,
                         workers: int = None):
    """Main entry point for domain node extraction."""
    
    # Extract registers
    if config.get("domain", {}).get("registers", {}).get("enabled", False):
        _extract_registers(config, skip_existing, model, workers)
    
    # Extract features
    if config.get("domain", {}).get("features", {}).get("enabled", False):
        _extract_features(config, skip_existing, model, workers)


# =============================================================================
# REGISTER EXTRACTION
# =============================================================================

def _extract_registers(config: dict, skip_existing: bool, model: str, workers: int):
    """Extract register nodes from table CSVs."""
    intermediates = get_intermediates_dir()
    csv_dir = get_tables_csv_dir()
    output_path = intermediates / "registers.json"
    
    print_step("REG 1/3", "Loading register definitions from config...")
    
    register_classes = get_register_classes(config)
    register_offsets = get_register_offsets(config)
    exclude_tables = get_exclude_tables(config)
    
    # Load tables map
    tables_map_path = intermediates / "tables_page_map.json"
    if not tables_map_path.exists():
        print("  WARNING: tables_page_map.json not found, skipping register extraction")
        return
    tables_map = load_json(tables_map_path)
    
    # Build register class nodes
    reg_class_nodes = []
    for rc in register_classes:
        reg_class_nodes.append({
            "id": rc["id"],
            "type": "REG_CLASS",
            "name": rc["name"],
            "address_start": rc["address_start"],
            "address_end": rc["address_end"],
            "table_1_1_name": rc.get("table_1_1_name", ""),
            "registers": []
        })
    
    print(f"    Register classes: {len(reg_class_nodes)}")
    
    # Find register tables (title contains "Register" and not in exclude list)
    print_step("REG 2/3", "Identifying register field tables...")
    register_tables = []
    all_tables_by_id = {}  # Full lookup including excluded – for config overrides
    for table in tables_map.get("tables", []):
        table_id = table["id"]
        csv_file = csv_dir / f"{table_id}.csv"
        if not csv_file.exists():
            continue
        entry = {
            "table_id": table_id,
            "title": table["title"],
            "csv_file": csv_file,
            "spec_page": table.get("spec_page", 0)
        }
        all_tables_by_id[table_id] = entry
        if table_id in exclude_tables:
            continue
        title = table.get("title", "").lower()
        if "register" in title:
            register_tables.append(entry)
    
    print(f"    Register tables found: {len(register_tables)}")
    
    # Parse CSVs to extract register fields
    print_step("REG 3/3", "Extracting register fields from CSVs...")
    
    llm_config = get_llm_config(config)
    num_workers = workers or llm_config.get("max_workers", 4)
    llm = LLMClient(config, model_override=model)
    
    registers = []
    for offset_str, reg_info in register_offsets.items():
        offset_norm = normalize_offset(offset_str)
        reg_id = f"REG_{offset_norm}"
        
        # Find matching register table:
        # 1) Config-driven override (bypasses exclusion + name matching)
        # 2) Fallback to auto name matching
        table_override = reg_info.get("table")
        if table_override and table_override in all_tables_by_id:
            matching_table = all_tables_by_id[table_override]
        else:
            matching_table = _find_register_table(register_tables, reg_info["name"])
        
        # Determine register class
        class_id = _find_register_class(register_classes, offset_str)
        
        reg = {
            "id": reg_id,
            "name": reg_info["name"],
            "offset": offset_str,
            "spec_section": reg_info.get("section", ""),
            "spec_table": matching_table["table_id"] if matching_table else "",
            "class_id": class_id,
            "fields": [],
            "source": {
                "page": 0,
                "definition_page": 0
            }
        }
        
        # Extract fields from CSV if available
        if matching_table:
            hint = find_matching_hint(config, matching_table["title"])
            fields = _parse_register_csv(matching_table["csv_file"], reg_id, hint)
            reg["fields"] = fields
            reg["source"]["page"] = matching_table.get("spec_page", 0)
        
        registers.append(reg)
    
    # Generate field abstracts via LLM (batch)
    all_fields = [f for r in registers for f in r.get("fields", []) if not f.get("abstract")]
    if all_fields:
        print(f"    Generating abstracts for {len(all_fields)} fields...")
        _generate_field_abstracts(llm, all_fields, num_workers)
    
    # Build output
    output = {
        "_metadata": {
            "source": config["spec"]["name"],
            "extraction_date": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "total_register_classes": len(reg_class_nodes),
            "total_registers": len(registers),
            "total_fields": sum(len(r["fields"]) for r in registers),
            "llm_stats": llm.stats
        },
        "register_classes": reg_class_nodes,
        "registers": registers
    }
    
    save_json(output, output_path)
    print(f"  Registers: {len(registers)}, Fields: {output['_metadata']['total_fields']}")


def _find_register_table(register_tables: List[dict], reg_name: str) -> Optional[dict]:
    """Find the CSV table that defines a register."""
    reg_name_lower = reg_name.lower()
    for table in register_tables:
        # Match by checking if key words from register name appear in table title
        title_lower = table["title"].lower()
        # Extract main name (before "Register")
        main_name = reg_name_lower.replace(" register", "").strip()
        if main_name in title_lower:
            return table
    return None


def _find_register_class(classes: List[dict], offset_str: str) -> str:
    """Find which register class an offset belongs to."""
    offset_val = int(normalize_offset(offset_str), 16)
    for rc in classes:
        start = int(normalize_offset(rc["address_start"]), 16)
        end = int(normalize_offset(rc["address_end"]), 16)
        if start <= offset_val <= end:
            return rc["id"]
    return ""


def _parse_register_csv(csv_path: Path, reg_id: str,
                        hint: Optional[dict] = None) -> List[dict]:
    """Parse a register field CSV into field dicts.
    
    Uses hint-driven column mapping when available:
    - Maps CSV headers to semantic roles (bit_range, access, field_name, description)
    - Handles merged name+description columns (3-column format)
    """
    fields = []
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Strip markdown fences that LLM sometimes leaves in
        content = _strip_markdown_fences(content)
        
        import io
        reader = csv.DictReader(io.StringIO(content))
        col_map = _build_column_map(list(reader.fieldnames or []), hint)
        
        is_merged = col_map.get("_merged_name_desc", False)
        bit_col = col_map.get("bit_range")
        access_col = col_map.get("access")
        name_col = col_map.get("field_name")
        desc_col = col_map.get("description")
        
        # Group consecutive rows: a new group starts when bit_range is non-empty.
        # Rows with empty bit_range are continuations (description/enum values).
        # This handles multi-row field definitions generically.
        raw_rows = list(reader)
        groups = []
        for row in raw_rows:
            bits = row.get(bit_col, "").strip() if bit_col else ""
            if bits:
                groups.append({"primary": row, "continuations": []})
            elif groups:
                groups[-1]["continuations"].append(row)
        
        for i, group in enumerate(groups):
            row = group["primary"]
            cont_texts = []
            for cr in group["continuations"]:
                val = cr.get(desc_col or name_col or "", "").strip()
                if val:
                    cont_texts.append(val)
            
            if is_merged and desc_col:
                # Name and description merged in one column
                raw_value = row.get(desc_col, "").strip()
                if not raw_value:
                    continue
                # Split: first line = field name, rest = description
                lines = raw_value.split('\n')
                field_name = lines[0].strip()
                desc = '\n'.join(lines[1:]).strip()
                # Append continuation rows as description
                if cont_texts:
                    desc = (desc + '\n' + '\n'.join(cont_texts)).strip()
            elif name_col:
                field_name = row.get(name_col, f"FIELD_{i}").strip()
                desc = row.get(desc_col, "").strip() if desc_col else ""
                # Append continuation rows as description
                if cont_texts:
                    desc = (desc + '\n' + '\n'.join(cont_texts)).strip()
            else:
                continue
            
            if not field_name or field_name.lower() in ["reserved", "rsvd"]:
                continue
            
            # Safety: if field_name is suspiciously long, try to split
            if len(field_name) > 80 and '\n' in field_name:
                parts = field_name.split('\n')
                field_name = parts[0].strip()
                desc = '\n'.join(parts[1:]).strip() + ('\n' + desc if desc else '')
            
            bits = row.get(bit_col, "").strip() if bit_col else ""
            access = row.get(access_col, "").strip() if access_col else ""
            
            # Parse bit range
            bit_high, bit_low, width = _parse_bit_range(bits)
            
            field_id = f"{reg_id}_F{i}"
            fields.append({
                "id": field_id,
                "name": field_name,
                "bits": bits,
                "bit_high": bit_high,
                "bit_low": bit_low,
                "width": width,
                "access": _normalize_access(access),
                "original_attrib": access,
                "raw": desc,
                "abstract": "",
                "values": []
            })
    except Exception as e:
        print(f"    Warning: Failed to parse {csv_path.name}: {e}")
    
    return fields


def _strip_markdown_fences(text: str) -> str:
    """Strip ```csv ... ``` markdown fences from CSV content."""
    text = text.strip()
    if text.startswith('```'):
        lines = text.split('\n')
        # Remove opening fence
        lines = lines[1:]
        # Remove closing fence
        if lines and lines[-1].strip().startswith('```'):
            lines = lines[:-1]
        text = '\n'.join(lines)
    return text


def _build_column_map(fieldnames: List[str], hint: Optional[dict] = None) -> dict:
    """Map CSV column names to semantic roles using hint or heuristics.
    
    Returns dict with keys: 'bit_range', 'access', 'field_name', 'description'.
    Special key '_merged_name_desc' = True if name and description share one column.
    
    Priority system: when a column header matches multiple roles,
    higher-priority roles win (description > field_name).
    """
    if not fieldnames:
        return {}
    
    # Role -> (priority, search_terms)
    # Higher priority wins when a column matches multiple roles.
    role_keywords = {
        "bit_range":   (4, ["bit", "location", "position", "bits"]),
        "access":      (3, ["access", "attrib", "type", "r/w", "attribute"]),
        "description": (2, ["description", "function", "explanation", "desc"]),
        "field_name":  (1, ["field name", "signal name", "name", "field"]),
    }
    
    # Override with hint aliases if available
    if hint and hint.get("expected_columns"):
        for col_def in hint["expected_columns"]:
            role = col_def["role"]
            names = [n.lower() for n in col_def.get("names", [])]
            if role in role_keywords:
                role_keywords[role] = (role_keywords[role][0], names)
    
    col_map = {}
    used_columns = set()
    
    # First pass: exact match on full column name
    for fname in fieldnames:
        fl = fname.strip().lower()
        for role, (priority, keywords) in role_keywords.items():
            if fl in keywords and fname not in used_columns and role not in col_map:
                col_map[role] = fname
                used_columns.add(fname)
                break
    
    # Second pass: substring match, resolving conflicts by priority
    remaining = {r: kw for r, kw in role_keywords.items() if r not in col_map}
    for fname in fieldnames:
        if fname in used_columns:
            continue
        fl = fname.strip().lower()
        matching_roles = []
        for role, (priority, keywords) in remaining.items():
            if any(kw in fl for kw in keywords):
                matching_roles.append((priority, role))
        if matching_roles:
            matching_roles.sort(reverse=True)
            best_role = matching_roles[0][1]
            col_map[best_role] = fname
            used_columns.add(fname)
            del remaining[best_role]
    
    # Detect merged name+description: if no field_name column found
    if "field_name" not in col_map and "description" in col_map:
        col_map["_merged_name_desc"] = True
    
    return col_map


def _parse_bit_range(bits_str: str) -> tuple:
    """Parse bit range string to (high, low, width)."""
    bits_str = bits_str.strip()
    
    # "7-4" or "7:4"
    match = re.match(r'(\d+)\s*[-:]\s*(\d+)', bits_str)
    if match:
        high = int(match.group(1))
        low = int(match.group(2))
        return high, low, high - low + 1
    
    # Single bit "7"
    match = re.match(r'^(\d+)$', bits_str)
    if match:
        bit = int(match.group(1))
        return bit, bit, 1
    
    return 0, 0, 0


def _normalize_access(access: str) -> str:
    """Normalize access type string."""
    access = access.strip().upper()
    mapping = {
        "RW": "read-write",
        "R/W": "read-write",
        "READ-WRITE": "read-write",
        "RO": "read-only",
        "R": "read-only",
        "READ-ONLY": "read-only",
        "WO": "write-only",
        "W": "write-only",
        "WRITE-ONLY": "write-only",
        "ROC": "read-only-clear",
        "RW1C": "read-write-1-clear",
        "W1C": "write-1-clear",
        "RSVD": "reserved",
    }
    return mapping.get(access, access.lower() if access else "")


def _generate_field_abstracts(llm: LLMClient, fields: List[dict], workers: int):
    """Generate LLM abstracts for register fields."""
    system_prompt = """You are a hardware register field specialist. Given a register field's raw description, produce a concise 1-sentence abstract. Respond with JUST the abstract text, no JSON."""
    
    completed = 0
    total = len(fields)
    
    for field in fields:
        raw = field.get("raw", "")[:500]
        if not raw:
            field["abstract"] = field["name"]
            completed += 1
            continue
        
        try:
            abstract = llm.call(
                system_prompt,
                f"Field: {field['name']}\nBits: {field['bits']}\nAccess: {field['access']}\nDescription: {raw}",
                max_tokens=256
            )
            field["abstract"] = abstract.strip()
        except Exception:
            field["abstract"] = field["name"]
        
        completed += 1
        if completed % 20 == 0 or completed == total:
            print(f"      Field abstracts: {completed}/{total}")


# =============================================================================
# FEATURE EXTRACTION
# =============================================================================

def _extract_features(config: dict, skip_existing: bool, model: str, workers: int):
    """Extract feature and HD sequence nodes from config definitions."""
    intermediates = get_intermediates_dir()
    output_path = intermediates / "features.json"
    
    print_step("FEAT 1/2", "Building feature skeleton from config...")
    
    feature_defs = get_feature_definitions(config)
    hd_seq_defs = get_hd_sequence_definitions(config)
    
    # Build feature nodes
    features = []
    for fdef in feature_defs:
        features.append({
            "id": fdef["id"],
            "type": "FEATURE",
            "name": fdef["name"],
            "description": "",
            "groups": fdef.get("groups", []),
            "priority": fdef.get("priority", "P0"),
            "parent_id": fdef.get("parent"),
            "figures": [],
            "tables": [],
            "registers": [],
            "spec_sections": [],
            "index_keywords": [],
            "confidence": 1.0,
            "validation_status": "SKELETON",
            "extras": {}
        })
    
    # Build HD sequence nodes
    hd_sequences = []
    for hdef in hd_seq_defs:
        hd_sequences.append({
            "id": hdef["id"],
            "type": "HD_SEQUENCE",
            "name": hdef["name"],
            "description": "",
            "groups": hdef.get("groups", []),
            "primary_spec_section": hdef.get("primary_section", ""),
            "figures": [],
            "tables": [],
            "spec_sections": [],
            "uses_features": [],
            "index_keywords": [],
            "confidence": 1.0,
            "validation_status": "SKELETON",
            "extras": {}
        })
    
    # Build PART_OF relations
    relations = []
    rel_counter = 0
    for f in features:
        if f["parent_id"]:
            rel_counter += 1
            relations.append({
                "id": f"REL_PART_OF_{rel_counter:03d}",
                "type": "PART_OF",
                "source_node": f["id"],
                "target_node": f["parent_id"],
                "description": f"{f['name']} is part of {f['parent_id']}"
            })
    
    print(f"    Features: {len(features)}, HD Sequences: {len(hd_sequences)}, Relations: {len(relations)}")
    
    # Optionally enrich with LLM
    print_step("FEAT 2/2", "Enriching features with LLM descriptions...")
    
    llm_config = get_llm_config(config)
    num_workers = workers or llm_config.get("max_workers", 4)
    llm = LLMClient(config, model_override=model)
    
    # Load sections for context
    sections_path = intermediates / "sections.json"
    sections_context = ""
    if sections_path.exists():
        sections_data = load_json(sections_path)
        # Build brief section index
        section_titles = []
        for sec_num, sec in sections_data.get("sections", {}).items():
            section_titles.append(f"{sec_num}: {sec['title']}")
        sections_context = "\n".join(section_titles[:100])
    
    # Enrich features with descriptions
    for feature in features:
        if feature.get("description"):
            continue
        
        try:
            desc = _enrich_feature(llm, feature, sections_context)
            feature["description"] = desc
            feature["validation_status"] = "AUTO"
            feature["index_keywords"] = extract_keywords(feature["name"] + " " + desc)
        except Exception as e:
            feature["description"] = f"[Enrichment failed: {str(e)[:100]}]"
    
    # Build output
    output = {
        "_metadata": {
            "source": config["spec"]["name"],
            "extraction_date": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "total_features": len(features),
            "total_hd_sequences": len(hd_sequences),
            "total_relations": len(relations),
            "llm_stats": llm.stats
        },
        "features": features,
        "hd_sequences": hd_sequences,
        "relations": relations
    }
    
    save_json(output, output_path)
    print(f"  Features: {len(features)}, HD Sequences: {len(hd_sequences)}")


def _enrich_feature(llm: LLMClient, feature: dict, sections_context: str) -> str:
    """Enrich a feature with LLM-generated description."""
    system_prompt = """You are a hardware specification expert. Given a feature name and its groups, provide a concise 2-3 sentence description of what this feature does in the context of an SD Host Controller. Be specific and technical."""
    
    prompt = f"""Feature: {feature['name']} (ID: {feature['id']})
Groups: {', '.join(feature['groups'])}
Priority: {feature['priority']}
Parent: {feature.get('parent_id', 'None (top-level)')}

Available spec sections:
{sections_context[:1500]}

Describe this feature's purpose and behavior."""
    
    response = llm.call(system_prompt, prompt, max_tokens=512)
    return response.strip()
