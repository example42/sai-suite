"""Version information for SAIGEN."""

try:
    from sai._version import version as __version__
except ImportError:
    # Fallback for development installations
    __version__ = "0.1.0-dev"

__title__ = "saigen"
__description__ = "SAI data Generation Tool"
__author__ = "SAI Team"
__author_email__ = "team@sai.software"
__license__ = "MIT"
__url__ = "https://sai.software"
__version_info__ = tuple(int(i) for i in __version__.split(".") if i.isdigit())


def get_version() -> str:
    """Get the current version string."""
    return __version__
