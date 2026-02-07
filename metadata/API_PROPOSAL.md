# SD Host 3.0 RAG API - Design Proposal v2

> **Purpose**: Agent-friendly API for querying the SD Host Controller specification metadata
> **Target Users**: LLM agents assisting developers and testers
> **Design Principle**: Strict, specialized functions - NO flexibility to prevent hallucinations

---

## Design Philosophy

### Core Principles

1. **One Function = One Purpose** - No multi-purpose parameters
2. **Explicit Over Flexible** - `get_register_by_offset()` not `get_register(identifier)`
3. **Predictable Output** - Consistent JSON structure across all responses
4. **Token Efficiency** - Return only what's needed
5. **Hard Limits** - Max 1000 results, require refinement if exceeded
6. **No Write Operations** - Read-only API

### Response Format (All Functions)

```python
{
    "success": bool,           # True if query succeeded
    "function": str,           # Function that was called
    "params": dict,            # Parameters that were passed
    "count": int,              # Number of results
    "truncated": bool,         # True if results were limited
    "results": [...],          # Array of results (type varies)
    "error": str | None        # Error message if success=False
}
```

### Error Responses

```python
{
    "success": False,
    "function": "get_register_by_offset",
    "params": {"offset": "999h"},
    "count": 0,
    "truncated": False,
    "results": [],
    "error": "NOT_FOUND: No register at offset 999h. Valid range: 000h-0FFh"
}
```

### Result Limit Policy

- Maximum 1000 results per query
- If exceeded: `truncated: True` + error suggestion to refine query
- Agent must use more specific filters

---

## API Functions

### Category 1: Register Access (by specific identifier)

#### `get_register_by_offset(offset: str) -> Register`
Get register by hex offset.

```python
get_register_by_offset("028h")
get_register_by_offset("028")   # 'h' suffix optional
get_register_by_offset("0x028") # 0x prefix accepted
```

**Returns**: Single REGISTER node with all fields.

---

#### `get_register_by_id(register_id: str) -> Register`
Get register by exact ID.

```python
get_register_by_id("REG_028")
```

**Returns**: Single REGISTER node with all fields.

---

#### `get_register_by_name(name: str, exact: bool = False) -> List[Register]`
Get registers matching name pattern.

```python
get_register_by_name("Host Control 1", exact=True)  # Exact match
get_register_by_name("Control")                      # Contains match
```

**Returns**: List of matching REGISTER nodes (summary, no fields).

---

#### `list_registers(class_id: str = None) -> List[RegisterSummary]`
List all registers, optionally filtered by class.

```python
list_registers()                              # All 32 registers
list_registers(class_id="REGCLASS_INTERRUPT") # Only interrupt registers
```

**Returns**: List of `{id, name, offset, class_id, field_count}`.

---

#### `get_registers_in_range(start_offset: str, end_offset: str) -> List[Register]`
Get registers within an offset range.

```python
get_registers_in_range("024h", "030h")
```

**Returns**: List of REGISTER nodes in range (summary, no fields).

---

### Category 2: Register Class Access

#### `get_register_class_by_id(class_id: str) -> RegisterClass`
Get register class by exact ID.

```python
get_register_class_by_id("REGCLASS_INTERRUPT")
```

**Returns**: REG_CLASS node with member register IDs.

---

#### `list_register_classes() -> List[RegisterClassSummary]`
List all register classes.

**Returns**: List of `{id, name, start_offset, end_offset, register_count}`.

---

### Category 3: Field Access

#### `get_field_by_id(field_id: str) -> Field`
Get field by exact ID.

```python
get_field_by_id("REG_028_F3")
```

**Returns**: Full field object with raw, abstract, values.

---

#### `get_field_by_name(register_id: str, field_name: str) -> Field`
Get field by name within a register.

```python
get_field_by_name("REG_028", "DMA Select")
```

**Returns**: Full field object.

---

#### `get_field_by_bit(register_id: str, bit: int) -> Field`
Get field containing a specific bit position.

```python
get_field_by_bit("REG_028", 4)  # Which field owns bit 4?
```

**Returns**: Full field object.

---

#### `list_fields_in_register(register_id: str) -> List[FieldSummary]`
List all fields in a register.

```python
list_fields_in_register("REG_028")
```

**Returns**: List of `{id, name, bits, width, access}`.

---

#### `search_fields_by_access(access: str, register_id: str = None) -> List[FieldSummary]`
Find fields by access type.

```python
search_fields_by_access("read-only")                     # All RO fields
search_fields_by_access("read-write", register_id="REG_028")  # RW in specific reg
```

**Valid access values**: `read-only`, `read-write`, `write-only`, `reserved`

**Returns**: List of field summaries with register context.

---

#### `search_fields_by_name(pattern: str) -> List[FieldSummary]`
Search fields by name pattern across all registers.

