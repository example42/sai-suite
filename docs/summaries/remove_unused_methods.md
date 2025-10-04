# Unused Methods Removal Plan

## Methods to Remove

### 1. ConfigManager (saigen/utils/config.py)
- `update_config()` - Not used anywhere

### 2. GenerationEngine (saigen/core/generation_engine.py)  
- `_generate_configure_args()` - Already removed in previous cleanup

### 3. LLMProviderManager (saigen/llm/provider_manager.py)
- `get_cost_estimate()` - Not used
- `get_provider_models()` - Not used
- `set_provider_model()` - Not used

### 4. OllamaProvider (saigen/llm/providers/ollama.py)
- `get_usage_stats()` - Not used

### 5. ParserRegistry (saigen/repositories/parsers/__init__.py)
- `get_available_formats()` - Not used

### 6. SaigenConfig (saigen/models/config.py)
- `validate_llm_providers()` - Not used

### 7. URLTemplateProcessor (saigen/utils/url_templating.py)
- `get_supported_placeholders()` - Not used
- `render_template()` - Not used

### 8. Module-level functions
- `get_version_info()` - Not used (saigen/version.py)
- `integrate_v03_prompts()` - Not used (saigen/llm/prompts_v03.py)
- `load_saidata_schema_v03()` - Not used (saigen/llm/prompts_v03.py)
- `validate_v03_templates()` - Not used (saigen/llm/prompts_v03.py)

## Already Removed
✅ BaseRepositoryDownloader.extract_package_metadata
✅ BaseRepositoryDownloader.normalize_package_name
✅ ChecksumValidator.get_supported_algorithms
✅ ChecksumValidator.is_valid_format

## Methods to Keep (False Positives)
- config_init, config_show, config_set, config_validate, config_samples - These are CLI commands
- list_repos, stats - These are CLI commands
- verify_checksum - Used in validation
- replace_secret_str - Used in config display
- _get_available_providers - Used in generation engine
- auto_detect - Used in URL templating

