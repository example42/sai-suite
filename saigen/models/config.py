"""Configuration models for saigen tool."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, SecretStr, validator
from pathlib import Path
from enum import Enum


class LogLevel(str, Enum):
    """Logging levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class LLMConfig(BaseModel):
    """LLM provider configuration."""
    provider: str
    api_key: Optional[SecretStr] = None
    api_base: Optional[str] = None
    model: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    timeout: Optional[int] = 30
    max_retries: Optional[int] = 3
    enabled: bool = True
    
    class Config:
        """Pydantic configuration."""
        validate_assignment = True


class RepositoryConfig(BaseModel):
    """Repository configuration."""
    name: str
    type: str  # apt, dnf, brew, winget, etc.
    url: Optional[str] = None
    enabled: bool = True
    cache_ttl: int = 3600  # seconds
    priority: int = 1
    credentials: Optional[Dict[str, SecretStr]] = None
    
    class Config:
        """Pydantic configuration."""
        validate_assignment = True


class CacheConfig(BaseModel):
    """Cache configuration."""
    directory: Path = Path.home() / ".saigen" / "cache"
    max_size_mb: int = 1000
    default_ttl: int = 3600  # seconds
    cleanup_interval: int = 86400  # seconds (24 hours)
    
    class Config:
        """Pydantic configuration."""
        validate_assignment = True


class RAGConfig(BaseModel):
    """RAG (Retrieval-Augmented Generation) configuration."""
    enabled: bool = True
    index_directory: Path = Path.home() / ".saigen" / "rag_index"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    max_context_items: int = 5
    similarity_threshold: float = 0.7
    rebuild_on_startup: bool = False
    
    class Config:
        """Pydantic configuration."""
        validate_assignment = True


class ValidationConfig(BaseModel):
    """Validation configuration."""
    schema_path: Optional[Path] = None
    strict_mode: bool = True
    auto_fix_common_issues: bool = True
    validate_repository_accuracy: bool = True
    
    class Config:
        """Pydantic configuration."""
        validate_assignment = True


class GenerationConfig(BaseModel):
    """Generation configuration."""
    default_providers: List[str] = Field(default_factory=lambda: ["apt", "brew", "winget"])
    output_directory: Path = Path.cwd() / "saidata"
    backup_existing: bool = True
    parallel_requests: int = 3
    request_timeout: int = 120
    
    class Config:
        """Pydantic configuration."""
        validate_assignment = True


class SaigenConfig(BaseModel):
    """Main saigen configuration."""
    # Core settings
    config_version: str = "0.1.0"
    log_level: LogLevel = LogLevel.INFO
    log_file: Optional[Path] = None
    
    # Component configurations
    llm_providers: Dict[str, LLMConfig] = Field(default_factory=dict)
    repositories: Dict[str, RepositoryConfig] = Field(default_factory=dict)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    rag: RAGConfig = Field(default_factory=RAGConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    generation: GenerationConfig = Field(default_factory=GenerationConfig)
    
    # Advanced settings
    user_agent: str = "saigen/0.1.0"
    max_concurrent_requests: int = 5
    request_timeout: int = 30
    

    
    class Config:
        """Pydantic configuration."""
        validate_assignment = True
        use_enum_values = True
    
    @validator('llm_providers')
    def validate_llm_providers(cls, v):
        """Ensure at least one LLM provider is configured."""
        if not v:
            # Set default OpenAI configuration
            v['openai'] = LLMConfig(
                provider='openai',
                model='gpt-3.5-turbo',
                max_tokens=4000,
                temperature=0.1
            )
        return v
    
    def get_masked_config(self) -> Dict[str, Any]:
        """Return configuration with sensitive data masked."""
        config_dict = self.dict()
        
        # Mask API keys and credentials
        for provider_name, provider_config in config_dict.get('llm_providers', {}).items():
            if 'api_key' in provider_config and provider_config['api_key']:
                provider_config['api_key'] = '***masked***'
        
        for repo_name, repo_config in config_dict.get('repositories', {}).items():
            if 'credentials' in repo_config and repo_config['credentials']:
                repo_config['credentials'] = {k: '***masked***' for k in repo_config['credentials']}
        
        return config_dict