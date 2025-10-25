"""Universal repository downloader with configurable parsing."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    pass

    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

from saigen.models.repository import RepositoryInfo, RepositoryPackage
from saigen.repositories.downloaders.base import BaseRepositoryDownloader
from saigen.repositories.parsers import ParserRegistry
from saigen.utils.errors import RepositoryError

logger = logging.getLogger(__name__)


class UniversalRepositoryDownloader(BaseRepositoryDownloader):
    """Universal repository downloader with YAML-driven configuration."""

    def __init__(
        self,
        repository_info: RepositoryInfo,
        config: Dict[str, Any],
        parser_registry: ParserRegistry,
    ):
        """Initialize universal downloader.

        Args:
            repository_info: Repository metadata
            config: Full repository configuration from YAML
            parser_registry: Registry of parsing functions
        """
        super().__init__(repository_info, config)
        self.full_config = config
        self.parser_registry = parser_registry
        self._session = None

        # Extract configuration sections
        self.endpoints = config.get("endpoints", {})
        self.parsing_config = config.get("parsing", {})
        self.cache_config = config.get("cache", {})
        self.limits_config = config.get("limits", {})
        self.auth_config = config.get("auth", {})

    async def _get_session(self):
        """Get or create HTTP session with configuration."""
        if not AIOHTTP_AVAILABLE:
            raise RepositoryError("aiohttp is required for network operations")

        if not self._session:
            import aiohttp

            # Configure timeout
            timeout_seconds = self.limits_config.get("timeout_seconds", 300)
            timeout = aiohttp.ClientTimeout(total=timeout_seconds)

            # Configure connection pooling
            concurrent_requests = self.limits_config.get("concurrent_requests", 10)
            connector = aiohttp.TCPConnector(
                limit=concurrent_requests * 2,
                limit_per_host=concurrent_requests,
                ttl_dns_cache=300,
                use_dns_cache=True,
                keepalive_timeout=30,
                enable_cleanup_closed=True,
            )

            # Configure headers
            headers = {"User-Agent": "saigen/1.0.0"}

            # Add authentication headers
            auth_headers = self._get_auth_headers()
            if auth_headers:
                headers.update(auth_headers)

            self._session = aiohttp.ClientSession(
                timeout=timeout, connector=connector, headers=headers
            )

        return self._session

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers based on configuration."""
        auth_type = self.auth_config.get("type", "none")
        headers = {}

        if auth_type == "bearer":
            token = self.auth_config.get("token")
            if token:
                headers["Authorization"] = f"Bearer {token}"

        elif auth_type == "api_key":
            api_key = self.auth_config.get("api_key")
            header_name = self.auth_config.get("api_key_header", "X-API-Key")
            if api_key:
                headers[header_name] = api_key

        return headers

    async def download_package_list(self) -> List[RepositoryPackage]:
        """Download and parse package list from repository."""
        packages_url = self.endpoints.get("packages")
        if not packages_url:
            raise RepositoryError(
                f"No packages URL configured for repository {self.repository_info.name}"
            )

        try:
            session = await self._get_session()

            # Support URL templates with architecture substitution
            url = self._resolve_url_template(packages_url)

            packages = await self._download_and_parse(session, url)

            logger.info(f"Downloaded {len(packages)} packages from {self.repository_info.name}")
            return packages

        except Exception as e:
            # Close session on error to prevent unclosed session warnings
            if self._session:
                try:
                    await self._session.close()
                    self._session = None
                except BaseException:
                    pass
            raise RepositoryError(
                f"Failed to download package list from {self.repository_info.name}: {str(e)}"
            )

    def _resolve_url_template(self, url_template: str) -> str:
        """Resolve URL template with configuration values."""
        # Get architecture - use first one if multiple
        architecture = self.repository_info.architecture
        if isinstance(architecture, list) and architecture:
            arch = architecture[0]
        elif isinstance(architecture, str):
            arch = architecture
        else:
            arch = "amd64"  # Default

        # Replace template variables
        url = url_template.replace("{arch}", arch)
        url = url.replace("{architecture}", arch)

        # Add other template variables as needed
        distribution = self.full_config.get("distribution", [])
        if distribution:
            url = url.replace("{release}", distribution[0])
            url = url.replace("{distribution}", distribution[0])

        return url

    async def _download_and_parse(self, session, url: str) -> List[RepositoryPackage]:
        """Download and parse packages from a URL."""
        logger.debug(f"Downloading from: {url}")

        # Security: Validate URL
        if not url.startswith(("http://", "https://")):
            raise RepositoryError(f"Invalid URL scheme: {url}")

        async with session.get(url, ssl=True) as response:
            if response.status != 200:
                raise RepositoryError(f"HTTP {response.status} from {url}")

            # Check content length
            max_size_mb = self.limits_config.get("max_response_size_mb", 200)
            content_length = response.headers.get("content-length")
            if content_length and int(content_length) > max_size_mb * 1024 * 1024:
                raise RepositoryError(f"Response too large: {content_length} bytes from {url}")

            # Read content
            content = await response.read()

            # Parse content
            return await self._parse_content(content, response.headers)

    async def _parse_content(
        self, content: bytes, headers: Dict[str, str]
    ) -> List[RepositoryPackage]:
        """Parse content using configured parser."""
        format_type = self.parsing_config.get("format", "json")

        # Handle compression
        content = self._decompress_content(content, headers)

        # Convert to text
        encoding = self.parsing_config.get("encoding", "utf-8")
        try:
            text_content = content.decode(encoding, errors="ignore")
        except UnicodeDecodeError as e:
            raise RepositoryError(f"Failed to decode content with {encoding}: {e}")

        # Get parser function
        parser_func = self.parser_registry.get_parser(format_type)
        if not parser_func:
            raise RepositoryError(f"No parser available for format: {format_type}")

        # Parse content
        try:
            packages = await parser_func(
                content=text_content,
                config=self.parsing_config,
                repository_info=self.repository_info,
            )
            return packages
        except Exception as e:
            raise RepositoryError(f"Failed to parse content: {e}")

    def _decompress_content(self, content: bytes, headers: Dict[str, str]) -> bytes:
        """Decompress content based on configuration or headers."""
        compression = self.parsing_config.get("compression", "none")

        # Auto-detect compression from headers
        if compression == "none":
            content_encoding = headers.get("content-encoding", "").lower()
            if content_encoding == "gzip":
                compression = "gzip"
            elif content_encoding in ["bzip2", "bz2"]:
                compression = "bzip2"
            elif content_encoding in ["br", "brotli"]:
                compression = "brotli"

        # Decompress if needed
        if compression == "gzip":
            import gzip

            try:
                # Try to decompress, but if it fails, check if content is already decompressed
                content = gzip.decompress(content)
            except (gzip.BadGzipFile, OSError) as e:
                # Content might not be gzipped - check if it looks like valid text/JSON
                try:
                    # Try to decode as UTF-8 to see if it's already decompressed
                    content.decode("utf-8", errors="strict")
                    # If successful, content is already decompressed, just return it
                    logger.debug(f"Content appears to be already decompressed despite gzip config")
                    return content
                except UnicodeDecodeError:
                    # Not valid UTF-8, so it's probably a real gzip error
                    raise RepositoryError(f"Failed to decompress gzip content: {e}")

        elif compression == "bzip2":
            import bz2

            try:
                content = bz2.decompress(content)
            except Exception as e:
                # Try to handle already decompressed content
                try:
                    content.decode("utf-8", errors="strict")
                    logger.debug(f"Content appears to be already decompressed despite bzip2 config")
                    return content
                except UnicodeDecodeError:
                    raise RepositoryError(f"Failed to decompress bzip2 content: {e}")

        elif compression == "xz":
            import lzma

            try:
                content = lzma.decompress(content)
            except Exception as e:
                # Try to handle already decompressed content
                try:
                    content.decode("utf-8", errors="strict")
                    logger.debug(f"Content appears to be already decompressed despite xz config")
                    return content
                except UnicodeDecodeError:
                    raise RepositoryError(f"Failed to decompress xz content: {e}")

        elif compression == "brotli":
            try:
                import brotli
            except ImportError:
                raise RepositoryError(
                    f"Brotli compression is required for {self.repository_info.name} but the 'brotli' "
                    "package is not installed. Install it with: pip install brotli"
                )

            try:
                content = brotli.decompress(content)
            except Exception as e:
                # Try to handle already decompressed content
                try:
                    content.decode("utf-8", errors="strict")
                    logger.debug(f"Content appears to be already decompressed despite brotli config")
                    return content
                except UnicodeDecodeError:
                    raise RepositoryError(f"Failed to decompress brotli content: {e}")

        return content

    async def search_package(self, name: str) -> List[RepositoryPackage]:
        """Search for specific package."""
        search_url = self.endpoints.get("search")

        if search_url:
            # Use dedicated search endpoint
            try:
                session = await self._get_session()
                url = search_url.replace("{query}", name).replace("{package}", name)
                packages = await self._download_and_parse(session, url)

                # Filter results to match search query
                name_lower = name.lower()
                matching_packages = []
                for package in packages:
                    if name_lower in package.name.lower() or (
                        package.description and name_lower in package.description.lower()
                    ):
                        matching_packages.append(package)

                return matching_packages

            except Exception as e:
                logger.debug(f"Search endpoint failed for {name}: {e}")
                # Fall back to full list search

        # Fall back to downloading all packages and filtering
        try:
            all_packages = await self.download_package_list()

            name_lower = name.lower()
            matching_packages = []

            for package in all_packages:
                if name_lower in package.name.lower() or (
                    package.description and name_lower in package.description.lower()
                ):
                    matching_packages.append(package)

            return matching_packages

        except Exception as e:
            logger.error(f"Failed to search packages in {self.repository_info.name}: {e}")
            return []

    async def get_package_details(
        self, name: str, version: Optional[str] = None
    ) -> Optional[RepositoryPackage]:
        """Get detailed information for a specific package."""
        info_url = self.endpoints.get("info")

        if info_url:
            # Use dedicated info endpoint
            try:
                session = await self._get_session()
                url = info_url.replace("{package}", name)
                if version:
                    url = url.replace("{version}", version)

                packages = await self._download_and_parse(session, url)

                # Return first matching package
                for package in packages:
                    if package.name.lower() == name.lower():
                        if version is None or package.version == version:
                            return package

                return packages[0] if packages else None

            except Exception as e:
                logger.debug(f"Info endpoint failed for {name}: {e}")

        # Fall back to search
        packages = await self.search_package(name)

        # Find exact match
        for package in packages:
            if package.name.lower() == name.lower():
                if version is None or package.version == version:
                    return package

        # Return first match if no exact match
        return packages[0] if packages else None

    async def is_available(self) -> bool:
        """Check if repository is available."""
        try:
            session = await self._get_session()

            # Test with a simple HEAD request to packages URL
            packages_url = self.endpoints.get("packages")
            if not packages_url:
                return False

            url = self._resolve_url_template(packages_url)

            # Use a shorter timeout for availability checks
            timeout = session.timeout.total if session.timeout else 30
            short_timeout = min(timeout, 10)  # Max 10 seconds for availability check

            async with session.head(url, ssl=True, timeout=short_timeout) as response:
                return response.status == 200

        except Exception as e:
            logger.debug(f"Repository {self.repository_info.name} is not available: {e}")
            # Close session on error to prevent unclosed session warnings
            if self._session:
                try:
                    await self._session.close()
                    self._session = None
                except BaseException:
                    pass
            return False

    async def get_repository_metadata(self) -> Dict[str, Any]:
        """Get repository metadata and statistics."""
        try:
            packages = await self.download_package_list()

            # Calculate statistics
            total_packages = len(packages)

            # Count packages by category if available
            categories = {}
            for package in packages:
                category = package.category or "unknown"
                categories[category] = categories.get(category, 0) + 1

            return {
                "package_count": total_packages,
                "categories": categories,
                "last_updated": datetime.utcnow(),
                "repository_type": self.repository_info.type,
                "platform": self.repository_info.platform,
                "architecture": self.repository_info.architecture,
                "enabled": self.repository_info.enabled,
                "priority": self.repository_info.priority,
            }

        except Exception as e:
            return {
                "error": str(e),
                "last_updated": datetime.utcnow(),
                "repository_type": self.repository_info.type,
                "platform": self.repository_info.platform,
            }

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._session:
            try:
                await self._session.close()
            except Exception as e:
                logger.debug(f"Error closing session: {e}")
            finally:
                self._session = None
        await super().__aexit__(exc_type, exc_val, exc_tb)

    async def close(self):
        """Explicitly close the session."""
        if self._session:
            try:
                await self._session.close()
            except Exception as e:
                logger.debug(f"Error closing session: {e}")
            finally:
                self._session = None
