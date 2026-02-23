#!/usr/bin/env python3
"""
Data classes for the RAG V2 pipeline.

Mirrors the v1 Node/Relation schema for backward compatibility.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class SourceInfo:
    """Source location in PDF."""
    page: int = 0
    page_end: int = 0
    pdf_page: int = 0
    pdf_page_end: int = 0


@dataclass
class CoverageInfo:
    """Implementation coverage tracking."""
    status: str = "NOT_IMPLEMENTED"  # NOT_IMPLEMENTED | PARTIAL | IMPLEMENTED | NOT_APPLICABLE
    notes: str = ""
    implemented_in: str = ""


@dataclass
class Node:
    """Base node in the metadata graph.
    
    Same schema as v1 for backward compatibility with metadata_api.py.
    """
    id: str
    type: str  # TABLE | FIGURE | SPEC_CHUNK | REGISTER | REG_CLASS | FEATURE | HD_SEQUENCE
    name: str
    description: str = ""
    index_keywords: List[str] = field(default_factory=list)
    source: Dict = field(default_factory=dict)
    coverage: Dict = field(default_factory=lambda: {
        "status": "NOT_IMPLEMENTED",
        "notes": "",
        "implemented_in": ""
    })
    confidence: float = 1.0
    validation_status: str = "AUTO"  # AUTO | USER_VALIDATED | NEEDS_REVIEW
    extras: Dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "description": self.description,
            "index_keywords": self.index_keywords,
            "source": self.source,
            "coverage": self.coverage,
            "confidence": self.confidence,
            "validation_status": self.validation_status,
            "extras": self.extras
        }


@dataclass
class Relation:
    """Relation between nodes.
    
    Same schema as v1.
    """
    id: str
    type: str  # REFERENCES | CONTAINS | DESCRIBES | VISUALIZED_BY | DEFINED_BY | PART_OF | ...
    source_node: str
    target_node: str
    description: str = ""
    bidirectional: bool = False
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        d = {
            "id": self.id,
            "type": self.type,
            "source_node": self.source_node,
            "target_node": self.target_node,
        }
        if self.description:
            d["description"] = self.description
        if self.bidirectional:
            d["bidirectional"] = True
        return d
