#!/usr/bin/env python3
"""
SD Host 3.0 RAG API - Metadata Access Layer

Provides strict, specialized functions for querying the metadata graph.
Designed for LLM agent use with predictable inputs and outputs.

Usage:
    from metadata_api import MetadataAPI
    api = MetadataAPI()
    result = api.get_register_by_offset("028h")
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

# =============================================================================
# CONFIGURATION
# =============================================================================

METADATA_PATH = Path(__file__).parent / "metadata.json"
MAX_RESULTS = 1000

# =============================================================================
# RESPONSE BUILDERS
# =============================================================================

def _success(function: str, params: dict, results: Any, count: int = None, truncated: bool = False) -> dict:
    """Build a successful response."""
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
    """Build an error response."""
    return {
        "success": False,
        "function": function,
        "params": params,
        "count": 0,
        "truncated": False,
        "results": [],
        "error": error_msg
    }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _normalize_offset(offset: str) -> str:
    """Normalize offset string to uppercase without prefix/suffix."""
    offset = offset.strip().upper()
    # Remove 0x prefix
    if offset.startswith("0X"):
        offset = offset[2:]
    # Remove h suffix
    if offset.endswith("H"):
        offset = offset[:-1]
    # Pad to 3 digits
    return offset.zfill(3)


def _format_offset(offset: str) -> str:
    """Format offset for display (e.g., '028h')."""
    return f"{_normalize_offset(offset)}h"


# =============================================================================
# MAIN API CLASS
# =============================================================================

class MetadataAPI:
    """
    API for accessing SD Host Controller 3.0 specification metadata.
    
    All methods return a consistent response dict:
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
        """Initialize API with metadata file."""
        self._path = metadata_path or METADATA_PATH
        self._metadata = None
        self._nodes_by_id = {}
        self._nodes_by_type = {}
        self._relations_by_source = {}
        self._relations_by_target = {}
        self._registers_by_offset = {}
        self._fields_by_id = {}
        self._load()
    
    def _load(self):
        """Load and index metadata."""
        with open(self._path, 'r', encoding='utf-8') as f:
            self._metadata = json.load(f)
        
        # Index nodes
        for node in self._metadata.get("nodes", []):
            node_id = node["id"]
            node_type = node["type"]
            
            self._nodes_by_id[node_id] = node
            
            if node_type not in self._nodes_by_type:
                self._nodes_by_type[node_type] = []
            self._nodes_by_type[node_type].append(node)
            
            # Index registers by offset
            if node_type == "REGISTER":
                offset = _normalize_offset(node.get("extras", {}).get("offset_hex", ""))
                if offset:
                    self._registers_by_offset[offset] = node
                
                # Index fields
                for field in node.get("extras", {}).get("fields", []):
                    self._fields_by_id[field["id"]] = {
                        **field,
                        "register_id": node_id,
                        "register_name": node["name"]
                    }
        
        # Index relations
        for rel in self._metadata.get("relations", []):
            src = rel["source_node"]
            tgt = rel["target_node"]
            
            if src not in self._relations_by_source:
                self._relations_by_source[src] = []
            self._relations_by_source[src].append(rel)
            
            if tgt not in self._relations_by_target:
                self._relations_by_target[tgt] = []
            self._relations_by_target[tgt].append(rel)
    
    # =========================================================================
    # CATEGORY 1: REGISTER ACCESS
    # =========================================================================
    
    def get_register_by_offset(self, offset: str) -> dict:
        """
        Get register by hex offset.
        
        Args:
            offset: Hex offset string (e.g., "028h", "0x028", "028")
        
        Returns:
            Single REGISTER node with all fields.
        """
        params = {"offset": offset}
        
        try:
            norm_offset = _normalize_offset(offset)
        except Exception:
            return _error("get_register_by_offset", params, 
                         f"INVALID_PARAM: Cannot parse offset '{offset}'")
        
        if norm_offset not in self._registers_by_offset:
            # Find valid range for helpful error
            offsets = sorted(self._registers_by_offset.keys())
            valid_range = f"{offsets[0]}h-{offsets[-1]}h" if offsets else "none"
            return _error("get_register_by_offset", params,
                         f"NOT_FOUND: No register at offset {norm_offset}h. Valid offsets: {valid_range}")
        
        return _success("get_register_by_offset", params, self._registers_by_offset[norm_offset])
    
    def get_register_by_id(self, register_id: str) -> dict:
        """
        Get register by exact ID.
        
        Args:
            register_id: Register ID (e.g., "REG_028")
        
        Returns:
            Single REGISTER node with all fields.
        """
        params = {"register_id": register_id}
        
        node = self._nodes_by_id.get(register_id)
        
        if not node:
            return _error("get_register_by_id", params,
                         f"NOT_FOUND: No node with ID '{register_id}'")
        
        if node["type"] != "REGISTER":
            return _error("get_register_by_id", params,
                         f"INVALID_TYPE: '{register_id}' is a {node['type']}, not a REGISTER")
        
        return _success("get_register_by_id", params, node)
    
    def get_register_by_name(self, name: str, exact: bool = False) -> dict:
        """
        Get registers matching name pattern.
        
        Args:
            name: Name to search for
            exact: If True, require exact match; if False, substring match
        
        Returns:
            List of matching REGISTER nodes (summary, no fields).
        """
        params = {"name": name, "exact": exact}
        
        registers = self._nodes_by_type.get("REGISTER", [])
        matches = []
        
        name_lower = name.lower()
        for reg in registers:
            reg_name = reg["name"].lower()
            if exact:
                if reg_name == name_lower:
                    matches.append(reg)
            else:
                if name_lower in reg_name:
                    matches.append(reg)
        
        if not matches:
            return _error("get_register_by_name", params,
                         f"NOT_FOUND: No register matching name '{name}'")
        
        # Return summary (no fields)
        summaries = [{
            "id": r["id"],
            "name": r["name"],
            "offset": r.get("extras", {}).get("offset_hex", ""),
            "class_id": r.get("extras", {}).get("class_id", ""),
            "field_count": len(r.get("extras", {}).get("fields", []))
        } for r in matches]
        
        return _success("get_register_by_name", params, summaries)
    
    def list_registers(self, class_id: str = None) -> dict:
        """
        List all registers, optionally filtered by class.
        
        Args:
            class_id: Optional register class ID to filter by
        
        Returns:
            List of register summaries.
        """
        params = {"class_id": class_id}
        
        registers = self._nodes_by_type.get("REGISTER", [])
        
        if class_id:
            # Validate class_id exists
            if class_id not in self._nodes_by_id:
                return _error("list_registers", params,
                             f"NOT_FOUND: Unknown class_id '{class_id}'")
            registers = [r for r in registers 
                        if r.get("extras", {}).get("class_id") == class_id]
        
        # Sort by offset
        registers = sorted(registers, 
                          key=lambda r: _normalize_offset(r.get("extras", {}).get("offset_hex", "ZZZ")))
        
        summaries = [{
            "id": r["id"],
            "name": r["name"],
            "offset": r.get("extras", {}).get("offset_hex", ""),
            "class_id": r.get("extras", {}).get("class_id", ""),
            "field_count": len(r.get("extras", {}).get("fields", []))
        } for r in registers]
        
        return _success("list_registers", params, summaries)
    
    def get_registers_in_range(self, start_offset: str, end_offset: str) -> dict:
        """
        Get registers within an offset range.
        
        Args:
            start_offset: Start of range (inclusive)
            end_offset: End of range (inclusive)
        
        Returns:
            List of REGISTER nodes in range (summary, no fields).
        """
        params = {"start_offset": start_offset, "end_offset": end_offset}
        
        try:
            start = int(_normalize_offset(start_offset), 16)
            end = int(_normalize_offset(end_offset), 16)
        except Exception:
            return _error("get_registers_in_range", params,
                         f"INVALID_PARAM: Cannot parse offset range")
        
        if start > end:
            return _error("get_registers_in_range", params,
                         f"INVALID_PARAM: start_offset must be <= end_offset")
        
        matches = []
        for offset_str, reg in self._registers_by_offset.items():
            offset_int = int(offset_str, 16)
            if start <= offset_int <= end:
                matches.append(reg)
        
        # Sort by offset
        matches = sorted(matches, 
                        key=lambda r: int(_normalize_offset(r.get("extras", {}).get("offset_hex", "0")), 16))
        
        summaries = [{
            "id": r["id"],
            "name": r["name"],
            "offset": r.get("extras", {}).get("offset_hex", ""),
            "class_id": r.get("extras", {}).get("class_id", ""),
            "field_count": len(r.get("extras", {}).get("fields", []))
        } for r in matches]
        
        return _success("get_registers_in_range", params, summaries)
    
    # =========================================================================
    # CATEGORY 2: REGISTER CLASS ACCESS
    # =========================================================================
    
    def get_register_class_by_id(self, class_id: str) -> dict:
        """
        Get register class by exact ID.
        
        Args:
            class_id: Class ID (e.g., "REGCLASS_INTERRUPT")
        
        Returns:
            REG_CLASS node with member register IDs.
        """
        params = {"class_id": class_id}
        
        node = self._nodes_by_id.get(class_id)
        
        if not node:
            return _error("get_register_class_by_id", params,
                         f"NOT_FOUND: No node with ID '{class_id}'")
        
        if node["type"] != "REG_CLASS":
            return _error("get_register_class_by_id", params,
                         f"INVALID_TYPE: '{class_id}' is a {node['type']}, not a REG_CLASS")
        
        # Find member registers
        member_ids = [r["id"] for r in self._nodes_by_type.get("REGISTER", [])
                     if r.get("extras", {}).get("class_id") == class_id]
        
        result = {**node, "member_register_ids": member_ids}
        return _success("get_register_class_by_id", params, result)
    
    def list_register_classes(self) -> dict:
        """
        List all register classes.
        
        Returns:
            List of register class summaries.
        """
        params = {}
        
        classes = self._nodes_by_type.get("REG_CLASS", [])
        
        summaries = []
        for cls in classes:
            addr_range = cls.get("extras", {}).get("address_range", {})
            member_count = len([r for r in self._nodes_by_type.get("REGISTER", [])
                               if r.get("extras", {}).get("class_id") == cls["id"]])
            summaries.append({
                "id": cls["id"],
                "name": cls["name"],
                "start_offset": addr_range.get("start", ""),
                "end_offset": addr_range.get("end", ""),
                "register_count": member_count
            })
        
        return _success("list_register_classes", params, summaries)
    
    # =========================================================================
    # CATEGORY 3: FIELD ACCESS
    # =========================================================================
    
    def get_field_by_id(self, field_id: str) -> dict:
        """
        Get field by exact ID.
        
        Args:
            field_id: Field ID (e.g., "REG_028_F3")
        
        Returns:
            Full field object with raw, abstract, values.
        """
        params = {"field_id": field_id}
        
        if field_id not in self._fields_by_id:
            return _error("get_field_by_id", params,
                         f"NOT_FOUND: No field with ID '{field_id}'")
        
        return _success("get_field_by_id", params, self._fields_by_id[field_id])
    
    def get_field_by_name(self, register_id: str, field_name: str) -> dict:
        """
        Get field by name within a register.
        
        Args:
            register_id: Register ID (e.g., "REG_028")
            field_name: Field name to search for (case-insensitive substring match)
        
        Returns:
            Full field object (first match).
        """
        params = {"register_id": register_id, "field_name": field_name}
        
        reg = self._nodes_by_id.get(register_id)
        if not reg:
            return _error("get_field_by_name", params,
                         f"NOT_FOUND: No register with ID '{register_id}'")
        
        if reg["type"] != "REGISTER":
            return _error("get_field_by_name", params,
                         f"INVALID_TYPE: '{register_id}' is a {reg['type']}, not a REGISTER")
        
        fields = reg.get("extras", {}).get("fields", [])
        field_name_lower = field_name.lower()
        
        matches = [f for f in fields if field_name_lower in f["name"].lower()]
        
        if not matches:
            field_names = [f["name"] for f in fields]
            return _error("get_field_by_name", params,
                         f"NOT_FOUND: No field matching '{field_name}' in {register_id}. "
                         f"Available: {', '.join(field_names[:5])}...")
        
        # Return first match with register context
        result = {
            **matches[0],
            "register_id": register_id,
            "register_name": reg["name"]
        }
        return _success("get_field_by_name", params, result)
    
    def get_field_by_bit(self, register_id: str, bit: int) -> dict:
        """
        Get field containing a specific bit position.
        
        Args:
            register_id: Register ID (e.g., "REG_028")
            bit: Bit position (0-based)
        
        Returns:
            Full field object.
        """
        params = {"register_id": register_id, "bit": bit}
        
        reg = self._nodes_by_id.get(register_id)
        if not reg:
            return _error("get_field_by_bit", params,
                         f"NOT_FOUND: No register with ID '{register_id}'")
        
        if reg["type"] != "REGISTER":
            return _error("get_field_by_bit", params,
                         f"INVALID_TYPE: '{register_id}' is a {reg['type']}, not a REGISTER")
        
        fields = reg.get("extras", {}).get("fields", [])
        
        for f in fields:
            bit_low = f.get("bit_low", 0)
            bit_high = f.get("bit_high", 0)
            if bit_low <= bit <= bit_high:
                result = {
                    **f,
                    "register_id": register_id,
                    "register_name": reg["name"]
                }
                return _success("get_field_by_bit", params, result)
        
        return _error("get_field_by_bit", params,
                     f"NOT_FOUND: No field contains bit {bit} in {register_id}")
    
    def list_fields_in_register(self, register_id: str) -> dict:
        """
        List all fields in a register.
        
        Args:
            register_id: Register ID (e.g., "REG_028")
        
        Returns:
            List of field summaries.
        """
        params = {"register_id": register_id}
        
        reg = self._nodes_by_id.get(register_id)
        if not reg:
            return _error("list_fields_in_register", params,
                         f"NOT_FOUND: No register with ID '{register_id}'")
        
        if reg["type"] != "REGISTER":
            return _error("list_fields_in_register", params,
                         f"INVALID_TYPE: '{register_id}' is a {reg['type']}, not a REGISTER")
        
        fields = reg.get("extras", {}).get("fields", [])
        
        summaries = [{
            "id": f["id"],
            "name": f["name"],
            "bits": f.get("bits", ""),
            "width": f.get("width", 0),
            "access": f.get("access", "")
        } for f in fields]
        
        return _success("list_fields_in_register", params, summaries)
    
    def search_fields_by_access(self, access: str, register_id: str = None) -> dict:
        """
        Find fields by access type.
        
        Args:
            access: Access type ("read-only", "read-write", "write-only", "reserved")
            register_id: Optional register ID to limit search
        
        Returns:
            List of field summaries with register context.
        """
        params = {"access": access, "register_id": register_id}
        
        valid_access = ["read-only", "read-write", "write-only", "reserved"]
        if access not in valid_access:
            return _error("search_fields_by_access", params,
                         f"INVALID_PARAM: access must be one of {valid_access}")
        
        results = []
        registers = self._nodes_by_type.get("REGISTER", [])
        
        if register_id:
            reg = self._nodes_by_id.get(register_id)
            if not reg or reg["type"] != "REGISTER":
                return _error("search_fields_by_access", params,
                             f"NOT_FOUND: No register with ID '{register_id}'")
            registers = [reg]
        
        for reg in registers:
            for f in reg.get("extras", {}).get("fields", []):
                if f.get("access") == access:
                    results.append({
                        "id": f["id"],
                        "name": f["name"],
                        "bits": f.get("bits", ""),
                        "width": f.get("width", 0),
                        "access": f.get("access", ""),
                        "register_id": reg["id"],
                        "register_name": reg["name"]
                    })
        
        truncated = len(results) > MAX_RESULTS
        if truncated:
            results = results[:MAX_RESULTS]
        
        return _success("search_fields_by_access", params, results, truncated=truncated)
    
    def search_fields_by_name(self, pattern: str) -> dict:
        """
        Search fields by name pattern across all registers.
        
        Args:
            pattern: Name pattern to search for (case-insensitive substring)
        
        Returns:
            List of field summaries with register context.
        """
        params = {"pattern": pattern}
        
        pattern_lower = pattern.lower()
        results = []
        
        for reg in self._nodes_by_type.get("REGISTER", []):
            for f in reg.get("extras", {}).get("fields", []):
                if pattern_lower in f["name"].lower():
                    results.append({
                        "id": f["id"],
                        "name": f["name"],
                        "bits": f.get("bits", ""),
                        "width": f.get("width", 0),
                        "access": f.get("access", ""),
                        "register_id": reg["id"],
                        "register_name": reg["name"]
                    })
        
        if not results:
            return _error("search_fields_by_name", params,
                         f"NOT_FOUND: No fields matching '{pattern}'")
        
        truncated = len(results) > MAX_RESULTS
        if truncated:
            results = results[:MAX_RESULTS]
        
        return _success("search_fields_by_name", params, results, truncated=truncated)
    
    # =========================================================================
    # CATEGORY 4: SPEC CONTENT ACCESS
    # =========================================================================
    
    def get_page_content(self, spec_page: int) -> dict:
        """
        Get full content of a specification page.
        
        Args:
            spec_page: The page number (1-based)
        
        Returns:
            Page content with text, chunks, tables, figures, and registers on page.
        """
        params = {"spec_page": spec_page}
        
        total_pages = self._metadata.get("spec_info", {}).get("total_pages", 0)
        if spec_page < 1 or spec_page > total_pages:
            return _error("get_page_content", params,
                         f"INVALID_PARAM: spec_page must be 1-{total_pages}")
        
        # Find chunks on this page
        chunks = []
        content_parts = []
        for node in self._nodes_by_type.get("SPEC_CHUNK", []):
            if node.get("source", {}).get("page") == spec_page:
                chunks.append(node["id"])
                full_text = node.get("extras", {}).get("full_text", "")
                if full_text:
                    content_parts.append(full_text)
        
        # Find tables on this page
        tables_on_page = []
        for node in self._nodes_by_type.get("TABLE", []):
            if node.get("source", {}).get("page") == spec_page:
                tables_on_page.append(node["id"])
        
        # Find figures on this page
        figures_on_page = []
        for node in self._nodes_by_type.get("FIGURE", []):
            if node.get("source", {}).get("page") == spec_page:
                figures_on_page.append(node["id"])
        
        # Find registers on this page
        registers_on_page = []
        for node in self._nodes_by_type.get("REGISTER", []):
            if node.get("source", {}).get("page") == spec_page:
                registers_on_page.append(node["id"])
        
        # Calculate PDF page (offset of 11)
        pdf_page = spec_page + 11
        
        result = {
            "spec_page": spec_page,
            "pdf_page": pdf_page,
            "content": "\n\n".join(content_parts),
            "chunks": chunks,
            "tables_on_page": tables_on_page,
            "figures_on_page": figures_on_page,
            "registers_on_page": registers_on_page
        }
        
        return _success("get_page_content", params, result)
    
    def get_section_by_number(self, section_number: str) -> dict:
        """
        Get section content by section number.
        
        Args:
            section_number: The section number (e.g., "2.2.10")
        
        Returns:
            Section with all chunks, title, and summary.
        """
        params = {"section_number": section_number}
        
        # Find all chunks for this section
        section_chunks = []
        section_title = None
        
        for node in self._nodes_by_type.get("SPEC_CHUNK", []):
            extras = node.get("extras", {})
            if extras.get("section_number") == section_number:
                section_chunks.append(node)
                if not section_title:
                    section_title = extras.get("section_title", "")
        
        if not section_chunks:
            return _error("get_section_by_number", params,
                         f"NOT_FOUND: No section with number '{section_number}'")
        
        # Sort by chunk index
        section_chunks.sort(key=lambda c: c.get("extras", {}).get("chunk_index", 0))
        
        # Combine content
        full_content = []
        chunk_ids = []
        for chunk in section_chunks:
            chunk_ids.append(chunk["id"])
            full_text = chunk.get("extras", {}).get("full_text", "")
            if full_text:
                full_content.append(full_text)
        
        # Get page range
        pages = [c.get("source", {}).get("page", 0) for c in section_chunks]
        start_page = min(pages) if pages else 0
        end_page = max(pages) if pages else 0
        
        result = {
            "section_number": section_number,
            "title": section_title,
            "chunk_count": len(section_chunks),
            "chunk_ids": chunk_ids,
            "start_page": start_page,
            "end_page": end_page,
            "content": "\n\n".join(full_content)
        }
        
        return _success("get_section_by_number", params, result)
    
    def get_chunk_by_id(self, chunk_id: str) -> dict:
        """
        Get specific chunk by ID.
        
        Args:
            chunk_id: The chunk ID (e.g., "SEC_2_2_10_C0")
        
        Returns:
            Full SPEC_CHUNK node with raw text.
        """
        params = {"chunk_id": chunk_id}
        
        node = self._nodes_by_id.get(chunk_id)
        
        if not node:
            return _error("get_chunk_by_id", params,
                         f"NOT_FOUND: No node with ID '{chunk_id}'")
        
        if node["type"] != "SPEC_CHUNK":
            return _error("get_chunk_by_id", params,
                         f"INVALID_TYPE: '{chunk_id}' is a {node['type']}, not a SPEC_CHUNK")
        
        return _success("get_chunk_by_id", params, node)
    
    def list_sections(self, parent: str = None) -> dict:
        """
        List sections, optionally under a parent.
        
        Args:
            parent: Optional parent section number (e.g., "2.2" for all 2.2.x)
        
        Returns:
            List of section summaries.
        """
        params = {"parent": parent}
        
        # Collect unique sections from chunks
        sections = {}
        for node in self._nodes_by_type.get("SPEC_CHUNK", []):
            extras = node.get("extras", {})
            section_num = extras.get("section_number", "")
            if not section_num:
                continue
            
            # Filter by parent if specified
            if parent:
                if not section_num.startswith(parent + ".") and section_num != parent:
                    continue
            
            if section_num not in sections:
                pages = []
                sections[section_num] = {
                    "section_number": section_num,
                    "title": extras.get("section_title", ""),
                    "chunk_count": 0,
                    "pages": pages
                }
            
            sections[section_num]["chunk_count"] += 1
            page = node.get("source", {}).get("page", 0)
            if page and page not in sections[section_num]["pages"]:
                sections[section_num]["pages"].append(page)
        
        # Convert to list and sort
        result = []
        for sec in sorted(sections.values(), 
                         key=lambda s: [int(x) if x.isdigit() else 0 for x in s["section_number"].split(".")]):
            sec["start_page"] = min(sec["pages"]) if sec["pages"] else 0
            del sec["pages"]
            result.append(sec)
        
        return _success("list_sections", params, result)
    
    # =========================================================================
    # CATEGORY 5: TABLE ACCESS
    # =========================================================================
    
    def get_table_by_id(self, table_id: str) -> dict:
        """
        Get table by exact ID.
        
        Args:
            table_id: Table ID (e.g., "TABLE_2_16")
        
        Returns:
            TABLE node with CSV path.
        """
        params = {"table_id": table_id}
        
        node = self._nodes_by_id.get(table_id)
        
        if not node:
            return _error("get_table_by_id", params,
                         f"NOT_FOUND: No node with ID '{table_id}'")
        
        if node["type"] != "TABLE":
            return _error("get_table_by_id", params,
                         f"INVALID_TYPE: '{table_id}' is a {node['type']}, not a TABLE")
        
        return _success("get_table_by_id", params, node)
    
    def get_table_by_reference(self, spec_ref: str) -> dict:
        """
        Get table by spec reference string.
        
        Args:
            spec_ref: Spec reference (e.g., "Table 2-16")
        
        Returns:
            TABLE node.
        """
        params = {"spec_ref": spec_ref}
        
        for node in self._nodes_by_type.get("TABLE", []):
            if node.get("source", {}).get("spec_reference", "") == spec_ref:
                return _success("get_table_by_reference", params, node)
        
        # Try case-insensitive match
        spec_ref_lower = spec_ref.lower()
        for node in self._nodes_by_type.get("TABLE", []):
            if node.get("source", {}).get("spec_reference", "").lower() == spec_ref_lower:
                return _success("get_table_by_reference", params, node)
        
        return _error("get_table_by_reference", params,
                     f"NOT_FOUND: No table with reference '{spec_ref}'")
    
    def list_tables(self, table_type: str = None) -> dict:
        """
        List tables, optionally filtered by type.
        
        Args:
            table_type: Optional filter (REGISTER_FIELDS, REGISTER_MAP, SIGNAL_LIST, TIMING, OTHER)
        
        Returns:
            List of table summaries.
        """
        params = {"table_type": table_type}
        
        valid_types = ["REGISTER_FIELDS", "REGISTER_MAP", "SIGNAL_LIST", "TIMING", "OTHER"]
        if table_type and table_type not in valid_types:
            return _error("list_tables", params,
                         f"INVALID_PARAM: table_type must be one of {valid_types}")
        
        tables = self._nodes_by_type.get("TABLE", [])
        
        if table_type:
            tables = [t for t in tables if t.get("extras", {}).get("table_type") == table_type]
        
        # Sort by ID
        tables = sorted(tables, key=lambda t: t["id"])
        
        summaries = [{
            "id": t["id"],
            "name": t["name"],
            "spec_reference": t.get("source", {}).get("spec_reference", ""),
            "page": t.get("source", {}).get("page", 0),
            "table_type": t.get("extras", {}).get("table_type", "")
        } for t in tables]
        
        return _success("list_tables", params, summaries)
    
    def get_table_csv(self, table_id: str) -> dict:
        """
        Get parsed CSV content for a table.
        
        Args:
            table_id: Table ID (e.g., "TABLE_2_16")
        
        Returns:
            2D array (rows × columns).
        """
        import csv
        
        params = {"table_id": table_id}
        
        node = self._nodes_by_id.get(table_id)
        
        if not node:
            return _error("get_table_csv", params,
                         f"NOT_FOUND: No node with ID '{table_id}'")
        
        if node["type"] != "TABLE":
            return _error("get_table_csv", params,
                         f"INVALID_TYPE: '{table_id}' is a {node['type']}, not a TABLE")
        
        csv_path_rel = node.get("extras", {}).get("csv_file", "")
        if not csv_path_rel:
            return _error("get_table_csv", params,
                         f"NO_CSV: Table '{table_id}' has no CSV file")
        
        # Resolve path relative to workspace root
        csv_path = self._path.parent.parent / csv_path_rel
        
        if not csv_path.exists():
            return _error("get_table_csv", params,
                         f"FILE_NOT_FOUND: CSV file not found at '{csv_path_rel}'")
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                rows = list(reader)
            return _success("get_table_csv", params, rows)
        except Exception as e:
            return _error("get_table_csv", params,
                         f"READ_ERROR: Failed to read CSV - {str(e)}")
    
    # =========================================================================
    # CATEGORY 6: FIGURE ACCESS
    # =========================================================================
    
    def get_figure_by_id(self, figure_id: str) -> dict:
        """
        Get figure by exact ID.
        
        Args:
            figure_id: Figure ID (e.g., "FIG_2_1")
        
        Returns:
            FIGURE node with PlantUML path.
        """
        params = {"figure_id": figure_id}
        
        node = self._nodes_by_id.get(figure_id)
        
        if not node:
            return _error("get_figure_by_id", params,
                         f"NOT_FOUND: No node with ID '{figure_id}'")
        
        if node["type"] != "FIGURE":
            return _error("get_figure_by_id", params,
                         f"INVALID_TYPE: '{figure_id}' is a {node['type']}, not a FIGURE")
        
        return _success("get_figure_by_id", params, node)
    
    def get_figure_by_reference(self, spec_ref: str) -> dict:
        """
        Get figure by spec reference string.
        
        Args:
            spec_ref: Spec reference (e.g., "Figure 2-1")
        
        Returns:
            FIGURE node.
        """
        params = {"spec_ref": spec_ref}
        
        for node in self._nodes_by_type.get("FIGURE", []):
            if node.get("source", {}).get("spec_reference", "") == spec_ref:
                return _success("get_figure_by_reference", params, node)
        
        # Try case-insensitive match
        spec_ref_lower = spec_ref.lower()
        for node in self._nodes_by_type.get("FIGURE", []):
            if node.get("source", {}).get("spec_reference", "").lower() == spec_ref_lower:
                return _success("get_figure_by_reference", params, node)
        
        return _error("get_figure_by_reference", params,
                     f"NOT_FOUND: No figure with reference '{spec_ref}'")
    
    def list_figures(self, figure_type: str = None) -> dict:
        """
        List figures, optionally filtered by type.
        
        Args:
            figure_type: Optional filter (STATE_DIAGRAM, TIMING_DIAGRAM, BLOCK_DIAGRAM, REGISTER_LAYOUT, FLOWCHART, OTHER)
        
        Returns:
            List of figure summaries.
        """
        params = {"figure_type": figure_type}
        
        valid_types = ["STATE_DIAGRAM", "TIMING_DIAGRAM", "BLOCK_DIAGRAM", "REGISTER_LAYOUT", "FLOWCHART", "OTHER"]
        if figure_type and figure_type not in valid_types:
            return _error("list_figures", params,
                         f"INVALID_PARAM: figure_type must be one of {valid_types}")
        
        figures = self._nodes_by_type.get("FIGURE", [])
        
        if figure_type:
            figures = [f for f in figures if f.get("extras", {}).get("figure_type") == figure_type]
        
        # Sort by ID
        figures = sorted(figures, key=lambda f: f["id"])
        
        summaries = [{
            "id": f["id"],
            "name": f["name"],
            "spec_reference": f.get("source", {}).get("spec_reference", ""),
            "page": f.get("source", {}).get("page", 0),
            "figure_type": f.get("extras", {}).get("figure_type", "")
        } for f in figures]
        
        return _success("list_figures", params, summaries)
    
    def get_figure_plantuml(self, figure_id: str) -> dict:
        """
        Get PlantUML source code for a figure.
        
        Args:
            figure_id: Figure ID (e.g., "FIG_2_1")
        
        Returns:
            Raw PlantUML text string.
        """
        params = {"figure_id": figure_id}
        
        node = self._nodes_by_id.get(figure_id)
        
        if not node:
            return _error("get_figure_plantuml", params,
                         f"NOT_FOUND: No node with ID '{figure_id}'")
        
        if node["type"] != "FIGURE":
            return _error("get_figure_plantuml", params,
                         f"INVALID_TYPE: '{figure_id}' is a {node['type']}, not a FIGURE")
        
        puml_path_rel = node.get("extras", {}).get("text_diagram_file", "")
        if not puml_path_rel:
            return _error("get_figure_plantuml", params,
                         f"NO_PLANTUML: Figure '{figure_id}' has no PlantUML file")
        
        # Resolve path relative to workspace root
        puml_path = self._path.parent.parent / puml_path_rel
        
        if not puml_path.exists():
            return _error("get_figure_plantuml", params,
                         f"FILE_NOT_FOUND: PlantUML file not found at '{puml_path_rel}'")
        
        try:
            with open(puml_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return _success("get_figure_plantuml", params, content)
        except Exception as e:
            return _error("get_figure_plantuml", params,
                         f"READ_ERROR: Failed to read PlantUML - {str(e)}")

    # =========================================================================
    # CATEGORY 7: SEARCH FUNCTIONS
    # =========================================================================
    
    def search_by_keywords(self, keywords: list, node_types: list = None) -> dict:
        """
        Search nodes by index keywords.
        
        Args:
            keywords: List of keywords to search for (case-insensitive)
            node_types: Optional list of node types to filter (REGISTER, SPEC_CHUNK, TABLE, FIGURE, REG_CLASS)
        
        Returns:
            List of matching nodes with scores.
        """
        params = {"keywords": keywords, "node_types": node_types}
        
        if not keywords:
            return _error("search_by_keywords", params,
                         "INVALID_PARAM: keywords list cannot be empty")
        
        valid_types = ["REGISTER", "SPEC_CHUNK", "TABLE", "FIGURE", "REG_CLASS"]
        if node_types:
            invalid = [t for t in node_types if t not in valid_types]
            if invalid:
                return _error("search_by_keywords", params,
                             f"INVALID_PARAM: Invalid node_types: {invalid}. Valid: {valid_types}")
        
        keywords_lower = [k.lower() for k in keywords]
        results = []
        
        # Search all nodes
        for node in self._metadata.get("nodes", []):
            if node_types and node["type"] not in node_types:
                continue
            
            node_keywords = [k.lower() for k in node.get("index_keywords", [])]
            matched = [k for k in keywords_lower if k in node_keywords]
            
            if matched:
                score = len(matched) / len(keywords_lower)
                results.append({
                    "node_id": node["id"],
                    "node_type": node["type"],
                    "name": node["name"],
                    "score": round(score, 2),
                    "matched_keywords": matched
                })
        
        # Sort by score descending
        results.sort(key=lambda r: (-r["score"], r["node_id"]))
        
        if not results:
            return _error("search_by_keywords", params,
                         f"NOT_FOUND: No nodes match keywords {keywords}")
        
        truncated = len(results) > MAX_RESULTS
        if truncated:
            results = results[:MAX_RESULTS]
        
        return _success("search_by_keywords", params, results, truncated=truncated)
    
    def search_chunks_by_text(self, query: str) -> dict:
        """
        Full-text search in chunk content.
        
        Args:
            query: Text to search for (case-insensitive)
        
        Returns:
            List of matching chunks with excerpts.
        """
        params = {"query": query}
        
        if not query or len(query) < 2:
            return _error("search_chunks_by_text", params,
                         "INVALID_PARAM: query must be at least 2 characters")
        
        query_lower = query.lower()
        results = []
        
        for node in self._nodes_by_type.get("SPEC_CHUNK", []):
            full_text = node.get("extras", {}).get("full_text", "")
            if not full_text:
                continue
            
            text_lower = full_text.lower()
            pos = text_lower.find(query_lower)
            
            if pos != -1:
                # Extract excerpt around match
                start = max(0, pos - 50)
                end = min(len(full_text), pos + len(query) + 50)
                excerpt = full_text[start:end]
                if start > 0:
                    excerpt = "..." + excerpt
                if end < len(full_text):
                    excerpt = excerpt + "..."
                
                results.append({
                    "chunk_id": node["id"],
                    "section_number": node.get("extras", {}).get("section_number", ""),
                    "section_title": node.get("extras", {}).get("section_title", ""),
                    "page": node.get("source", {}).get("page", 0),
                    "excerpt": excerpt,
                    "match_position": pos
                })
        
        if not results:
            return _error("search_chunks_by_text", params,
                         f"NOT_FOUND: No chunks contain text '{query}'")
        
        truncated = len(results) > MAX_RESULTS
        if truncated:
            results = results[:MAX_RESULTS]
        
        return _success("search_chunks_by_text", params, results, truncated=truncated)
    
    def search_fields_by_text(self, query: str) -> dict:
        """
        Full-text search in field raw descriptions.
        
        Args:
            query: Text to search for (case-insensitive)
        
        Returns:
            List of matching fields with excerpts.
        """
        params = {"query": query}
        
        if not query or len(query) < 2:
            return _error("search_fields_by_text", params,
                         "INVALID_PARAM: query must be at least 2 characters")
        
        query_lower = query.lower()
        results = []
        
        for reg in self._nodes_by_type.get("REGISTER", []):
            for field in reg.get("extras", {}).get("fields", []):
                raw = field.get("raw", "")
                abstract = field.get("abstract", "")
                combined = f"{raw} {abstract}"
                
                if not combined:
                    continue
                
                combined_lower = combined.lower()
                pos = combined_lower.find(query_lower)
                
                if pos != -1:
                    # Extract excerpt
                    start = max(0, pos - 30)
                    end = min(len(combined), pos + len(query) + 30)
                    excerpt = combined[start:end]
                    if start > 0:
                        excerpt = "..." + excerpt
                    if end < len(combined):
                        excerpt = excerpt + "..."
                    
                    results.append({
                        "field_id": field["id"],
                        "field_name": field["name"],
                        "register_id": reg["id"],
                        "register_name": reg["name"],
                        "excerpt": excerpt
                    })
        
        if not results:
            return _error("search_fields_by_text", params,
                         f"NOT_FOUND: No fields contain text '{query}'")
        
        truncated = len(results) > MAX_RESULTS
        if truncated:
            results = results[:MAX_RESULTS]
        
        return _success("search_fields_by_text", params, results, truncated=truncated)

    # =========================================================================
    # CATEGORY 8: RELATIONSHIP QUERIES
    # =========================================================================
    
    def get_tables_for_register(self, register_id: str) -> dict:
        """
        Get table IDs that define a register.
        
        Args:
            register_id: Register ID (e.g., "REG_028")
        
        Returns:
            List of table IDs.
        """
        params = {"register_id": register_id}
        
        if register_id not in self._nodes_by_id:
            return _error("get_tables_for_register", params,
                         f"NOT_FOUND: No node with ID '{register_id}'")
        
        if self._nodes_by_id[register_id]["type"] != "REGISTER":
            return _error("get_tables_for_register", params,
                         f"INVALID_TYPE: '{register_id}' is not a REGISTER")
        
        # Find relations where register is target and source is table
        table_ids = []
        for rel in self._relations_by_target.get(register_id, []):
            source_id = rel["source_node"]
            source_node = self._nodes_by_id.get(source_id)
            if source_node and source_node["type"] == "TABLE":
                table_ids.append(source_id)
        
        return _success("get_tables_for_register", params, table_ids)
    
    def get_figures_for_register(self, register_id: str) -> dict:
        """
        Get figure IDs that visualize a register.
        
        Args:
            register_id: Register ID (e.g., "REG_028")
        
        Returns:
            List of figure IDs.
        """
        params = {"register_id": register_id}
        
        if register_id not in self._nodes_by_id:
            return _error("get_figures_for_register", params,
                         f"NOT_FOUND: No node with ID '{register_id}'")
        
        if self._nodes_by_id[register_id]["type"] != "REGISTER":
            return _error("get_figures_for_register", params,
                         f"INVALID_TYPE: '{register_id}' is not a REGISTER")
        
        # Find relations where register is target and source is figure
        figure_ids = []
        for rel in self._relations_by_target.get(register_id, []):
            source_id = rel["source_node"]
            source_node = self._nodes_by_id.get(source_id)
            if source_node and source_node["type"] == "FIGURE":
                figure_ids.append(source_id)
        
        return _success("get_figures_for_register", params, figure_ids)
    
    def get_chunks_for_register(self, register_id: str) -> dict:
        """
        Get chunk IDs that describe a register.
        
        Args:
            register_id: Register ID (e.g., "REG_028")
        
        Returns:
            List of chunk IDs.
        """
        params = {"register_id": register_id}
        
        if register_id not in self._nodes_by_id:
            return _error("get_chunks_for_register", params,
                         f"NOT_FOUND: No node with ID '{register_id}'")
        
        if self._nodes_by_id[register_id]["type"] != "REGISTER":
            return _error("get_chunks_for_register", params,
                         f"INVALID_TYPE: '{register_id}' is not a REGISTER")
        
        # Find relations where register is target and source is chunk
        chunk_ids = []
        for rel in self._relations_by_target.get(register_id, []):
            source_id = rel["source_node"]
            source_node = self._nodes_by_id.get(source_id)
            if source_node and source_node["type"] == "SPEC_CHUNK":
                chunk_ids.append(source_id)
        
        return _success("get_chunks_for_register", params, chunk_ids)
    
    def get_registers_for_table(self, table_id: str) -> dict:
        """
        Get register IDs defined by a table.
        
        Args:
            table_id: Table ID (e.g., "TABLE_2_16")
        
        Returns:
            List of register IDs.
        """
        params = {"table_id": table_id}
        
        if table_id not in self._nodes_by_id:
            return _error("get_registers_for_table", params,
                         f"NOT_FOUND: No node with ID '{table_id}'")
        
        if self._nodes_by_id[table_id]["type"] != "TABLE":
            return _error("get_registers_for_table", params,
                         f"INVALID_TYPE: '{table_id}' is not a TABLE")
        
        # Find relations where table is source and target is register
        register_ids = []
        for rel in self._relations_by_source.get(table_id, []):
            target_id = rel["target_node"]
            target_node = self._nodes_by_id.get(target_id)
            if target_node and target_node["type"] == "REGISTER":
                register_ids.append(target_id)
        
        return _success("get_registers_for_table", params, register_ids)
    
    def get_chunks_referencing(self, node_id: str) -> dict:
        """
        Get chunks that reference a table or figure.
        
        Args:
            node_id: Table or Figure ID (e.g., "TABLE_2_16", "FIG_2_1")
        
        Returns:
            List of chunk IDs.
        """
        params = {"node_id": node_id}
        
        if node_id not in self._nodes_by_id:
            return _error("get_chunks_referencing", params,
                         f"NOT_FOUND: No node with ID '{node_id}'")
        
        node_type = self._nodes_by_id[node_id]["type"]
        if node_type not in ["TABLE", "FIGURE"]:
            return _error("get_chunks_referencing", params,
                         f"INVALID_TYPE: '{node_id}' is a {node_type}, expected TABLE or FIGURE")
        
        # Find relations where this node is target and source is chunk
        chunk_ids = []
        for rel in self._relations_by_target.get(node_id, []):
            source_id = rel["source_node"]
            source_node = self._nodes_by_id.get(source_id)
            if source_node and source_node["type"] == "SPEC_CHUNK":
                chunk_ids.append(source_id)
        
        return _success("get_chunks_referencing", params, chunk_ids)

    # =========================================================================
    # CATEGORY 9: METADATA & NAVIGATION
    # =========================================================================
    
    def get_spec_info(self) -> dict:
        """
        Get specification metadata.
        
        Returns:
            Spec version, page count, extraction info, node counts.
        """
        params = {}
        
        spec_info = self._metadata.get("spec_info", {})
        extraction_info = self._metadata.get("extraction_info", {})
        stats = extraction_info.get("statistics", {})
        
        result = {
            "name": spec_info.get("name", ""),
            "version": spec_info.get("version", ""),
            "date": spec_info.get("date", ""),
            "total_pages": spec_info.get("total_pages", 0),
            "metadata_version": self._metadata.get("metadata_version", ""),
            "extracted_date": extraction_info.get("extracted_date", ""),
            "node_counts": stats.get("by_type", {}),
            "total_nodes": stats.get("total_nodes", 0),
            "total_relations": stats.get("total_relations", 0),
            "total_fields": stats.get("register_fields", 0)
        }
        
        return _success("get_spec_info", params, result)
    
    def get_register_map(self) -> dict:
        """
        Get full register address map (sorted by offset).
        
        Returns:
            List of {offset, id, name, size_bits, class_id}.
        """
        params = {}
        
        registers = self._nodes_by_type.get("REGISTER", [])
        
        # Sort by offset
        registers = sorted(registers, 
                          key=lambda r: int(_normalize_offset(
                              r.get("extras", {}).get("offset_hex", "0")), 16))
        
        result = [{
            "offset": r.get("extras", {}).get("offset_hex", ""),
            "id": r["id"],
            "name": r["name"],
            "size_bits": r.get("extras", {}).get("size_bits", 0),
            "class_id": r.get("extras", {}).get("class_id", "")
        } for r in registers]
        
        return _success("get_register_map", params, result)


# =============================================================================
# CLI INTERFACE (for testing)
# =============================================================================

def main():
    """CLI interface for testing the API."""
    import argparse
    
    parser = argparse.ArgumentParser(description="SD Host 3.0 Metadata API")
    parser.add_argument("function", help="Function to call")
    parser.add_argument("args", nargs="*", help="Function arguments")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()
    
    api = MetadataAPI()
    
    # Map function names to methods
    func_map = {
        # Category 1: Register Access
        "get_register_by_offset": lambda a: api.get_register_by_offset(a[0]),
        "get_register_by_id": lambda a: api.get_register_by_id(a[0]),
        "get_register_by_name": lambda a: api.get_register_by_name(a[0], exact=len(a) > 1 and a[1] == "exact"),
        "list_registers": lambda a: api.list_registers(class_id=a[0] if a else None),
        "get_registers_in_range": lambda a: api.get_registers_in_range(a[0], a[1]),
        # Category 2: Register Class Access
        "get_register_class_by_id": lambda a: api.get_register_class_by_id(a[0]),
        "list_register_classes": lambda a: api.list_register_classes(),
        # Category 3: Field Access
        "get_field_by_id": lambda a: api.get_field_by_id(a[0]),
        "get_field_by_name": lambda a: api.get_field_by_name(a[0], a[1]),
        "get_field_by_bit": lambda a: api.get_field_by_bit(a[0], int(a[1])),
        "list_fields_in_register": lambda a: api.list_fields_in_register(a[0]),
        "search_fields_by_access": lambda a: api.search_fields_by_access(a[0], register_id=a[1] if len(a) > 1 else None),
        "search_fields_by_name": lambda a: api.search_fields_by_name(a[0]),
        # Category 4: Spec Content Access
        "get_page_content": lambda a: api.get_page_content(int(a[0])),
        "get_section_by_number": lambda a: api.get_section_by_number(a[0]),
        "get_chunk_by_id": lambda a: api.get_chunk_by_id(a[0]),
        "list_sections": lambda a: api.list_sections(parent=a[0] if a else None),
        # Category 5: Table Access
        "get_table_by_id": lambda a: api.get_table_by_id(a[0]),
        "get_table_by_reference": lambda a: api.get_table_by_reference(a[0]),
        "list_tables": lambda a: api.list_tables(table_type=a[0] if a else None),
        "get_table_csv": lambda a: api.get_table_csv(a[0]),
        # Category 6: Figure Access
        "get_figure_by_id": lambda a: api.get_figure_by_id(a[0]),
        "get_figure_by_reference": lambda a: api.get_figure_by_reference(a[0]),
        "list_figures": lambda a: api.list_figures(figure_type=a[0] if a else None),
        "get_figure_plantuml": lambda a: api.get_figure_plantuml(a[0]),
        # Category 7: Search Functions
        "search_by_keywords": lambda a: api.search_by_keywords(a[0].split(","), node_types=a[1].split(",") if len(a) > 1 else None),
        "search_chunks_by_text": lambda a: api.search_chunks_by_text(a[0]),
        "search_fields_by_text": lambda a: api.search_fields_by_text(a[0]),
        # Category 8: Relationship Queries
        "get_tables_for_register": lambda a: api.get_tables_for_register(a[0]),
        "get_figures_for_register": lambda a: api.get_figures_for_register(a[0]),
        "get_chunks_for_register": lambda a: api.get_chunks_for_register(a[0]),
        "get_registers_for_table": lambda a: api.get_registers_for_table(a[0]),
        "get_chunks_referencing": lambda a: api.get_chunks_referencing(a[0]),
        # Category 9: Metadata & Navigation
        "get_spec_info": lambda a: api.get_spec_info(),
        "get_register_map": lambda a: api.get_register_map(),
    }
    
    if args.function not in func_map:
        print(f"Unknown function: {args.function}")
        print(f"Available: {', '.join(func_map.keys())}")
        return 1
    
    result = func_map[args.function](args.args)
    
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        # Pretty print
        if result["success"]:
            print(f"✓ {result['function']} - {result['count']} result(s)")
            if result["truncated"]:
                print(f"  ⚠ Results truncated to {MAX_RESULTS}")
            print(json.dumps(result["results"], indent=2))
        else:
            print(f"✗ {result['function']} - ERROR")
            print(f"  {result['error']}")
    
    return 0 if result["success"] else 1


if __name__ == "__main__":
    exit(main())
