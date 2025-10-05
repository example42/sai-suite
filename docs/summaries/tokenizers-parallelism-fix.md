# Tokenizers Parallelism Warning Fix

## Issue
When running batch generation, the following warning appeared:

```
huggingface/tokenizers: The current process just got forked, after parallelism has already been used. 
Disabling parallelism to avoid deadlocks...
To disable this warning, you can either:
- Avoid using `tokenizers` before the fork if possible
- Explicitly set the environment variable TOKENIZERS_PARALLELISM=(true | false)
```

## Root Cause
The warning occurs because:
1. The RAG system loads the sentence transformer model (`all-MiniLM-L6-v2`) which uses HuggingFace tokenizers
2. The tokenizers library initializes Rust-based parallelism internally
3. The batch engine then forks processes for concurrent generation
4. Forking after parallelism initialization can cause deadlocks due to inconsistent threading state

## Solution Implemented
Set the `TOKENIZERS_PARALLELISM` environment variable to `"false"` before importing the sentence_transformers library.

### Code Changes
Modified `saigen/repositories/indexer.py`:

```python
"""RAG (Retrieval-Augmented Generation) indexer for semantic search."""

import os
import asyncio
import json
import pickle
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple, Union, TYPE_CHECKING
from datetime import datetime, timedelta

# Disable tokenizers parallelism to avoid fork-related warnings
# This must be set before importing sentence_transformers
os.environ["TOKENIZERS_PARALLELISM"] = "false"

try:
    import numpy as np
    from sentence_transformers import SentenceTransformer
    import faiss
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    # ...
```

## Why This Location
The environment variable is set in `indexer.py` because:
- This is where the sentence transformer model is loaded
- It's set before the `sentence_transformers` import
- It affects all subsequent tokenizer operations
- It's early enough in the initialization chain to prevent the warning

## Performance Impact
Setting `TOKENIZERS_PARALLELISM="false"` disables parallel tokenization, which means:
- Tokenization will be slightly slower (single-threaded)
- **Impact is negligible** because:
  - LLM API calls are orders of magnitude slower than tokenization
  - The RAG system only tokenizes relatively small text chunks
  - The bottleneck is network I/O, not CPU-bound tokenization

## Alternative Solutions Considered
1. **Lazy load the model** (Option 2): Would require refactoring the RAG initialization
2. **Use threading instead of forking** (Option 3): Would require changes to the batch engine's concurrency model

Option 1 was chosen for its simplicity and minimal impact.

## Testing
The fix can be verified by running batch generation and confirming the warning no longer appears:
```bash
saigen batch -f docs/software_lists/test_sets/test_current.txt --preview
```

The warning should no longer appear in the output.