```python
search_fields_by_name("Enable")
search_fields_by_name("DMA")
```

**Returns**: List of field summaries with register context.

---

### Category 4: Spec Content Access

#### `get_page_content(spec_page: int) -> PageContent`
Get full content of a specification page.

```python
get_page_content(41)
```

**Returns**:
```python
{
    "spec_page": 41,
    "pdf_page": 52,
    "content": "concatenated chunk text...",
    "chunks": ["SEC_2_2_10_C0", "SEC_2_2_10_C1"],
    "tables_on_page": ["TABLE_2_16"],
    "figures_on_page": [],
    "registers_on_page": ["REG_028"]
}
```

---

#### `get_section_by_number(section_number: str) -> Section`
Get section content by number.

```python
get_section_by_number("2.2.10")
```

**Returns**: Section with all chunks, title, abstract.

---

#### `get_chunk_by_id(chunk_id: str) -> Chunk`
Get specific chunk by ID.

```python
get_chunk_by_id("SEC_2_2_10_C0")
```

**Returns**: Full SPEC_CHUNK node with raw text.

---

#### `list_sections(parent: str = None) -> List[SectionSummary]`
List sections, optionally under a parent.

```python
list_sections()           # All top-level sections
list_sections("2.2")      # All children of 2.2
```

**Returns**: List of `{section_number, title, chunk_count, page}`.

---

### Category 5: Table Access

#### `get_table_by_id(table_id: str) -> Table`
Get table by exact ID.

```python
get_table_by_id("TABLE_2_16")
```

**Returns**: TABLE node with CSV path.

---

#### `get_table_by_reference(spec_ref: str) -> Table`
Get table by spec reference string.

```python
get_table_by_reference("Table 2-16")
```

**Returns**: TABLE node.

---

#### `list_tables(table_type: str = None) -> List[TableSummary]`
List tables, optionally by type.

```python
list_tables()
list_tables(table_type="REGISTER_FIELDS")
```

**Valid types**: `REGISTER_FIELDS`, `REGISTER_MAP`, `SIGNAL_LIST`, `TIMING`, `OTHER`

**Returns**: List of `{id, name, spec_reference, page, table_type}`.

---

#### `get_table_csv(table_id: str) -> List[List[str]]`
Get parsed CSV content.

```python
get_table_csv("TABLE_2_16")
```

**Returns**: 2D array (rows × columns).

---

### Category 6: Figure Access

#### `get_figure_by_id(figure_id: str) -> Figure`
Get figure by exact ID.

```python
get_figure_by_id("FIG_2_1")
```

**Returns**: FIGURE node with PlantUML path.

---

#### `get_figure_by_reference(spec_ref: str) -> Figure`
Get figure by spec reference string.

```python
get_figure_by_reference("Figure 2-1")
```

**Returns**: FIGURE node.

---

#### `list_figures(figure_type: str = None) -> List[FigureSummary]`
List figures, optionally by type.

```python
list_figures()
list_figures(figure_type="STATE_DIAGRAM")
```

**Valid types**: `STATE_DIAGRAM`, `TIMING_DIAGRAM`, `BLOCK_DIAGRAM`, `REGISTER_LAYOUT`, `FLOWCHART`, `OTHER`

**Returns**: List of `{id, name, spec_reference, page, figure_type}`.

---

#### `get_figure_plantuml(figure_id: str) -> str`
Get PlantUML source code.

```python
get_figure_plantuml("FIG_2_1")
```

**Returns**: Raw PlantUML text string.

---

### Category 7: Search Functions

#### `search_by_keywords(keywords: List[str], node_types: List[str] = None) -> List[SearchResult]`
Search nodes by index keywords.

```python
search_by_keywords(["interrupt", "status"])
search_by_keywords(["DMA"], node_types=["REGISTER"])
```

**Valid node_types**: `REGISTER`, `SPEC_CHUNK`, `TABLE`, `FIGURE`, `REG_CLASS`

**Returns**: List of `{node_id, node_type, name, score, matched_keywords}`.

---

#### `search_chunks_by_text(query: str) -> List[ChunkSearchResult]`
Full-text search in chunk content.

```python
search_chunks_by_text("shall be set to 1")
```

**Returns**: List of `{chunk_id, section_number, excerpt, match_position}`.

---

#### `search_fields_by_text(query: str) -> List[FieldSearchResult]`
Full-text search in field raw descriptions.

```python
search_fields_by_text("reserved")
```

**Returns**: List of `{field_id, register_id, field_name, excerpt}`.

---

### Category 8: Relationship Queries

#### `get_tables_for_register(register_id: str) -> List[str]`
Get table IDs that define a register.

```python
get_tables_for_register("REG_028")
```

**Returns**: List of table IDs (usually 1).

---

#### `get_figures_for_register(register_id: str) -> List[str]`
Get figure IDs that visualize a register.

