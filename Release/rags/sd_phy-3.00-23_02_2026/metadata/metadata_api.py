#!/usr/bin/env python3
"""
RAG V2 Metadata API — Query interface for the metadata graph.

Combines the generic node/relation API with domain-specific helpers
for registers, features, and coverage tracking.

Usage:
    from metadata_api import MetadataAPI
    api = MetadataAPI()
    result = api.search_nodes("clock control")
    
CLI Usage:
    python metadata_api.py get_node_by_id REG_028
    python metadata_api.py search_nodes "clock"
    python metadata_api.py list_registers
    python metadata_api.py get_coverage_summary
"""

import json
import re
import sys
import shutil
import time
from pathlib import Path
from typing import List, Dict, Any, Optional


# =============================================================================
# CONFIGURATION
# =============================================================================

METADATA_PATH = Path(__file__).parent / "metadata.json"
MAX_RESULTS = 1000


# =============================================================================
# RESPONSE HELPERS
# =============================================================================

def _success(function: str, params: dict, results: Any, count: int = None, truncated: bool = False) -> dict:
    if count is None:
        count = len(results) if isinstance(results, list) else 1
    return {
        "success": True,
        "function": function,
        "params": params,
        "count": count,
        "truncated": truncated,
        "results": results,
        "error": None
    }


def _error(function: str, params: dict, error_msg: str) -> dict:
    return {
        "success": False,
        "function": function,
        "params": params,
        "count": 0,
        "truncated": False,
        "results": [],
        "error": error_msg
    }


def _normalize_offset(offset: str) -> str:
    offset = offset.strip().upper()
    if offset.startswith("0X"):
        offset = offset[2:]
    if offset.endswith("H"):
        offset = offset[:-1]
    return offset.zfill(3)


# =============================================================================
# MAIN API CLASS
# =============================================================================

