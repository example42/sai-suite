"""Error classes for saigen tool."""


class SaigenError(Exception):
    """Base exception for saigen tool."""


class RepositoryError(SaigenError):
    """Repository data access failed."""


class CacheError(SaigenError):
    """Cache operation failed."""


class ConfigurationError(SaigenError):
    """Configuration error."""


class ValidationError(SaigenError):
    """Validation error."""


class GenerationError(SaigenError):
    """Generation process failed."""


class LLMProviderError(SaigenError):
    """LLM provider communication failed."""


class RAGError(SaigenError):
    """RAG (Retrieval-Augmented Generation) operation failed."""