```python
get_figures_for_register("REG_028")
```

**Returns**: List of figure IDs.

---

#### `get_chunks_for_register(register_id: str) -> List[str]`
Get chunk IDs that describe a register.

```python
get_chunks_for_register("REG_028")
```

**Returns**: List of chunk IDs.

---

#### `get_registers_for_table(table_id: str) -> List[str]`
Get register IDs defined by a table.

```python
get_registers_for_table("TABLE_2_16")
```

**Returns**: List of register IDs.

---

#### `get_chunks_referencing(node_id: str) -> List[str]`
Get chunks that reference a table or figure.

```python
get_chunks_referencing("TABLE_2_16")
get_chunks_referencing("FIG_2_1")
```

**Returns**: List of chunk IDs.

---

### Category 9: Metadata & Navigation

#### `get_spec_info() -> SpecInfo`
Get specification metadata.

**Returns**:
```python
{
    "name": "SD Host Controller Simplified Specification",
    "version": "3.00",
    "total_pages": 157,
    "node_counts": {"REGISTER": 32, "TABLE": 60, ...},
    "total_relations": 606
}
```

---

#### `get_register_map() -> List[RegisterMapEntry]`
Get full register address map (sorted by offset).

**Returns**: List of `{offset, id, name, size_bits, class_id}`.

---

#### `get_section_tree() -> SectionTree`
Get hierarchical section structure.

**Returns**: Nested structure with `{number, title, children: [...]}`.

---

---

## Function Summary Table

| Category | Function | Returns |
|----------|----------|---------|
| **Register** | `get_register_by_offset(offset)` | Single register with fields |
| | `get_register_by_id(id)` | Single register with fields |
| | `get_register_by_name(name, exact)` | List of matching registers |
| | `list_registers(class_id)` | All register summaries |
| | `get_registers_in_range(start, end)` | Registers in offset range |
| **Reg Class** | `get_register_class_by_id(id)` | Single class with members |
| | `list_register_classes()` | All class summaries |
| **Field** | `get_field_by_id(id)` | Single field full detail |
| | `get_field_by_name(reg_id, name)` | Single field full detail |
| | `get_field_by_bit(reg_id, bit)` | Single field full detail |
| | `list_fields_in_register(reg_id)` | Field summaries in register |
| | `search_fields_by_access(access)` | Fields by access type |
| | `search_fields_by_name(pattern)` | Fields by name pattern |
| **Spec** | `get_page_content(page)` | Page text + resources |
| | `get_section_by_number(num)` | Section with chunks |
| | `get_chunk_by_id(id)` | Single chunk full text |
| | `list_sections(parent)` | Section summaries |
| **Table** | `get_table_by_id(id)` | Single table |
| | `get_table_by_reference(ref)` | Single table |
| | `list_tables(type)` | Table summaries |
| | `get_table_csv(id)` | Parsed CSV data |
| **Figure** | `get_figure_by_id(id)` | Single figure |
| | `get_figure_by_reference(ref)` | Single figure |
| | `list_figures(type)` | Figure summaries |
| | `get_figure_plantuml(id)` | PlantUML source |
| **Search** | `search_by_keywords(kw, types)` | Matching nodes |
| | `search_chunks_by_text(query)` | Matching chunks |
| | `search_fields_by_text(query)` | Matching fields |
| **Relations** | `get_tables_for_register(id)` | Table IDs |
| | `get_figures_for_register(id)` | Figure IDs |
| | `get_chunks_for_register(id)` | Chunk IDs |
| | `get_registers_for_table(id)` | Register IDs |
| | `get_chunks_referencing(id)` | Chunk IDs |
| **Navigation** | `get_spec_info()` | Spec metadata |
| | `get_register_map()` | Full offset map |
| | `get_section_tree()` | Section hierarchy |

**Total: 35 specialized functions**

---

## Implementation Priority

### Phase 1 (MVP) - Core Register/Field Access
1. `get_register_by_offset()`
2. `get_register_by_id()`
3. `list_registers()`
4. `get_field_by_id()`
5. `get_field_by_name()`
6. `list_fields_in_register()`
7. `get_spec_info()`
8. `get_register_map()`

### Phase 2 - Spec Content
9. `get_page_content()`
10. `get_section_by_number()`
11. `get_chunk_by_id()`
12. `list_sections()`
13. `get_table_by_id()`
14. `get_figure_by_id()`

### Phase 3 - Search & Relations
15. `search_by_keywords()`
16. `search_chunks_by_text()`
17. `search_fields_by_access()`
18. `get_tables_for_register()`
19. `get_chunks_for_register()`
20. Remaining functions...

---

## File Structure

```
metadata/
├── metadata.json           # The data (read-only)
├── metadata_api.py         # The API implementation
├── context.md              # Folder documentation
└── API_PROPOSAL.md         # This design doc
```
