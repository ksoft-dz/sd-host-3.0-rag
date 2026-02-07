#!/usr/bin/env python3
"""
Generic RAG Metadata API

Provides query functions for accessing the unified metadata graph.
Designed for LLM agent use with predictable inputs and outputs.

Usage:
    from metadata_api import MetadataAPI
    api = MetadataAPI()
    result = api.search_nodes("keyword")
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

# =============================================================================
# CONFIGURATION
# =============================================================================

METADATA_PATH = Path(__file__).parent / "metadata.json"
MAX_RESULTS = 100

# =============================================================================
# RESPONSE HELPERS
# =============================================================================

def _success(function: str, params: dict, results: Any, count: int = None) -> dict:
    """Build a successful response."""
    if count is None:
        count = len(results) if isinstance(results, list) else 1
    return {
        "success": True,
        "function": function,
        "params": params,
        "count": count,
        "results": results,
        "error": None
    }


def _error(function: str, params: dict, error_msg: str) -> dict:
    """Build an error response."""
    return {
        "success": False,
        "function": function,
        "params": params,
        "count": 0,
        "results": [],
        "error": error_msg
    }


# =============================================================================
# MAIN API CLASS
# =============================================================================

class MetadataAPI:
    """
    API for accessing specification metadata graph.
    
    All methods return a consistent response dict:
    {
        "success": bool,
        "function": str,
        "params": dict,
        "count": int,
        "results": [...],
        "error": str | None
    }
    """
    
    def __init__(self, metadata_path: Path = None):
        """Initialize API with metadata file path."""
        self.metadata_path = metadata_path or METADATA_PATH
        self._data = None
        self._nodes_by_id = {}
        self._nodes_by_type = {}
        self._relations_by_source = {}
        self._relations_by_target = {}
    
    def _load(self):
        """Load metadata if not already loaded."""
        if self._data is not None:
            return
        
        with open(self.metadata_path, 'r', encoding='utf-8') as f:
            self._data = json.load(f)
        
        # Build indexes
        for node in self._data.get("nodes", []):
            if node.get("_comment"):
                continue
            self._nodes_by_id[node["id"]] = node
            node_type = node.get("type", "UNKNOWN")
            if node_type not in self._nodes_by_type:
                self._nodes_by_type[node_type] = []
            self._nodes_by_type[node_type].append(node)
        
        for rel in self._data.get("relations", []):
            if rel.get("_comment"):
                continue
            src = rel.get("source_node")
            tgt = rel.get("target_node")
            if src:
                if src not in self._relations_by_source:
                    self._relations_by_source[src] = []
                self._relations_by_source[src].append(rel)
            if tgt:
                if tgt not in self._relations_by_target:
                    self._relations_by_target[tgt] = []
                self._relations_by_target[tgt].append(rel)
    
    # =========================================================================
    # NODE QUERIES
    # =========================================================================
    
    def get_node_by_id(self, node_id: str) -> dict:
        """Get a single node by its ID."""
        self._load()
        node = self._nodes_by_id.get(node_id)
        if node:
            return _success("get_node_by_id", {"node_id": node_id}, node)
        return _error("get_node_by_id", {"node_id": node_id}, f"Node not found: {node_id}")
    
    def get_nodes_by_type(self, node_type: str) -> dict:
        """Get all nodes of a specific type (TABLE, FIGURE, SPEC_CHUNK, etc.)."""
        self._load()
        nodes = self._nodes_by_type.get(node_type.upper(), [])
        return _success("get_nodes_by_type", {"node_type": node_type}, nodes)
    
    def search_nodes(self, query: str, node_type: str = None, limit: int = 20) -> dict:
        """
        Search nodes by keyword in name, description, or keywords.
        
        Args:
            query: Search query string
            node_type: Optional filter by type (TABLE, FIGURE, SPEC_CHUNK)
            limit: Maximum results to return
        """
        self._load()
        query_lower = query.lower()
        query_words = set(query_lower.split())
        results = []
        
        nodes = self._data.get("nodes", [])
        if node_type:
            nodes = self._nodes_by_type.get(node_type.upper(), [])
        
        for node in nodes:
            if node.get("_comment"):
                continue
            
            # Search in name, description, keywords
            text = " ".join([
                node.get("name", ""),
                node.get("description", ""),
                " ".join(node.get("index_keywords", []))
            ]).lower()
            
            # Score by word matches
            matches = sum(1 for w in query_words if w in text)
            if matches > 0:
                results.append((matches, node))
        
        # Sort by match count descending
        results.sort(key=lambda x: -x[0])
        results = [r[1] for r in results[:limit]]
        
        return _success("search_nodes", {"query": query, "node_type": node_type}, results)
    
    def list_all_types(self) -> dict:
        """List all node types and their counts."""
        self._load()
        counts = {t: len(nodes) for t, nodes in self._nodes_by_type.items()}
        return _success("list_all_types", {}, counts)
    
    # =========================================================================
    # RELATION QUERIES
    # =========================================================================
    
    def get_relations_from(self, node_id: str, relation_type: str = None) -> dict:
        """Get all relations where node_id is the source."""
        self._load()
        rels = self._relations_by_source.get(node_id, [])
        if relation_type:
            rels = [r for r in rels if r.get("type") == relation_type.upper()]
        return _success("get_relations_from", {"node_id": node_id}, rels)
    
    def get_relations_to(self, node_id: str, relation_type: str = None) -> dict:
        """Get all relations where node_id is the target."""
        self._load()
        rels = self._relations_by_target.get(node_id, [])
        if relation_type:
            rels = [r for r in rels if r.get("type") == relation_type.upper()]
        return _success("get_relations_to", {"node_id": node_id}, rels)
    
    def get_referenced_by(self, node_id: str) -> dict:
        """Get all nodes that reference this node."""
        self._load()
        rels = self._relations_by_target.get(node_id, [])
        ref_rels = [r for r in rels if r.get("type") == "REFERENCES"]
        source_ids = [r["source_node"] for r in ref_rels]
        nodes = [self._nodes_by_id[sid] for sid in source_ids if sid in self._nodes_by_id]
        return _success("get_referenced_by", {"node_id": node_id}, nodes)
    
    # =========================================================================
    # TABLE QUERIES
    # =========================================================================
    
    def get_table(self, table_id: str) -> dict:
        """Get a table node by ID (e.g., TABLE_1_1)."""
        return self.get_node_by_id(table_id)
    
    def list_tables(self) -> dict:
        """List all tables."""
        return self.get_nodes_by_type("TABLE")
    
    # =========================================================================
    # FIGURE QUERIES
    # =========================================================================
    
    def get_figure(self, figure_id: str) -> dict:
        """Get a figure node by ID (e.g., FIG_1_1)."""
        return self.get_node_by_id(figure_id)
    
    def list_figures(self) -> dict:
        """List all figures."""
        return self.get_nodes_by_type("FIGURE")
    
    # =========================================================================
    # SECTION/CHUNK QUERIES
    # =========================================================================
    
    def get_chunk(self, chunk_id: str) -> dict:
        """Get a spec chunk by ID (e.g., SEC_1_C1)."""
        return self.get_node_by_id(chunk_id)
    
    def list_chunks(self) -> dict:
        """List all spec chunks."""
        return self.get_nodes_by_type("SPEC_CHUNK")
    
    def get_chunks_for_section(self, section_prefix: str) -> dict:
        """Get all chunks belonging to a section (e.g., 'SEC_1' gets SEC_1_C1, SEC_1_C2, etc.)."""
        self._load()
        chunks = [n for n in self._nodes_by_type.get("SPEC_CHUNK", [])
                  if n["id"].startswith(section_prefix + "_C")]
        # Sort by chunk index
        chunks.sort(key=lambda c: int(c["id"].split("_C")[-1]) if "_C" in c["id"] else 0)
        return _success("get_chunks_for_section", {"section_prefix": section_prefix}, chunks)
    
    # =========================================================================
    # STATISTICS
    # =========================================================================
    
    def get_statistics(self) -> dict:
        """Get metadata statistics."""
        self._load()
        stats = self._data.get("extraction_info", {}).get("statistics", {})
        return _success("get_statistics", {}, stats)


# =============================================================================
# CLI INTERFACE
# =============================================================================

def main():
    """CLI entry point."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python metadata_api.py <function> [args...]")
        print("\nAvailable functions:")
        print("  search_nodes <query> [type]")
        print("  get_node_by_id <id>")
        print("  get_nodes_by_type <type>")
        print("  list_all_types")
        print("  get_relations_from <node_id> [type]")
        print("  get_relations_to <node_id> [type]")
        print("  get_statistics")
        return
    
    api = MetadataAPI()
    func = sys.argv[1]
    args = sys.argv[2:]
    
    if func == "search_nodes":
        result = api.search_nodes(args[0], args[1] if len(args) > 1 else None)
    elif func == "get_node_by_id":
        result = api.get_node_by_id(args[0])
    elif func == "get_nodes_by_type":
        result = api.get_nodes_by_type(args[0])
    elif func == "list_all_types":
        result = api.list_all_types()
    elif func == "get_relations_from":
        result = api.get_relations_from(args[0], args[1] if len(args) > 1 else None)
    elif func == "get_relations_to":
        result = api.get_relations_to(args[0], args[1] if len(args) > 1 else None)
    elif func == "get_statistics":
        result = api.get_statistics()
    else:
        print(f"Unknown function: {func}")
        return
    
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
