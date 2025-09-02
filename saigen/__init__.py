"""
saigen - AI-powered saidata generation tool

A comprehensive Python tool for generating, validating, and managing 
software metadata in YAML format following the saidata JSON schema specification.
"""

__version__ = "0.1.0"
__author__ = "SAI Team"
__email__ = "team@sai.software"

from .models.saidata import SaiData
from .models.repository import RepositoryPackage
from .models.generation import GenerationRequest, GenerationResult

__all__ = [
    "SaiData",
    "RepositoryPackage", 
    "GenerationRequest",
    "GenerationResult",
]