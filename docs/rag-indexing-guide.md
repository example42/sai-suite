# RAG Indexing and Similarity Search Guide

This guide explains how to use the RAG (Retrieval-Augmented Generation) indexing and similarity search functionality in saigen.

## Overview

The RAG system provides semantic search capabilities for:
- **Repository packages**: Search for similar packages across different package managers
- **Existing saidata files**: Find similar software definitions to use as examples
- **Context building**: Automatically gather relevant information for LLM-based generation

## Prerequisites

RAG functionality requires additional dependencies:

```bash
pip install saigen[rag]
```

This installs:
- `sentence-transformers`: For generating embeddings
- `faiss-cpu`: For efficient similarity search
- `numpy`: For numerical operations

## CLI Commands

### Index Management

#### Check Index Status
```bash
saigen index status
```

Shows the current state of RAG indices, including:
- Package index availability and count
- Saidata index availability and count
- Embedding model information
- Storage size

#### Rebuild Indices
```bash
# Rebuild all indices
saigen index rebuild

# Rebuild with specific saidata directory
saigen index rebuild --saidata-dir /path/to/saidata

# Rebuild specific repositories only
saigen index rebuild --repositories apt brew

# Force rebuild even if indices exist
saigen index rebuild --force
```

#### Clear All Indices
```bash
saigen index clear
```

### Similarity Search

#### Search Repository Packages
```bash
# Basic package search
saigen index search "web server"

# Advanced search with parameters
saigen index search "database" --limit 10 --min-score 0.4
```

#### Find Similar Saidata
```bash
# Find similar saidata files
saigen index find-saidata "nginx"

# With custom parameters
saigen index find-saidata "docker" --limit 5 --min-score 0.3
```

#### Build RAG Context
```bash
# Build context for software
saigen index context "web server"

# Target specific providers
saigen index context "database" --providers apt brew --max-packages 5
```

## How It Works

### 1. Repository Package Indexing

The system extracts packages from the repository cache and creates semantic embeddings:

```python
# Packages are indexed with their metadata
package_text = f"{name} {description} category: {category} tags: {tags} repository: {repository}"
```

### 2. Saidata File Indexing

Existing saidata files are indexed to provide examples:

```python
# Saidata is indexed with comprehensive metadata
saidata_text = f"{name} {description} category: {category} providers: {providers} packages: {package_names}"
```

### 3. Semantic Search

Uses sentence transformers to find semantically similar items:

- **Model**: `all-MiniLM-L6-v2` (lightweight, fast)
- **Similarity**: Cosine similarity with configurable thresholds
- **Storage**: FAISS indices for efficient search

### 4. Context Building

Combines multiple sources for comprehensive context:

- Similar repository packages
- Similar existing saidata files
- Default sample saidata files
- Provider-specific filtering

## Configuration

RAG settings can be configured in your saigen config:

```yaml
rag:
  enabled: true
  index_dir: "~/.saigen/rag_index"
  model_name: "all-MiniLM-L6-v2"
  use_default_samples: true
  max_sample_examples: 3
  default_samples_directory: "docs/saidata_samples"
```

## Integration with Generation

The RAG system automatically enhances saidata generation by:

1. **Finding similar packages** in repositories for accurate naming
2. **Providing examples** from existing saidata files
3. **Building context** that gets injected into LLM prompts
4. **Improving accuracy** through retrieval-augmented generation

## Performance Notes

- **First run**: Downloads the embedding model (~90MB)
- **Indexing**: Processes packages/files in batches for memory efficiency
- **Search**: Sub-second response times for typical queries
- **Storage**: Indices are cached on disk for persistence

## Troubleshooting

### RAG Not Available
```
RAG functionality is not available. Install with: pip install saigen[rag]
```
**Solution**: Install the RAG dependencies as shown above.

### No Repository Data
```
No repository data found. Run 'saigen repositories update' first.
```
**Solution**: Update repository cache before indexing:
```bash
saigen repositories update
```

### Model Download Issues
If the embedding model fails to download, try:
```bash
# Clear cache and retry
rm -rf ~/.cache/huggingface/
saigen index rebuild
```

## Examples

### Complete Workflow

```bash
# 1. Update repository cache
saigen repositories update

# 2. Rebuild RAG indices
saigen index rebuild --saidata-dir saidata

# 3. Check status
saigen index status

# 4. Search for similar packages
saigen index search "web server"

# 5. Find similar saidata
saigen index find-saidata "nginx"

# 6. Build context for generation
saigen index context "database server" --providers apt dnf
```

### Using in Generation

The RAG system automatically enhances generation:

```bash
# This will use RAG context if available
saigen generate nginx --providers apt dnf
```

The generation process will:
1. Search for similar packages named "nginx"
2. Find existing nginx saidata files
3. Build comprehensive context
4. Inject context into LLM prompts
5. Generate more accurate saidata