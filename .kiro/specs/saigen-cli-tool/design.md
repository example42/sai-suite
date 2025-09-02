# Design Document

## Overview

The `saigen` CLI tool is designed as an intelligent saidata generation system that combines multiple data sources (LLMs, repository metadata, existing saidata) to create comprehensive and accurate software definitions. The architecture emphasizes modularity, extensibility, and robust data processing while maintaining high-quality output through validation and testing.

## Architecture

### Core Components

```
saigen/
├── cli/                    # Command-line interface layer
│   ├── commands/          # Individual command implementations
│   ├── parser.py          # Argument parsing and validation
│   └── output.py          # Formatted output and progress reporting
├── core/                  # Core business logic
│   ├── generator.py       # Main saidata generation engine
│   ├── llm_manager.py     # LLM provider management and routing
│   ├── repository_manager.py # Repository data downloading and caching
│   └── validator.py       # Saidata validation and testing
├── llm/                   # LLM integration layer
│   ├── providers/         # LLM provider implementations
│   │   ├── openai.py     # OpenAI GPT integration
│   │   ├── anthropic.py  # Anthropic Claude integration
│   │   ├── ollama.py     # Local Ollama integration
│   │   └── base.py       # Abstract LLM provider interface
│   ├── prompts/          # Prompt templates and management
│   └── context.py        # Context building and RAG integration
├── repositories/         # Repository data management
│   ├── downloaders/      # Repository-specific downloaders
│   │   ├── apt.py        # APT repository downloader
│   │   ├── brew.py       # Homebrew repository downloader
│   │   └── base.py       # Abstract downloader interface
│   ├── cache.py          # Repository data caching system
│   └── indexer.py        # RAG indexing and search
├── models/               # Data models and schemas
│   ├── saidata.py        # Saidata structure models
│   ├── repository.py     # Repository data models
│   ├── generation.py     # Generation request/response models
│   └── config.py         # Configuration models
└── utils/                # Utility functions
    ├── schema.py         # Schema validation utilities
    ├── templating.py     # Template processing
    └── testing.py        # Saidata testing utilities
```## 
Components and Interfaces

### LLM Provider Interface

```python
class BaseLLMProvider(ABC):
    @abstractmethod
    async def generate_saidata(self, software_name: str, context: GenerationContext) -> SaidataResponse:
        """Generate saidata using LLM with provided context"""
        
    @abstractmethod
    def is_available(self) -> bool:
        """Check if LLM provider is properly configured"""
        
    @abstractmethod
    def get_model_info(self) -> ModelInfo:
        """Return information about the model being used"""

class GenerationContext:
    software_name: str
    repository_data: List[RepositoryPackage]
    similar_saidata: List[SaiData]
    user_hints: Optional[Dict[str, Any]]
    target_providers: List[str]
```

### Repository Downloader Interface

```python
class BaseRepositoryDownloader(ABC):
    @abstractmethod
    async def download_package_list(self) -> List[RepositoryPackage]:
        """Download complete package list from repository"""
        
    @abstractmethod
    async def search_package(self, name: str) -> List[RepositoryPackage]:
        """Search for specific package in repository"""
        
    @abstractmethod
    def get_cache_key(self) -> str:
        """Return unique cache key for this repository"""

class RepositoryPackage:
    name: str
    version: str
    description: str
    homepage: Optional[str]
    dependencies: List[str]
    repository_name: str
    platform: str
```

### RAG System Interface

```python
class RAGIndexer:
    def index_repository_data(self, packages: List[RepositoryPackage]) -> None:
        """Index repository data for semantic search"""
        
    def index_existing_saidata(self, saidata_files: List[Path]) -> None:
        """Index existing saidata files for similarity search"""
        
    def search_similar_packages(self, query: str, limit: int = 5) -> List[RepositoryPackage]:
        """Find similar packages using semantic search"""
        
    def find_similar_saidata(self, software_name: str, limit: int = 3) -> List[SaiData]:
        """Find similar existing saidata files"""
```

## Data Models

### Generation Request

```python
@dataclass
class GenerationRequest:
    software_name: str
    target_providers: List[str]
    llm_provider: str
    use_rag: bool = True
    user_hints: Optional[Dict[str, Any]] = None
    output_path: Optional[Path] = None
    update_mode: bool = False
```

### Generation Result

```python
@dataclass
class GenerationResult:
    success: bool
    saidata: Optional[SaiData]
    validation_errors: List[str]
    warnings: List[str]
    generation_time: float
    llm_provider_used: str
    repository_sources_used: List[str]
```

### Repository Cache Entry

```python
@dataclass
class CacheEntry:
    repository_name: str
    data: List[RepositoryPackage]
    timestamp: datetime
    expires_at: datetime
    checksum: str
```

## LLM Integration Design

### Prompt Engineering

The system uses structured prompts with context injection:

```python
class PromptTemplate:
    base_template: str
    context_sections: List[str]
    
    def render(self, context: GenerationContext) -> str:
        """Render prompt with context data"""

# Example prompt structure:
SAIDATA_GENERATION_PROMPT = """
Generate a saidata YAML file for the software: {software_name}

Context from repositories:
{repository_context}

Similar software examples:
{similar_saidata_examples}

Requirements:
- Follow the saidata schema exactly
- Include all relevant providers: {target_providers}
- Use accurate package names from repository data
- Include comprehensive metadata
"""
```

### Model Selection Strategy

