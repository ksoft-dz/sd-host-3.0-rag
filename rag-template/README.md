# RAG Template - Technical Specification Extraction

A reusable template for building RAG (Retrieval Augmented Generation) knowledge bases from technical PDF specifications.

## Quick Start

1. Copy this `rag-template/` folder to your new project
2. Update `config.json` with your source PDF info
3. Run extraction scripts in order
4. Run merge to create unified metadata

## Folder Structure

```
rag-template/
├── config.json              # Project configuration
├── README.md                # This file
├── tables/
│   ├── context.md          # Instructions for table extraction
│   ├── tables_page_map.json # Template JSON
│   └── csv/                 # Output: converted CSV files
├── figures/
│   ├── context.md          # Instructions for figure extraction
│   ├── figures_page_map.json # Template JSON
│   └── plantuml/           # Output: PlantUML transcriptions
├── spec/
│   ├── context.md          # Instructions for section extraction
│   └── sections.json       # Template JSON
├── metadata/
│   ├── metadata.json       # Output: unified graph
│   └── metadata_api.py     # Generic query API
└── scripts/
    └── merge_metadata.py   # Generic merge script
```

## Extraction Order

1. **spec/sections.json** - Extract document structure (ToC) first
2. **tables/tables_page_map.json** - Extract tables, convert to CSV
3. **figures/figures_page_map.json** - Extract figures, optionally transcribe
4. **metadata/metadata.json** - Merge all into unified graph

## Customization Points

- **Domain-specific entities**: Add folders like `registers/`, `signals/`, `commands/`
- **Node types**: Extend the merge script to handle new entity types
- **Relations**: Define domain-specific relation types
- **Coverage tracking**: Customize status values for your workflow
