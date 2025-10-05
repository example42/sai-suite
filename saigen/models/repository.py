"""Pydantic models for repository data structures."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class RepositoryPackage(BaseModel):
    """Package information from repository sources."""

    name: str
    version: str
    description: Optional[str] = None
    homepage: Optional[str] = None
    dependencies: Optional[List[str]] = None
    repository_name: str
    platform: str
    architecture: Optional[str] = None
    maintainer: Optional[str] = None
    license: Optional[str] = None
    size: Optional[int] = None
    checksum: Optional[str] = None
    download_url: Optional[str] = None
    source_url: Optional[str] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None
    last_updated: Optional[datetime] = None

    model_config = ConfigDict(validate_assignment=True, extra="allow")


class CacheEntry(BaseModel):
    """Repository cache entry."""

    repository_name: str
    data: List[RepositoryPackage]
    timestamp: datetime
    expires_at: datetime
    checksum: str
    metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(validate_assignment=True)


class RepositoryInfo(BaseModel):
    """Repository information and metadata."""

    name: str
    url: Optional[str] = None
    type: str  # apt, dnf, brew, winget, etc.
    platform: str  # linux, macos, windows
    architecture: Optional[List[str]] = None
    description: Optional[str] = None
    maintainer: Optional[str] = None
    last_sync: Optional[datetime] = None
    package_count: Optional[int] = None
    enabled: bool = True
    priority: int = 1

    model_config = ConfigDict(validate_assignment=True)


class SearchResult(BaseModel):
    """Search result for repository packages."""

    query: str
    packages: List[RepositoryPackage]
    total_results: int
    search_time: float
    repository_sources: List[str]

    model_config = ConfigDict(validate_assignment=True)
