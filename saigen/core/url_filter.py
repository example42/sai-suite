"""Post-LLM URL validation filter for saidata generation."""

import asyncio
import logging
from typing import Dict, Optional, Set
from urllib.parse import urlparse

import aiohttp

from ..models.saidata import SaiData

logger = logging.getLogger(__name__)


class URLValidationFilter:
    """Filter to validate and remove unreachable URLs from generated saidata."""

    def __init__(
        self, timeout: int = 5, max_concurrent: int = 10, user_agent: str = "SAI-URLValidator/1.0"
    ):
        """Initialize URL validation filter.

        Args:
            timeout: Request timeout in seconds
            max_concurrent: Maximum concurrent URL checks
            user_agent: User agent string for requests
        """
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        self.user_agent = user_agent
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers={"User-Agent": self.user_agent},
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._session:
            await self._session.close()
            self._session = None

    async def filter_saidata(self, saidata: SaiData) -> SaiData:
        """Filter out unreachable URLs from saidata.

        Args:
            saidata: Generated saidata to filter

        Returns:
            Filtered saidata with only reachable URLs
        """
        logger.info(f"Starting URL validation for saidata: {saidata.metadata.name}")

        # Extract all URLs from saidata
        urls = self._extract_urls(saidata)

        if not urls:
            logger.debug("No URLs found in saidata")
            return saidata

        logger.debug(f"Found {len(urls)} URLs to validate")

        # Validate URLs
        valid_urls = await self._validate_urls(urls)

        logger.info(f"URL validation complete: {len(valid_urls)}/{len(urls)} URLs are reachable")

        # Filter saidata to keep only valid URLs
        filtered_saidata = self._filter_urls(saidata, valid_urls)

        return filtered_saidata

    def _extract_urls(self, saidata: SaiData) -> Set[str]:
        """Extract all URLs from saidata.

        Args:
            saidata: Saidata to extract URLs from

        Returns:
            Set of unique URLs
        """
        urls = set()

        # Extract from metadata.urls
        if saidata.metadata.urls:
            for field in [
                "website",
                "documentation",
                "source",
                "issues",
                "support",
                "download",
                "changelog",
                "license",
                "sbom",
                "icon",
            ]:
                url = getattr(saidata.metadata.urls, field, None)
                if url and self._is_http_url(url) and not self._has_template_variables(url):
                    urls.add(url)

        # Extract from metadata.security
        if saidata.metadata.security:
            for field in ["vulnerability_disclosure", "sbom_url", "signing_key"]:
                url = getattr(saidata.metadata.security, field, None)
                if url and self._is_http_url(url) and not self._has_template_variables(url):
                    urls.add(url)

        # Extract from packages
        if saidata.packages:
            for package in saidata.packages:
                if (
                    package.download_url
                    and self._is_http_url(package.download_url)
                    and not self._has_template_variables(package.download_url)
                ):
                    urls.add(package.download_url)

        # Extract from sources
        if saidata.sources:
            for source in saidata.sources:
                if (
                    source.url
                    and self._is_http_url(source.url)
                    and not self._has_template_variables(source.url)
                ):
                    urls.add(source.url)

        # Extract from binaries
        if saidata.binaries:
            for binary in saidata.binaries:
                if (
                    binary.url
                    and self._is_http_url(binary.url)
                    and not self._has_template_variables(binary.url)
                ):
                    urls.add(binary.url)

        # Extract from scripts
        if saidata.scripts:
            for script in saidata.scripts:
                if (
                    script.url
                    and self._is_http_url(script.url)
                    and not self._has_template_variables(script.url)
                ):
                    urls.add(script.url)

        # Extract from providers
        if saidata.providers:
            for provider_config in saidata.providers.values():
                # Packages
                if provider_config.packages:
                    for package in provider_config.packages:
                        if (
                            package.download_url
                            and self._is_http_url(package.download_url)
                            and not self._has_template_variables(package.download_url)
                        ):
                            urls.add(package.download_url)

                # Repositories
                if provider_config.repositories:
                    for repo in provider_config.repositories:
                        if (
                            repo.url
                            and self._is_http_url(repo.url)
                            and not self._has_template_variables(repo.url)
                        ):
                            urls.add(repo.url)
                        if (
                            repo.key
                            and self._is_http_url(repo.key)
                            and not self._has_template_variables(repo.key)
                        ):
                            urls.add(repo.key)

                        # Nested packages in repositories
                        if repo.packages:
                            for package in repo.packages:
                                if (
                                    package.download_url
                                    and self._is_http_url(package.download_url)
                                    and not self._has_template_variables(package.download_url)
                                ):
                                    urls.add(package.download_url)

                        # Nested sources in repositories
                        if repo.sources:
                            for source in repo.sources:
                                if (
                                    source.url
                                    and self._is_http_url(source.url)
                                    and not self._has_template_variables(source.url)
                                ):
                                    urls.add(source.url)

                        # Nested binaries in repositories
                        if repo.binaries:
                            for binary in repo.binaries:
                                if (
                                    binary.url
                                    and self._is_http_url(binary.url)
                                    and not self._has_template_variables(binary.url)
                                ):
                                    urls.add(binary.url)

                        # Nested scripts in repositories
                        if repo.scripts:
                            for script in repo.scripts:
                                if (
                                    script.url
                                    and self._is_http_url(script.url)
                                    and not self._has_template_variables(script.url)
                                ):
                                    urls.add(script.url)

                # Package sources
                if provider_config.package_sources:
                    for pkg_source in provider_config.package_sources:
                        if pkg_source.packages:
                            for package in pkg_source.packages:
                                if (
                                    package.download_url
                                    and self._is_http_url(package.download_url)
                                    and not self._has_template_variables(package.download_url)
                                ):
                                    urls.add(package.download_url)

                # Direct sources
                if provider_config.sources:
                    for source in provider_config.sources:
                        if (
                            source.url
                            and self._is_http_url(source.url)
                            and not self._has_template_variables(source.url)
                        ):
                            urls.add(source.url)

                # Direct binaries
                if provider_config.binaries:
                    for binary in provider_config.binaries:
                        if (
                            binary.url
                            and self._is_http_url(binary.url)
                            and not self._has_template_variables(binary.url)
                        ):
                            urls.add(binary.url)

                # Direct scripts
                if provider_config.scripts:
                    for script in provider_config.scripts:
                        if (
                            script.url
                            and self._is_http_url(script.url)
                            and not self._has_template_variables(script.url)
                        ):
                            urls.add(script.url)

        return urls

    def _is_http_url(self, url: str) -> bool:
        """Check if URL is an HTTP/HTTPS URL.

        Args:
            url: URL to check

        Returns:
            True if URL is HTTP/HTTPS
        """
        try:
            parsed = urlparse(url)
            return parsed.scheme in ("http", "https")
        except Exception:
            return False

    def _has_template_variables(self, url: str) -> bool:
        """Check if URL contains template variables.

        Template variables like {{version}}, {{platform}}, and {{architecture}} are used
        in saidata URLs to support dynamic URL generation. These URLs should not be
        validated by making HTTP requests since they are not actual URLs yet - they will
        be resolved at runtime by the SAI execution engine.

        Args:
            url: URL to check

        Returns:
            True if URL contains template variables like {{version}}, {{platform}}, {{architecture}}
        """
        return "{{" in url and "}}" in url

    async def _validate_urls(self, urls: Set[str]) -> Set[str]:
        """Validate URLs by making HTTP requests.

        Args:
            urls: Set of URLs to validate

        Returns:
            Set of valid (reachable) URLs
        """
        if not self._session:
            raise RuntimeError("URLValidationFilter must be used as async context manager")

        # Create semaphore for concurrent request limiting
        semaphore = asyncio.Semaphore(self.max_concurrent)

        # Validate all URLs concurrently
        tasks = [self._check_url(url, semaphore) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect valid URLs
        valid_urls = set()
        for url, result in zip(urls, results):
            if isinstance(result, Exception):
                logger.debug(f"URL validation error for {url}: {result}")
            elif result:
                valid_urls.add(url)

        return valid_urls

    async def _check_url(self, url: str, semaphore: asyncio.Semaphore) -> bool:
        """Check if a single URL is reachable.

        Args:
            url: URL to check
            semaphore: Semaphore for concurrent request limiting

        Returns:
            True if URL is reachable
        """
        async with semaphore:
            try:
                async with self._session.head(url, allow_redirects=True) as response:
                    # Consider 2xx and 3xx as valid
                    is_valid = 200 <= response.status < 400
                    if is_valid:
                        logger.debug(f"URL valid: {url} (status: {response.status})")
                    else:
                        logger.warning(f"URL invalid: {url} (status: {response.status})")
                    return is_valid
            except asyncio.TimeoutError:
                logger.warning(f"URL timeout: {url}")
                return False
            except aiohttp.ClientError as e:
                logger.warning(f"URL unreachable: {url} ({type(e).__name__})")
                return False
            except Exception as e:
                logger.warning(f"URL check failed: {url} ({e})")
                return False

    def _filter_urls(self, saidata: SaiData, valid_urls: Set[str]) -> SaiData:
        """Filter saidata to keep only valid URLs.

        Args:
            saidata: Original saidata
            valid_urls: Set of valid URLs

        Returns:
            Filtered saidata
        """
        # Create a copy to avoid modifying the original
        data_dict = saidata.model_dump()

        # Filter metadata.urls
        if data_dict.get("metadata", {}).get("urls"):
            urls_dict = data_dict["metadata"]["urls"]
            for field in list(urls_dict.keys()):
                url = urls_dict[field]
                if (
                    url
                    and self._is_http_url(url)
                    and not self._has_template_variables(url)
                    and url not in valid_urls
                ):
                    logger.debug(f"Filtering out invalid URL from metadata.urls.{field}: {url}")
                    urls_dict[field] = None

        # Filter metadata.security
        if data_dict.get("metadata", {}).get("security"):
            security_dict = data_dict["metadata"]["security"]
            for field in ["vulnerability_disclosure", "sbom_url", "signing_key"]:
                url = security_dict.get(field)
                if (
                    url
                    and self._is_http_url(url)
                    and not self._has_template_variables(url)
                    and url not in valid_urls
                ):
                    logger.debug(f"Filtering out invalid URL from metadata.security.{field}: {url}")
                    security_dict[field] = None

        # Filter packages
        if data_dict.get("packages"):
            for package in data_dict["packages"]:
                if package.get("download_url"):
                    url = package["download_url"]
                    if (
                        self._is_http_url(url)
                        and not self._has_template_variables(url)
                        and url not in valid_urls
                    ):
                        logger.debug(
                            f"Filtering out invalid download_url from package {
                                package['name']}: {url}")
                        package["download_url"] = None

        # Filter sources
        if data_dict.get("sources"):
            data_dict["sources"] = [
                source
                for source in data_dict["sources"]
                if not self._is_http_url(source["url"])
                or self._has_template_variables(source["url"])
                or source["url"] in valid_urls
            ]

        # Filter binaries
        if data_dict.get("binaries"):
            data_dict["binaries"] = [
                binary
                for binary in data_dict["binaries"]
                if not self._is_http_url(binary["url"])
                or self._has_template_variables(binary["url"])
                or binary["url"] in valid_urls
            ]

        # Filter scripts
        if data_dict.get("scripts"):
            data_dict["scripts"] = [
                script
                for script in data_dict["scripts"]
                if not self._is_http_url(script["url"])
                or self._has_template_variables(script["url"])
                or script["url"] in valid_urls
            ]

        # Filter providers
        if data_dict.get("providers"):
            for provider_name, provider_config in data_dict["providers"].items():
                self._filter_provider_config(provider_config, valid_urls)

        # Reconstruct SaiData from filtered dict
        return SaiData(**data_dict)

    def _filter_provider_config(self, provider_config: Dict, valid_urls: Set[str]) -> None:
        """Filter URLs in provider configuration (in-place).

        Args:
            provider_config: Provider configuration dict
            valid_urls: Set of valid URLs
        """
        # Filter packages
        if provider_config.get("packages"):
            for package in provider_config["packages"]:
                if package.get("download_url"):
                    url = package["download_url"]
                    if (
                        self._is_http_url(url)
                        and not self._has_template_variables(url)
                        and url not in valid_urls
                    ):
                        logger.debug(
                            f"Filtering out invalid download_url from provider package: {url}"
                        )
                        package["download_url"] = None

        # Filter repositories
        if provider_config.get("repositories"):
            for repo in provider_config["repositories"]:
                # Repository URL
                if repo.get("url"):
                    url = repo["url"]
                    if (
                        self._is_http_url(url)
                        and not self._has_template_variables(url)
                        and url not in valid_urls
                    ):
                        logger.debug(f"Filtering out invalid repository URL: {url}")
                        repo["url"] = None

                # Repository key
                if repo.get("key"):
                    url = repo["key"]
                    if (
                        self._is_http_url(url)
                        and not self._has_template_variables(url)
                        and url not in valid_urls
                    ):
                        logger.debug(f"Filtering out invalid repository key URL: {url}")
                        repo["key"] = None

                # Nested packages
                if repo.get("packages"):
                    for package in repo["packages"]:
                        if package.get("download_url"):
                            url = package["download_url"]
                            if (
                                self._is_http_url(url)
                                and not self._has_template_variables(url)
                                and url not in valid_urls
                            ):
                                logger.debug(
                                    f"Filtering out invalid download_url from repo package: {url}"
                                )
                                package["download_url"] = None

                # Nested sources
                if repo.get("sources"):
                    repo["sources"] = [
                        source
                        for source in repo["sources"]
                        if not self._is_http_url(source["url"])
                        or self._has_template_variables(source["url"])
                        or source["url"] in valid_urls
                    ]

                # Nested binaries
                if repo.get("binaries"):
                    repo["binaries"] = [
                        binary
                        for binary in repo["binaries"]
                        if not self._is_http_url(binary["url"])
                        or self._has_template_variables(binary["url"])
                        or binary["url"] in valid_urls
                    ]

                # Nested scripts
                if repo.get("scripts"):
                    repo["scripts"] = [
                        script
                        for script in repo["scripts"]
                        if not self._is_http_url(script["url"])
                        or self._has_template_variables(script["url"])
                        or script["url"] in valid_urls
                    ]

        # Filter package sources
        if provider_config.get("package_sources"):
            for pkg_source in provider_config["package_sources"]:
                if pkg_source.get("packages"):
                    for package in pkg_source["packages"]:
                        if package.get("download_url"):
                            url = package["download_url"]
                            if (
                                self._is_http_url(url)
                                and not self._has_template_variables(url)
                                and url not in valid_urls
                            ):
                                logger.debug(
                                    f"Filtering out invalid download_url from package source: {url}"
                                )
                                package["download_url"] = None

        # Filter direct sources
        if provider_config.get("sources"):
            provider_config["sources"] = [
                source
                for source in provider_config["sources"]
                if not self._is_http_url(source["url"])
                or self._has_template_variables(source["url"])
                or source["url"] in valid_urls
            ]

        # Filter direct binaries
        if provider_config.get("binaries"):
            provider_config["binaries"] = [
                binary
                for binary in provider_config["binaries"]
                if not self._is_http_url(binary["url"])
                or self._has_template_variables(binary["url"])
                or binary["url"] in valid_urls
            ]

        # Filter direct scripts
        if provider_config.get("scripts"):
            provider_config["scripts"] = [
                script
                for script in provider_config["scripts"]
                if not self._is_http_url(script["url"])
                or self._has_template_variables(script["url"])
                or script["url"] in valid_urls
            ]
