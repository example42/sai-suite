"""Tests for URL validation filter."""

from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from saigen.core.url_filter import URLValidationFilter
from saigen.models.saidata import (
    Binary,
    BuildSystem,
    Metadata,
    Package,
    ProviderConfig,
    Repository,
    SaiData,
    Script,
    SecurityMetadata,
    Source,
    Urls,
)


@pytest.fixture
def sample_saidata():
    """Create sample saidata with various URLs."""
    return SaiData(
        version="0.3",
        metadata=Metadata(
            name="test-software",
            description="Test software",
            urls=Urls(
                website="https://example.com",
                documentation="https://docs.example.com",
                source="https://github.com/example/repo",
            ),
            security=SecurityMetadata(
                sbom_url="https://example.com/sbom.json", signing_key="https://example.com/key.asc"
            ),
        ),
        packages=[
            Package(
                name="pkg1", package_name="test-pkg", download_url="https://example.com/pkg.tar.gz"
            )
        ],
        sources=[
            Source(
                name="source1",
                url="https://example.com/source.tar.gz",
                build_system=BuildSystem.CMAKE,
            )
        ],
        binaries=[Binary(name="binary1", url="https://example.com/binary.tar.gz")],
        scripts=[Script(name="script1", url="https://example.com/install.sh")],
    )


@pytest.mark.asyncio
async def test_url_filter_initialization():
    """Test URL filter initialization."""
    async with URLValidationFilter(timeout=10, max_concurrent=5) as filter:
        assert filter.timeout == 10
        assert filter.max_concurrent == 5
        assert filter._session is not None


@pytest.mark.asyncio
async def test_extract_urls(sample_saidata):
    """Test URL extraction from saidata."""
    async with URLValidationFilter() as filter:
        urls = filter._extract_urls(sample_saidata)

        # Should extract all HTTP/HTTPS URLs
        assert "https://example.com" in urls
        assert "https://docs.example.com" in urls
        assert "https://github.com/example/repo" in urls
        assert "https://example.com/sbom.json" in urls
        assert "https://example.com/key.asc" in urls
        assert "https://example.com/pkg.tar.gz" in urls
        assert "https://example.com/source.tar.gz" in urls
        assert "https://example.com/binary.tar.gz" in urls
        assert "https://example.com/install.sh" in urls

        # Should have 9 unique URLs
        assert len(urls) == 9


@pytest.mark.asyncio
async def test_is_http_url():
    """Test HTTP URL detection."""
    async with URLValidationFilter() as filter:
        assert filter._is_http_url("https://example.com")
        assert filter._is_http_url("http://example.com")
        assert not filter._is_http_url("ftp://example.com")
        assert not filter._is_http_url("git://example.com")
        assert not filter._is_http_url("/local/path")
        assert not filter._is_http_url("not-a-url")


@pytest.mark.asyncio
async def test_check_url_valid():
    """Test checking a valid URL."""
    async with URLValidationFilter() as filter:
        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.__aenter__.return_value = mock_response
        mock_response.__aexit__.return_value = None

        filter._session.head = MagicMock(return_value=mock_response)

        semaphore = AsyncMock()
        semaphore.__aenter__.return_value = None
        semaphore.__aexit__.return_value = None

        result = await filter._check_url("https://example.com", semaphore)
        assert result is True


@pytest.mark.asyncio
async def test_check_url_invalid_status():
    """Test checking a URL with invalid status."""
    async with URLValidationFilter() as filter:
        # Mock 404 response
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.__aenter__.return_value = mock_response
        mock_response.__aexit__.return_value = None

        filter._session.head = MagicMock(return_value=mock_response)

        semaphore = AsyncMock()
        semaphore.__aenter__.return_value = None
        semaphore.__aexit__.return_value = None

        result = await filter._check_url("https://example.com/notfound", semaphore)
        assert result is False


@pytest.mark.asyncio
async def test_check_url_timeout():
    """Test checking a URL that times out."""
    async with URLValidationFilter() as filter:
        # Mock timeout
        async def mock_head(*args, **kwargs):
            raise aiohttp.ClientTimeout()

        filter._session.head = mock_head

        semaphore = AsyncMock()
        semaphore.__aenter__.return_value = None
        semaphore.__aexit__.return_value = None

        result = await filter._check_url("https://slow.example.com", semaphore)
        assert result is False