class MetadataAPI:
    """
    Unified API for querying the RAG V2 metadata graph.
    
    All methods return:
    {
        "success": bool,
        "function": str,
        "params": dict,
        "count": int,
        "truncated": bool,
        "results": [...],
        "error": str | None
    }
    """
    
    def __init__(self, metadata_path: Path = None):
        self._path = metadata_path or METADATA_PATH
        self._metadata = None
        self._nodes_by_id = {}
        self._nodes_by_type = {}
        self._relations_by_source = {}
        self._relations_by_target = {}
        self._registers_by_offset = {}
        self._fields_by_id = {}
        self._features_by_group = {}
        self._load()
    
    def _load(self):
        """Load and index metadata."""
        with open(self._path, 'r', encoding='utf-8') as f:
            self._metadata = json.load(f)
        
        for node in self._metadata.get("nodes", []):
            nid = node["id"]
            ntype = node["type"]
            self._nodes_by_id[nid] = node
            self._nodes_by_type.setdefault(ntype, []).append(node)
            
            if ntype == "REGISTER":
                offset = _normalize_offset(node.get("extras", {}).get("offset_hex", ""))
                if offset:
                    self._registers_by_offset[offset] = node
                for field in node.get("extras", {}).get("fields", []):
                    self._fields_by_id[field["id"]] = {**field, "register_id": nid, "register_name": node["name"]}
            
            if ntype == "FEATURE":
                for group in node.get("extras", {}).get("groups", []):
                    self._features_by_group.setdefault(group, []).append(node)
        
        for rel in self._metadata.get("relations", []):
            src, tgt = rel["source_node"], rel["target_node"]
            self._relations_by_source.setdefault(src, []).append(rel)
            self._relations_by_target.setdefault(tgt, []).append(rel)
    
    def _save(self):
        """Save metadata back to disk."""
        backup_dir = self._path.parent / "backups"
        backup_dir.mkdir(exist_ok=True)
        if self._path.exists():
            ts = time.strftime("%Y%m%dT%H%M%S")
            shutil.copy2(self._path, backup_dir / f"metadata_{ts}.json")
        with open(self._path, 'w', encoding='utf-8') as f:
            json.dump(self._metadata, f, indent=2, ensure_ascii=False)
    
    # =========================================================================
    # 1. GENERIC NODE QUERIES
    # =========================================================================
    
    def get_node_by_id(self, node_id: str) -> dict:
        """Get any node by its ID."""
        params = {"node_id": node_id}
        node = self._nodes_by_id.get(node_id)
        if node:
            return _success("get_node_by_id", params, node)
        return _error("get_node_by_id", params, f"NOT_FOUND: '{node_id}'")
    
    def get_nodes_by_type(self, node_type: str) -> dict:
        """Get all nodes of a specific type."""
        params = {"node_type": node_type}
        nodes = self._nodes_by_type.get(node_type.upper(), [])
        return _success("get_nodes_by_type", params, nodes)
    
    def search_nodes(self, query: str, node_type: str = None, limit: int = 20) -> dict:
        """Search nodes by keyword in name, description, or index_keywords."""
        params = {"query": query, "node_type": node_type, "limit": limit}
        query_words = set(query.lower().split())
        results = []
        
        nodes = self._metadata.get("nodes", [])
        if node_type:
            nodes = self._nodes_by_type.get(node_type.upper(), [])
        
        for node in nodes:
            text = " ".join([
                node.get("name", ""),
                node.get("description", ""),
                " ".join(node.get("index_keywords", []))
            ]).lower()
            matches = sum(1 for w in query_words if w in text)
            if matches > 0:
                results.append((matches, node))
        
        results.sort(key=lambda x: -x[0])
        results = [r[1] for r in results[:limit]]
        return _success("search_nodes", params, results)
    
    def list_all_types(self) -> dict:
        """List all node types and their counts."""
        counts = {t: len(nodes) for t, nodes in self._nodes_by_type.items()}
        return _success("list_all_types", {}, counts)
    
    def search_by_keywords(self, keywords: str, node_types: str = None, limit: int = 20) -> dict:
        """Search across multiple node types by keywords."""
        return self.search_nodes(keywords, node_types, limit)
    
    # =========================================================================
    # 2. RELATION QUERIES
    # =========================================================================
    
    def get_relations_from(self, node_id: str, relation_type: str = None) -> dict:
        """Get all relations where node_id is the source."""
        rels = self._relations_by_source.get(node_id, [])
        if relation_type:
            rels = [r for r in rels if r.get("type") == relation_type.upper()]
        return _success("get_relations_from", {"node_id": node_id}, rels)
    
    def get_relations_to(self, node_id: str, relation_type: str = None) -> dict:
        """Get all relations where node_id is the target."""
        rels = self._relations_by_target.get(node_id, [])
        if relation_type:
            rels = [r for r in rels if r.get("type") == relation_type.upper()]
        return _success("get_relations_to", {"node_id": node_id}, rels)
    
    def get_chunks_referencing(self, node_id: str) -> dict:
        """Get SPEC_CHUNK nodes that reference a given node."""
        rels = self._relations_by_target.get(node_id, [])
        ref_rels = [r for r in rels if r.get("type") == "REFERENCES"]
        nodes = [self._nodes_by_id[r["source_node"]] for r in ref_rels if r["source_node"] in self._nodes_by_id]
        return _success("get_chunks_referencing", {"node_id": node_id}, nodes)
    
    # =========================================================================
    # 3. REGISTER QUERIES
    # =========================================================================
    
    def get_register_by_offset(self, offset: str) -> dict:
        """Get register by hex offset (e.g., '028h', '0x028')."""
        params = {"offset": offset}
        try:
            norm = _normalize_offset(offset)
        except Exception:
            return _error("get_register_by_offset", params, f"INVALID_PARAM: '{offset}'")
        reg = self._registers_by_offset.get(norm)
        if reg:
            return _success("get_register_by_offset", params, reg)
        return _error("get_register_by_offset", params, f"NOT_FOUND: offset {norm}h")
    
    def get_register_by_id(self, register_id: str) -> dict:
        """Get register by exact ID."""
        params = {"register_id": register_id}
        node = self._nodes_by_id.get(register_id)
        if not node:
            return _error("get_register_by_id", params, f"NOT_FOUND: '{register_id}'")
        if node["type"] != "REGISTER":
            return _error("get_register_by_id", params, f"INVALID_TYPE: {node['type']}")
        return _success("get_register_by_id", params, node)
    
    def get_register_by_name(self, name: str, exact: bool = False) -> dict:
        """Get registers matching name pattern."""
        params = {"name": name, "exact": exact}
        name_lower = name.lower()
        registers = self._nodes_by_type.get("REGISTER", [])
        matches = [r for r in registers if (r["name"].lower() == name_lower if exact else name_lower in r["name"].lower())]
        if not matches:
            return _error("get_register_by_name", params, f"NOT_FOUND: '{name}'")
        summaries = [{"id": r["id"], "name": r["name"], "offset": r.get("extras", {}).get("offset_hex", "")} for r in matches]
        return _success("get_register_by_name", params, summaries)
    
    def list_registers(self, class_id: str = None) -> dict:
        """List all registers, optionally filtered by class."""
        params = {"class_id": class_id}
        registers = self._nodes_by_type.get("REGISTER", [])
        if class_id:
            registers = [r for r in registers if r.get("extras", {}).get("class_id") == class_id]
        registers = sorted(registers, key=lambda r: _normalize_offset(r.get("extras", {}).get("offset_hex", "ZZZ")))
        summaries = [{"id": r["id"], "name": r["name"], "offset": r.get("extras", {}).get("offset_hex", ""), "field_count": len(r.get("extras", {}).get("fields", []))} for r in registers]
        return _success("list_registers", params, summaries)
    
    def get_register_class_by_id(self, class_id: str) -> dict:
        """Get register class with member register IDs."""
        params = {"class_id": class_id}
        node = self._nodes_by_id.get(class_id)
        if not node or node["type"] != "REG_CLASS":
            return _error("get_register_class_by_id", params, f"NOT_FOUND: '{class_id}'")
        members = [r["id"] for r in self._nodes_by_type.get("REGISTER", []) if r.get("extras", {}).get("class_id") == class_id]
        return _success("get_register_class_by_id", params, {**node, "member_register_ids": members})
    
    def list_register_classes(self) -> dict:
        """List all register classes."""
        classes = self._nodes_by_type.get("REG_CLASS", [])
        summaries = [{"id": c["id"], "name": c["name"]} for c in classes]
        return _success("list_register_classes", {}, summaries)
    
    # =========================================================================
    # 4. FIELD QUERIES
    # =========================================================================
    
    def get_field_by_id(self, field_id: str) -> dict:
        """Get register field by ID."""
        params = {"field_id": field_id}
        f = self._fields_by_id.get(field_id)
        if f:
            return _success("get_field_by_id", params, f)
        return _error("get_field_by_id", params, f"NOT_FOUND: '{field_id}'")
    
    def list_fields_in_register(self, register_id: str) -> dict:
        """List all fields in a register."""
        params = {"register_id": register_id}
        reg = self._nodes_by_id.get(register_id)
        if not reg or reg["type"] != "REGISTER":
            return _error("list_fields_in_register", params, f"NOT_FOUND: '{register_id}'")
        fields = reg.get("extras", {}).get("fields", [])
        summaries = [{"id": f["id"], "name": f["name"], "bits": f.get("bits", ""), "access": f.get("access", "")} for f in fields]
        return _success("list_fields_in_register", params, summaries)
    
    def search_fields_by_name(self, pattern: str) -> dict:
        """Search fields by name across all registers."""
        params = {"pattern": pattern}
        pattern_lower = pattern.lower()
        results = [f for f in self._fields_by_id.values() if pattern_lower in f["name"].lower()]
        return _success("search_fields_by_name", params, results[:MAX_RESULTS])
    
    # =========================================================================
    # 5. TABLE & FIGURE QUERIES
    # =========================================================================
    
    def get_table_by_id(self, table_id: str) -> dict:
        """Get table by ID (e.g., TABLE_1_1)."""
        return self.get_node_by_id(table_id)
    
    def list_tables(self) -> dict:
        """List all tables."""
        return self.get_nodes_by_type("TABLE")
    
    def get_table_csv(self, table_id: str) -> dict:
        """Get CSV content for a table."""
        params = {"table_id": table_id}
        node = self._nodes_by_id.get(table_id)
        if not node or node["type"] != "TABLE":
            return _error("get_table_csv", params, f"NOT_FOUND: '{table_id}'")
        csv_file = node.get("extras", {}).get("csv_file", "")
        if not csv_file:
            return _error("get_table_csv", params, f"NO_CSV: Table not yet converted")
        csv_path = self._path.parent.parent / csv_file
        if not csv_path.exists():
            return _error("get_table_csv", params, f"FILE_MISSING: {csv_file}")
        content = csv_path.read_text(encoding='utf-8')
        return _success("get_table_csv", params, {"csv_file": csv_file, "content": content})
    
    def get_figure_by_id(self, figure_id: str) -> dict:
        """Get figure by ID (e.g., FIG_1_1)."""
        return self.get_node_by_id(figure_id)
    
    def list_figures(self) -> dict:
        """List all figures."""
        return self.get_nodes_by_type("FIGURE")
    
    def get_figure_plantuml(self, figure_id: str) -> dict:
        """Get PlantUML content for a figure."""
        params = {"figure_id": figure_id}
        node = self._nodes_by_id.get(figure_id)
        if not node or node["type"] != "FIGURE":
            return _error("get_figure_plantuml", params, f"NOT_FOUND: '{figure_id}'")
        puml_file = node.get("extras", {}).get("text_diagram_file", "")
        if not puml_file:
            return _error("get_figure_plantuml", params, f"NO_PLANTUML: Figure not yet transcribed")
        puml_path = self._path.parent.parent / puml_file
        if not puml_path.exists():
            return _error("get_figure_plantuml", params, f"FILE_MISSING: {puml_file}")
        content = puml_path.read_text(encoding='utf-8')
        return _success("get_figure_plantuml", params, {"plantuml_file": puml_file, "content": content})
    
    # =========================================================================
    # 6. FEATURE & HD_SEQUENCE QUERIES
    # =========================================================================
    
    def get_feature_by_id(self, feature_id: str) -> dict:
        """Get feature by ID."""
        return self.get_node_by_id(feature_id)
    
    def list_features(self) -> dict:
        """List all features."""
        return self.get_nodes_by_type("FEATURE")
    
    def get_feature_tree(self) -> dict:
        """Get feature hierarchy as a tree."""
        features = self._nodes_by_type.get("FEATURE", [])
        tree = []
        for f in features:
            parent = f.get("extras", {}).get("parent_id")
            if not parent:
                tree.append({
                    "id": f["id"],
                    "name": f["name"],
                    "priority": f.get("extras", {}).get("priority", ""),
                    "children": [
                        {"id": c["id"], "name": c["name"], "priority": c.get("extras", {}).get("priority", "")}
                        for c in features if c.get("extras", {}).get("parent_id") == f["id"]
                    ]
                })
        return _success("get_feature_tree", {}, tree)
    
    def get_feature_groups(self) -> dict:
        """Get all feature groups and their members."""
        return _success("get_feature_groups", {}, {
            g: [{"id": f["id"], "name": f["name"]} for f in fs]
            for g, fs in self._features_by_group.items()
        })
    
    def list_hd_sequences(self) -> dict:
        """List all HD sequences."""
        return self.get_nodes_by_type("HD_SEQUENCE")
    
    def get_hd_sequence_by_id(self, seq_id: str) -> dict:
        """Get HD sequence by ID."""
        return self.get_node_by_id(seq_id)
    
    # =========================================================================
    # 7. SPEC CONTENT QUERIES
    # =========================================================================
    
    def get_chunk_by_id(self, chunk_id: str) -> dict:
        """Get a spec chunk by ID."""
        return self.get_node_by_id(chunk_id)
    
    def list_sections(self) -> dict:
        """List all unique sections from SPEC_CHUNK nodes."""
        chunks = self._nodes_by_type.get("SPEC_CHUNK", [])
        sections = {}
        for c in chunks:
            sec_num = c.get("extras", {}).get("section_number", "")
            if sec_num and sec_num not in sections:
                sections[sec_num] = {
                    "section_number": sec_num,
                    "title": c.get("extras", {}).get("section_title", ""),
                    "chunk_count": 0
                }
            if sec_num:
                sections[sec_num]["chunk_count"] += 1
        return _success("list_sections", {}, list(sections.values()))
    
    def get_page_content(self, spec_page: int) -> dict:
        """Get all chunks that appear on a specific spec page."""
        params = {"spec_page": spec_page}
        chunks = [c for c in self._nodes_by_type.get("SPEC_CHUNK", []) if c.get("source", {}).get("page") == spec_page]
        return _success("get_page_content", params, chunks)
    
    def search_chunks_by_text(self, text: str, limit: int = 10) -> dict:
        """Full-text search across SPEC_CHUNK full_text fields."""
        params = {"text": text, "limit": limit}
        text_lower = text.lower()
        results = []
        for c in self._nodes_by_type.get("SPEC_CHUNK", []):
            full_text = c.get("extras", {}).get("full_text", "").lower()
            if text_lower in full_text:
                results.append(c)
                if len(results) >= limit:
                    break
        return _success("search_chunks_by_text", params, results)
    
    # =========================================================================
    # 8. COVERAGE MANAGEMENT
    # =========================================================================
    
    def set_node_coverage_status(self, node_id: str, status: str,
                                  notes: str = "", implemented_in: str = "") -> dict:
        """Set coverage status on any node. Writes to disk."""
        params = {"node_id": node_id, "status": status}
        valid = {"NOT_IMPLEMENTED", "PARTIAL", "IMPLEMENTED", "NOT_APPLICABLE"}
        if status not in valid:
            return _error("set_node_coverage_status", params, f"INVALID_STATUS: must be one of {valid}")
        
        node = self._nodes_by_id.get(node_id)
        if not node:
            return _error("set_node_coverage_status", params, f"NOT_FOUND: '{node_id}'")
        
        node["coverage"] = {"status": status, "notes": notes, "implemented_in": implemented_in}
        self._save()
        return _success("set_node_coverage_status", params, node["coverage"])
    
    def get_node_coverage_status(self, node_id: str) -> dict:
        """Get coverage status of a node."""
        params = {"node_id": node_id}
        node = self._nodes_by_id.get(node_id)
        if not node:
            return _error("get_node_coverage_status", params, f"NOT_FOUND: '{node_id}'")
        return _success("get_node_coverage_status", params, node.get("coverage", {}))
    
    def list_nodes_by_coverage(self, status: str, node_type: str = None) -> dict:
        """List nodes by coverage status."""
        params = {"status": status, "node_type": node_type}
        nodes = self._metadata.get("nodes", [])
        if node_type:
            nodes = self._nodes_by_type.get(node_type.upper(), [])
        matches = [n for n in nodes if n.get("coverage", {}).get("status") == status]
        summaries = [{"id": n["id"], "type": n["type"], "name": n["name"]} for n in matches]
        return _success("list_nodes_by_coverage", params, summaries)
    
    def get_coverage_summary(self) -> dict:
        """Get coverage summary by node type."""
        summary = {}
        for ntype, nodes in self._nodes_by_type.items():
            by_status = {}
            for n in nodes:
                s = n.get("coverage", {}).get("status", "NOT_IMPLEMENTED")
                by_status[s] = by_status.get(s, 0) + 1
            summary[ntype] = by_status
        return _success("get_coverage_summary", {}, summary)
    
    # =========================================================================
    # 9. METADATA INFO
    # =========================================================================
    
    def get_spec_info(self) -> dict:
        """Get spec info and extraction statistics."""
        return _success("get_spec_info", {}, {
            "spec_info": self._metadata.get("spec_info", {}),
            "extraction_info": self._metadata.get("extraction_info", {}),
            "metadata_version": self._metadata.get("metadata_version", "")
        })
    
    def get_register_map(self) -> dict:
        """Get register offset map for navigation."""
        registers = sorted(
            self._nodes_by_type.get("REGISTER", []),
            key=lambda r: int(_normalize_offset(r.get("extras", {}).get("offset_hex", "0")), 16)
        )
        return _success("get_register_map", {}, [
            {"offset": r.get("extras", {}).get("offset_hex", ""), "id": r["id"], "name": r["name"]}
            for r in registers
        ])


