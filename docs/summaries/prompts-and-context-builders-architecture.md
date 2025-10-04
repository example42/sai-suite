# Prompts and Context Builders Architecture

## Current State (As of October 4, 2025)

### Which Files Are Actually Used?

#### **Prompts: `prompts.py` is ACTIVELY USED** ✅

**Location**: `saigen/llm/prompts.py`

**Used by**: All LLM providers (OpenAI, Anthropic, Ollama)
- `saigen/llm/providers/openai.py` → imports `PromptManager` from `prompts.py`
- `saigen/llm/providers/anthropic.py` → imports `PromptManager` from `prompts.py`
- `saigen/llm/providers/ollama.py` → imports `PromptManager` from `prompts.py`

**Templates provided**:
- `SAIDATA_GENERATION_TEMPLATE` - Main generation template
- `UPDATE_SAIDATA_TEMPLATE` - Update existing saidata
- `RETRY_SAIDATA_TEMPLATE` - Retry after validation failure

**Status**: ✅ **ACTIVE** - This is the file that controls what prompts are sent to LLMs

---

#### **Prompts V03: `prompts_v03.py` is NOT USED** ❌

**Location**: `saigen/llm/prompts_v03.py`

**Used by**: Nobody currently

**Templates provided**:
- `SAIDATA_V03_GENERATION_TEMPLATE` - Enhanced 0.3 generation template
- `PromptManagerV03` - Alternative prompt manager

**Status**: ❌ **UNUSED** - This appears to be an alternative/experimental implementation that was never integrated

---

#### **Context Builder: `context_builder_v03.py` is ACTIVELY USED** ✅

**Location**: `saigen/core/context_builder_v03.py`

**Used by**: `GenerationEngine`
- `saigen/core/generation_engine.py` → imports `EnhancedContextBuilderV03`
- Initialized in `GenerationEngine.__init__()`: `self.enhanced_context_builder = EnhancedContextBuilderV03(...)`
- Called in `_build_enhanced_generation_context_v03()` method

**Purpose**: Enhances the generation context with 0.3-specific features:
- Installation method examples (sources, binaries, scripts)
- Security metadata templates
- Compatibility matrix templates
- URL templating examples
- Provider enhancement examples

**Status**: ✅ **ACTIVE** - Used to build enhanced context for 0.3 schema generation

---

## Why Both prompts.py and prompts_v03.py Exist?

Based on the code analysis:

1. **`prompts.py`** - The **production/active** prompt templates
   - Contains the actual prompts used by all LLM providers
   - Has 0.3 schema support built-in
   - Was updated with checksum fixes

2. **`prompts_v03.py`** - An **unused/experimental** alternative
   - Appears to be a more elaborate version with enhanced features
   - Has `ContextBuilderV03` class with installation method examples
   - Was never integrated into the provider code
   - Also updated with checksum fixes (for consistency)

## Recommendation

Since `prompts_v03.py` is not being used, you have two options:

### Option 1: Keep Both (Current State)
- **Pros**: Preserves experimental work, both files now have checksum fixes
- **Cons**: Confusing to maintain, duplicate code

### Option 2: Consolidate
- Merge useful features from `prompts_v03.py` into `prompts.py`
- Delete `prompts_v03.py` to reduce confusion
- Keep only `context_builder_v03.py` for context enhancement

### Option 3: Switch to V03
- Update all LLM providers to use `PromptManagerV03` from `prompts_v03.py`
- This would require changing imports in 3 provider files
- Would give access to more elaborate prompt templates

## Current Fix Status

Both files were updated with checksum fixes, so the system works correctly regardless of which approach you choose in the future:

✅ **`prompts.py`** - Fixed (actively used)
✅ **`prompts_v03.py`** - Fixed (not used, but consistent)
✅ **`context_builder_v03.py`** - Fixed (actively used)

## Summary

**What's actually running in production:**
- ✅ `prompts.py` → Provides prompts to LLMs
- ✅ `context_builder_v03.py` → Enhances context with 0.3 features
- ❌ `prompts_v03.py` → Not used anywhere

The system is working correctly with the current architecture.