@pytest.mark.asyncio
async def test_filter_saidata_all_valid(sample_saidata):
    """Test filtering when all URLs are valid."""
    async with URLValidationFilter() as filter:
        # Mock all URLs as valid
        filter._validate_urls = AsyncMock(
            return_value={
                "https://example.com",
                "https://docs.example.com",
                "https://github.com/example/repo",
                "https://example.com/sbom.json",
                "https://example.com/key.asc",
                "https://example.com/pkg.tar.gz",
                "https://example.com/source.tar.gz",
                "https://example.com/binary.tar.gz",
                "https://example.com/install.sh",
            }
        )

        filtered = await filter.filter_saidata(sample_saidata)

        # All URLs should remain
        assert filtered.metadata.urls.website == "https://example.com"
        assert filtered.metadata.urls.documentation == "https://docs.example.com"
        assert filtered.metadata.urls.source == "https://github.com/example/repo"
        assert filtered.metadata.security.sbom_url == "https://example.com/sbom.json"
        assert len(filtered.sources) == 1
        assert len(filtered.binaries) == 1
        assert len(filtered.scripts) == 1


@pytest.mark.asyncio
async def test_filter_saidata_some_invalid(sample_saidata):
    """Test filtering when some URLs are invalid."""
    async with URLValidationFilter() as filter:
        # Mock only some URLs as valid
        filter._validate_urls = AsyncMock(
            return_value={
                "https://example.com",
                "https://github.com/example/repo",
                "https://example.com/source.tar.gz",
            }
        )

        filtered = await filter.filter_saidata(sample_saidata)

        # Valid URLs should remain
        assert filtered.metadata.urls.website == "https://example.com"
        assert filtered.metadata.urls.source == "https://github.com/example/repo"

        # Invalid URLs should be filtered
        assert filtered.metadata.urls.documentation is None
        assert filtered.metadata.security.sbom_url is None
        assert filtered.metadata.security.signing_key is None
        assert filtered.packages[0].download_url is None

        # Sources with valid URL should remain
        assert len(filtered.sources) == 1

        # Binaries and scripts with invalid URLs should be removed
        assert len(filtered.binaries) == 0
        assert len(filtered.scripts) == 0


@pytest.mark.asyncio
async def test_filter_saidata_no_urls():
    """Test filtering saidata with no URLs."""
    saidata = SaiData(
        version="0.3",
        metadata=Metadata(name="test-software", description="Test software without URLs"),
    )

    async with URLValidationFilter() as filter:
        filtered = await filter.filter_saidata(saidata)

        # Should return unchanged
        assert filtered.metadata.name == "test-software"
        assert filtered.metadata.urls is None


@pytest.mark.asyncio
async def test_filter_provider_configs():
    """Test filtering URLs in provider configurations."""
    saidata = SaiData(
        version="0.3",
        metadata=Metadata(name="test-software", description="Test software"),
        providers={
            "apt": ProviderConfig(
                repositories=[
                    Repository(
                        name="repo1",
                        url="https://repo.example.com",
                        key="https://repo.example.com/key.asc",
                        sources=[
                            Source(
                                name="source1",
                                url="https://repo.example.com/source.tar.gz",
                                build_system=BuildSystem.CMAKE,
                            )
                        ],
                    )
                ]
            )
        },
    )

    async with URLValidationFilter() as filter:
        # Mock only repo URL as valid
        filter._validate_urls = AsyncMock(return_value={"https://repo.example.com"})

        filtered = await filter.filter_saidata(saidata)

        # Valid repo URL should remain
        assert filtered.providers["apt"].repositories[0].url == "https://repo.example.com"

        # Invalid key URL should be filtered
        assert filtered.providers["apt"].repositories[0].key is None

        # Invalid source should be removed
        assert len(filtered.providers["apt"].repositories[0].sources) == 0


@pytest.mark.asyncio
async def test_concurrent_url_validation():
    """Test that URLs are validated concurrently."""
    urls = {f"https://example{i}.com" for i in range(20)}

    async with URLValidationFilter(max_concurrent=5) as filter:
        # Mock check_url to track calls
        call_count = 0

        async def mock_check_url(url, semaphore):
            nonlocal call_count
            call_count += 1
            return True

        filter._check_url = mock_check_url

        valid_urls = await filter._validate_urls(urls)

        # All URLs should be validated
        assert len(valid_urls) == 20
        assert call_count == 20
