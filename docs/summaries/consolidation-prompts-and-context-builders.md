# Consolidation: Prompts and Context Builders

## Date
October 4, 2025

## Objective
Consolidate duplicate prompt and context builder files to reduce confusion and improve maintainability.

## Changes Made

### 1. Moved ContextBuilderV03 Class
**From**: `saigen/llm/prompts_v03.py`  
**To**: `saigen/core/context_builder.py` (formerly `context_builder_v03.py`)

The `ContextBuilderV03` class contained useful example data for:
- Installation method examples (sources, binaries, scripts)
- Security metadata examples
- Compatibility matrix examples

This class was being imported by `EnhancedContextBuilder` (formerly `EnhancedContextBuilderV03`), so it made sense to move it into the same file.

### 2. Renamed Files
- `saigen/core/context_builder_v03.py` → `saigen/core/context_builder.py`

### 3. Renamed Classes
- `EnhancedContextBuilderV03` → `EnhancedContextBuilder`

### 4. Deleted Files
- ❌ `saigen/llm/prompts_v03.py` - Deleted (was not being used)

### 5. Updated References
Updated imports in:
- `saigen/core/generation_engine.py`:
  - Changed: `from .context_builder_v03 import EnhancedContextBuilderV03`
  - To: `from .context_builder import EnhancedContextBuilder`
  - Updated instantiation: `EnhancedContextBuilderV03(...)` → `EnhancedContextBuilder(...)`

## Final Architecture

### Active Files

1. **`saigen/llm/prompts.py`** ✅
   - Contains all prompt templates used by LLM providers
   - Provides: `PromptManager`, `SAIDATA_GENERATION_TEMPLATE`, `UPDATE_SAIDATA_TEMPLATE`, `RETRY_SAIDATA_TEMPLATE`
   - Used by: OpenAI, Anthropic, Ollama providers

2. **`saigen/core/context_builder.py`** ✅
   - Contains context enhancement logic for saidata generation
   - Provides: `EnhancedContextBuilder`, `ContextBuilderV03`
   - Used by: `GenerationEngine`

### Removed Files

1. **`saigen/llm/prompts_v03.py`** ❌ DELETED
   - Was an unused alternative implementation
   - Contained duplicate prompt templates
   - Had `ContextBuilderV03` class which was moved to `context_builder.py`

## Benefits

1. **Reduced Confusion**: No more duplicate files with similar names
2. **Clearer Architecture**: One prompt file, one context builder file
3. **Easier Maintenance**: Changes only need to be made in one place
4. **Better Organization**: Related code is now together

## Testing

Tested generation after consolidation:
```bash
python -m saigen generate redis --force
```

Results:
- ✅ Generation successful
- ✅ No checksums included
- ✅ All imports working correctly
- ✅ Context enhancement working (with minor non-blocking warning)

## Migration Notes

If you have any custom code that imports from the old locations:

**Old imports** (no longer work):
```python
from saigen.llm.prompts_v03 import ContextBuilderV03
from saigen.core.context_builder_v03 import EnhancedContextBuilderV03
```

**New imports** (correct):
```python
from saigen.core.context_builder import ContextBuilderV03
from saigen.core.context_builder import EnhancedContextBuilder
```

## Files Modified

1. `saigen/core/context_builder_v03.py` → `saigen/core/context_builder.py` (renamed + updated)
2. `saigen/core/generation_engine.py` (updated imports)
3. `saigen/llm/prompts_v03.py` (deleted)

## Impact

- **Positive**: Cleaner codebase, less confusion
- **Positive**: Easier to maintain and understand
- **Neutral**: No functional changes, everything works the same
- **Breaking**: Any external code importing from `prompts_v03.py` will need updates (unlikely to exist)