```python
class ModelSelector:
    def select_best_model(self, request: GenerationRequest) -> str:
        """Select optimal model based on request complexity"""
        
    def get_fallback_models(self, primary_model: str) -> List[str]:
        """Return fallback models if primary fails"""
```

## Repository Data Management

### Caching Strategy

```python
class RepositoryCache:
    def __init__(self, cache_dir: Path, default_ttl: timedelta):
        self.cache_dir = cache_dir
        self.default_ttl = default_ttl
        
    async def get_or_fetch(self, downloader: BaseRepositoryDownloader) -> List[RepositoryPackage]:
        """Get from cache or fetch fresh data"""
        
    def invalidate(self, repository_name: str) -> None:
        """Invalidate specific repository cache"""
        
    def cleanup_expired(self) -> None:
        """Remove expired cache entries"""
```

### Data Transformation Pipeline

```python
class DataTransformer:
    def normalize_package_data(self, packages: List[RepositoryPackage]) -> List[RepositoryPackage]:
        """Normalize package data across different repositories"""
        
    def extract_metadata(self, package: RepositoryPackage) -> Dict[str, Any]:
        """Extract relevant metadata for saidata generation"""
        
    def deduplicate_packages(self, packages: List[RepositoryPackage]) -> List[RepositoryPackage]:
        """Remove duplicate packages across repositories"""
```## Val
idation and Testing Strategy

### Multi-Level Validation

```python
class SaidataValidator:
    def validate_schema(self, saidata: dict) -> ValidationResult:
        """Validate against JSON schema"""
        
    def validate_cross_references(self, saidata: SaiData) -> ValidationResult:
        """Validate internal consistency and references"""
        
    def validate_repository_accuracy(self, saidata: SaiData) -> ValidationResult:
        """Check package names against repository data"""

class SaidataTester:
    def dry_run_test(self, saidata: SaiData, providers: List[str]) -> TestResult:
        """Test saidata without actual installation"""
        
    def mcp_server_test(self, saidata: SaiData) -> TestResult:
        """Test using MCP servers if available"""
        
    def provider_compatibility_test(self, saidata: SaiData) -> TestResult:
        """Test compatibility across different providers"""
```

### Quality Metrics

```python
@dataclass
class QualityMetrics:
    schema_compliance: float
    repository_accuracy: float
    completeness_score: float
    provider_coverage: float
    metadata_richness: float
```

## Error Handling

### Error Hierarchy

```python
class SaigenError(Exception):
    """Base exception for saigen tool"""

class LLMProviderError(SaigenError):
    """LLM provider communication failed"""

class RepositoryError(SaigenError):
    """Repository data access failed"""

class ValidationError(SaigenError):
    """Generated saidata validation failed"""

class GenerationError(SaigenError):
    """Saidata generation process failed"""
```

### Resilience Patterns

1. **LLM Fallback**: Try alternative models/providers on failure
2. **Partial Generation**: Continue with available data when some sources fail
3. **Incremental Retry**: Retry failed operations with exponential backoff
4. **Graceful Degradation**: Reduce functionality rather than complete failure

## Performance Considerations

### Async Architecture

```python
class AsyncGenerationEngine:
    async def generate_batch(self, requests: List[GenerationRequest]) -> List[GenerationResult]:
        """Process multiple generation requests concurrently"""
        
    async def parallel_repository_fetch(self, downloaders: List[BaseRepositoryDownloader]) -> Dict[str, List[RepositoryPackage]]:
        """Fetch from multiple repositories in parallel"""
```

### Caching Layers

1. **Repository Data Cache**: Long-term cache for package lists
2. **LLM Response Cache**: Cache LLM responses for identical requests
3. **RAG Index Cache**: Persistent vector embeddings
4. **Schema Cache**: Compiled JSON schemas

### Resource Management

- Connection pooling for HTTP requests
- Memory-efficient streaming for large repository data
- Configurable concurrency limits
- Progress reporting for long-running operations

## Security Considerations

### API Key Management

```python
class SecureConfig:
    def load_api_keys(self) -> Dict[str, str]:
        """Load API keys from secure storage"""
        
    def mask_sensitive_data(self, config: dict) -> dict:
        """Mask sensitive data in config display"""
```

### Input Sanitization

- Validate software names against allowed patterns
- Sanitize repository URLs and paths
- Prevent injection attacks in LLM prompts
- Secure temporary file handling

## Testing Strategy

### Unit Testing

- Mock LLM providers for consistent testing
- Test repository downloaders with fixture data
- Validate prompt template rendering
- Test caching mechanisms with temporary directories

### Integration Testing

- End-to-end generation workflows
- Real LLM provider integration (with test accounts)
- Repository downloader integration
- Cross-platform compatibility testing

### Performance Testing

- Batch generation performance benchmarks
- Memory usage profiling
- Cache effectiveness measurement
- Concurrent request handling

## CLI Design

### Command Structure

```bash
saigen generate <software> [options]
saigen batch <software-list-file> [options]
saigen update <existing-saidata-file> [options]
saigen validate <saidata-file> [options]
saigen test <saidata-file> [options]
saigen config [show|set <key> <value>]
saigen cache [update|clear|status]
saigen index [rebuild|status]
```

### Global Options

- `--llm-provider <name>`: Specify LLM provider
- `--no-rag`: Disable RAG context injection
- `--output-dir <path>`: Output directory for generated files
- `--config <file>`: Use specific config file
- `--verbose`: Detailed output
- `--dry-run`: Show what would be generated without creating files