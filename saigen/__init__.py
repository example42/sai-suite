"""
saigen - AI-powered saidata generation tool

A comprehensive Python tool for generating, validating, and managing
software metadata in YAML format following the saidata JSON schema specification.
"""

__version__ = "0.1.0"
__author__ = "SAI Team"
__email__ = "team@sai.software"

from .models.generation import GenerationRequest, GenerationResult
from .models.repository import RepositoryPackage
from .models.saidata import SaiData

__all__ = [
    "SaiData",
    "RepositoryPackage",
    "GenerationRequest",
    "GenerationResult",
]
