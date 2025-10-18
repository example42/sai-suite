"""Version information for SAI."""

try:
    from ._version import version as __version__
except ImportError:
    # Fallback for development installations
    __version__ = "0.1.0-dev"

__title__ = "sai"
__description__ = "SAI Software Management Suite"
__author__ = "SAI Team"
__author_email__ = "team@sai.software"
__license__ = "MIT"
__url__ = "https://sai.software"
__version_info__ = tuple(int(i) for i in __version__.split(".") if i.isdigit())


def get_version() -> str:
    """Get the current version string."""
    return __version__


def get_version_info() -> dict:
    """Get detailed version information."""
    return {
        "version": __version__,
        "title": __title__,
        "description": __description__,
        "author": __author__,
        "author_email": __author_email__,
        "license": __license__,
        "url": __url__,
        "version_info": __version_info__,
    }
