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

__all__ = [
    "ProviderData",
    "SaiConfig",
    "SaiData",
    "SaidataLoader",
    "ValidationResult",
    "SaidataNotFoundError",
    "get_config",
    "get_config_manager",
]