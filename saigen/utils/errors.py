"""Error classes for saigen tool."""


class SaigenError(Exception):
    """Base exception for saigen tool."""
    pass


class RepositoryError(SaigenError):
    """Repository data access failed."""
    pass


class CacheError(SaigenError):
    """Cache operation failed."""
    pass


class ConfigurationError(SaigenError):
    """Configuration error."""
    pass


class ValidationError(SaigenError):
    """Validation error."""
    pass


class GenerationError(SaigenError):
    """Generation process failed."""
    pass


class LLMProviderError(SaigenError):
    """LLM provider communication failed."""
    pass


class RAGError(SaigenError):
    """RAG (Retrieval-Augmented Generation) operation failed."""
    pass