# =============================================================================
# CLI INTERFACE
# =============================================================================

def main():
    """CLI entry point: python metadata_api.py <function> [args...]"""
    if len(sys.argv) < 2:
        print("Usage: python metadata_api.py <function> [args...]")
        print("\nAvailable functions:")
        api = MetadataAPI.__new__(MetadataAPI)
        for name in sorted(dir(MetadataAPI)):
            if not name.startswith('_'):
                func = getattr(MetadataAPI, name)
                if callable(func):
                    doc = (func.__doc__ or "").strip().split('\n')[0]
                    print(f"  {name:35s} {doc}")
        sys.exit(1)
    
    func_name = sys.argv[1]
    args = sys.argv[2:]
    
    try:
        api = MetadataAPI()
    except FileNotFoundError:
        print(f"ERROR: {METADATA_PATH} not found. Run the pipeline first.")
        sys.exit(1)
    
    if not hasattr(api, func_name):
        print(f"ERROR: Unknown function '{func_name}'")
        sys.exit(1)
    
    func = getattr(api, func_name)
    
    # Convert string args
    kwargs = {}
    positional = []
    for arg in args:
        if '=' in arg:
            k, v = arg.split('=', 1)
            # Try to parse as int/bool
            if v.isdigit():
                v = int(v)
            elif v.lower() in ('true', 'false'):
                v = v.lower() == 'true'
            kwargs[k] = v
        else:
            positional.append(arg)
    
    try:
        if positional and kwargs:
            result = func(*positional, **kwargs)
        elif positional:
            result = func(*positional)
        elif kwargs:
            result = func(**kwargs)
        else:
            result = func()
    except TypeError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
