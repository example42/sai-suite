"""
sai - CLI tool for software automation and installation

A command-line interface for managing software using saidata and provider configurations.
"""

__version__ = "0.1.0"
__author__ = "SAI Team"
__email__ = "team@sai.software"

from .models.provider_data import ProviderData
from .models.config import SaiConfig
from .models.saidata import SaiData
from .core.saidata_loader import SaidataLoader, ValidationResult, SaidataNotFoundError
from .utils.config import get_config, get_config_manager
from .utils.errors import SaiError, format_error_for_cli, get_error_suggestions
from .utils.logging import get_logger, setup_root_logging
from .utils.execution_tracker import get_execution_tracker, ExecutionResult

__all__ = [
    "ProviderData",
    "SaiConfig",
    "SaiData",
    "SaidataLoader",
    "ValidationResult",
    "SaidataNotFoundError",
    "get_config",
    "get_config_manager",
    "SaiError",
    "format_error_for_cli",
    "get_error_suggestions",
    "get_logger",
    "setup_root_logging",
    "get_execution_tracker",
    "ExecutionResult",
]