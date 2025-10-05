"""Tests for RAG indexer functionality."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from saigen.models.repository import RepositoryPackage
from saigen.models.saidata import Metadata, SaiData
from saigen.repositories.indexer import RAGContextBuilder, RAGIndexer
from saigen.utils.errors import RAGError


class TestRAGIndexer:
    """Test RAG indexer functionality."""

    @pytest.fixture
    def temp_index_dir(self):
        """Create temporary directory for index storage."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def sample_packages(self):
        """Create sample repository packages for testing."""
        return [
            RepositoryPackage(
                name="nginx",
                version="1.20.1",
                description="High-performance HTTP server and reverse proxy",
                repository_name="apt",
                platform="linux",
                category="web-server",
                tags=["http", "server", "proxy"],
                homepage="https://nginx.org",
                maintainer="nginx team",
            ),
            RepositoryPackage(
                name="apache2",
                version="2.4.41",
                description="Apache HTTP Server",
                repository_name="apt",
                platform="linux",
                category="web-server",
                tags=["http", "server"],
                homepage="https://httpd.apache.org",
            ),
            RepositoryPackage(
                name="nginx",
                version="1.21.0",
                description="HTTP and reverse proxy server",
                repository_name="brew",
                platform="macos",
                category="web-server",
                homepage="https://nginx.org",
            ),
        ]

    @pytest.fixture
    def sample_saidata(self):
        """Create sample saidata for testing."""
        return [
            SaiData(
                version="0.2",
                metadata=Metadata(
                    name="nginx",
                    display_name="NGINX",
                    description="High-performance web server",
                    category="web-server",
                    tags=["http", "server", "proxy"],
                ),
            ),
            SaiData(
                version="0.2",
                metadata=Metadata(
                    name="apache",
                    display_name="Apache HTTP Server",
                    description="Popular web server",
                    category="web-server",
                    tags=["http", "server"],
                ),
            ),
        ]

    def test_rag_not_available_error(self, temp_index_dir):
        """Test RAGError when dependencies not available."""
        with patch("saigen.repositories.indexer.RAG_AVAILABLE", False):
            with pytest.raises(RAGError, match="RAG dependencies not available"):
                RAGIndexer(temp_index_dir)

    @pytest.mark.skipif(
        not pytest.importorskip("sentence_transformers", reason="RAG dependencies not available"),
        reason="RAG dependencies not available",
    )
    def test_indexer_initialization(self, temp_index_dir):
        """Test RAG indexer initialization."""
        indexer = RAGIndexer(temp_index_dir)

        assert indexer.index_dir == temp_index_dir
        assert indexer.model_name == "all-MiniLM-L6-v2"
        assert indexer.max_sequence_length == 512
        assert temp_index_dir.exists()

    @pytest.mark.skipif(
        not pytest.importorskip("sentence_transformers", reason="RAG dependencies not available"),
        reason="RAG dependencies not available",
    )
    def test_create_package_text(self, temp_index_dir, sample_packages):
        """Test package text creation for embedding."""
        indexer = RAGIndexer(temp_index_dir)

        package = sample_packages[0]  # nginx package
        text = indexer._create_package_text(package)

        assert "nginx" in text
        assert "High-performance HTTP server" in text
        assert "web-server" in text
        assert "http server proxy" in text
        assert "repository: apt" in text
        assert "platform: linux" in text

    @pytest.mark.skipif(
        not pytest.importorskip("sentence_transformers", reason="RAG dependencies not available"),
        reason="RAG dependencies not available",
    )
    def test_create_saidata_text(self, temp_index_dir, sample_saidata):
        """Test saidata text creation for embedding."""
        indexer = RAGIndexer(temp_index_dir)

        saidata = sample_saidata[0]  # nginx saidata
        text = indexer._create_saidata_text(saidata)

        assert "nginx" in text
        assert "NGINX" in text
        assert "High-performance web server" in text
        assert "category: web-server" in text
        assert "tags: http server proxy" in text

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not pytest.importorskip("sentence_transformers", reason="RAG dependencies not available"),
        reason="RAG dependencies not available",
    )
    async def test_index_repository_data(self, temp_index_dir, sample_packages):
        """Test indexing repository data."""
        indexer = RAGIndexer(temp_index_dir)

        # Mock the sentence transformer to avoid downloading models in tests
        with patch.object(indexer, "_get_model") as mock_get_model:
            mock_model = Mock()
            mock_model.encode.return_value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]]
            mock_get_model.return_value = mock_model

            # Mock FAISS operations
            with patch("saigen.repositories.indexer.faiss") as mock_faiss:
                mock_index = Mock()
                mock_faiss.IndexFlatIP.return_value = mock_index
                mock_faiss.normalize_L2 = Mock()
                mock_faiss.write_index = Mock()

                await indexer.index_repository_data(sample_packages)

                # Verify model was called
                mock_get_model.assert_called_once()
                mock_model.encode.assert_called_once()

                # Verify FAISS operations
                mock_faiss.IndexFlatIP.assert_called_once()
                mock_index.add.assert_called_once()
                mock_faiss.write_index.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not pytest.importorskip("sentence_transformers", reason="RAG dependencies not available"),
        reason="RAG dependencies not available",
    )
    async def test_search_similar_packages(self, temp_index_dir, sample_packages):
        """Test semantic search for similar packages."""
        indexer = RAGIndexer(temp_index_dir)

        # Mock the model and index
        with patch.object(indexer, "_get_model") as mock_get_model, patch.object(
            indexer, "_load_package_index"
        ) as mock_load_index:
            mock_model = Mock()
            mock_model.encode.return_value = [[0.1, 0.2, 0.3]]
            mock_get_model.return_value = mock_model

            # Mock loaded index
            mock_index = Mock()
            mock_index.search.return_value = ([[0.8, 0.6]], [[0, 1]])
            indexer._package_index = mock_index

            # Mock metadata
            indexer._package_metadata = [
                {
                    "name": "nginx",
                    "version": "1.20.1",
                    "description": "HTTP server",
                    "repository_name": "apt",
                    "platform": "linux",
                    "category": "web-server",
                    "tags": ["http", "server"],
                    "homepage": "https://nginx.org",
                    "maintainer": "nginx team",
                    "license": "BSD",
                    "last_updated": None,
                },
                {
                    "name": "apache2",
                    "version": "2.4.41",
                    "description": "Apache server",
                    "repository_name": "apt",
                    "platform": "linux",
                    "category": "web-server",
                    "tags": ["http", "server"],
                    "homepage": "https://httpd.apache.org",
                    "maintainer": None,
                    "license": None,
                    "last_updated": None,
                },
            ]

            with patch("saigen.repositories.indexer.faiss") as mock_faiss:
                mock_faiss.normalize_L2 = Mock()

                results = await indexer.search_similar_packages("web server", limit=2)

                assert len(results) == 2
                assert results[0].name == "nginx"
                assert results[1].name == "apache2"
                assert all(isinstance(pkg, RepositoryPackage) for pkg in results)

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not pytest.importorskip("sentence_transformers", reason="RAG dependencies not available"),
        reason="RAG dependencies not available",
    )
    async def test_get_index_stats(self, temp_index_dir):
        """Test getting index statistics."""
        indexer = RAGIndexer(temp_index_dir)

        stats = await indexer.get_index_stats()

        assert isinstance(stats, dict)
        assert "model_name" in stats
        assert "package_index_available" in stats
        assert "saidata_index_available" in stats
        assert "package_count" in stats
        assert "saidata_count" in stats
        assert stats["model_name"] == "all-MiniLM-L6-v2"


class TestRAGContextBuilder:
    """Test RAG context builder functionality."""

    @pytest.fixture
    def mock_indexer(self):
        """Create mock RAG indexer."""
        indexer = Mock(spec=RAGIndexer)
        return indexer

    @pytest.fixture
    def context_builder(self, mock_indexer):
        """Create RAG context builder with mock indexer."""
        return RAGContextBuilder(mock_indexer)

    @pytest.fixture
    def sample_packages(self):
        """Create sample packages for context building."""
        return [
            RepositoryPackage(
                name="nginx",
                version="1.20.1",
                description="HTTP server",
                repository_name="apt",
                platform="linux",
            )
        ]

    @pytest.fixture
    def sample_saidata(self):
        """Create sample saidata for context building."""
        return [
            SaiData(
                version="0.2",
                metadata=Metadata(name="nginx", description="Web server", category="web-server"),
            )
        ]

    @pytest.mark.asyncio
    async def test_build_context(
        self, context_builder, mock_indexer, sample_packages, sample_saidata
    ):
        """Test building RAG context."""
        # Mock indexer methods
        mock_indexer.search_similar_packages.return_value = sample_packages
        mock_indexer.find_similar_saidata.return_value = sample_saidata

        context = await context_builder.build_context(
            software_name="nginx", target_providers=["apt", "brew"], max_packages=5, max_saidata=3
        )

        assert isinstance(context, dict)
        assert "similar_packages" in context
        assert "similar_saidata" in context
        assert "provider_specific_packages" in context
        assert "context_summary" in context

        assert context["similar_packages"] == sample_packages
        assert context["similar_saidata"] == sample_saidata
        assert isinstance(context["context_summary"], str)

        # Verify indexer was called correctly
        mock_indexer.search_similar_packages.assert_called_once_with("nginx", limit=5)
        mock_indexer.find_similar_saidata.assert_called_once_with("nginx", limit=3)

    @pytest.mark.asyncio
    async def test_build_context_with_error(self, context_builder, mock_indexer):
        """Test building context when indexer fails."""
        # Mock indexer to raise exception
        mock_indexer.search_similar_packages.side_effect = Exception("Index error")

        context = await context_builder.build_context("nginx")

        # Should return empty context on error
        assert context["similar_packages"] == []
        assert context["similar_saidata"] == []
        assert context["provider_specific_packages"] == {}
        assert isinstance(context["context_summary"], str)

    def test_build_context_summary(self, context_builder, sample_packages, sample_saidata):
        """Test context summary building."""
        summary = context_builder._build_context_summary(
            software_name="nginx",
            similar_packages=sample_packages,
            similar_saidata=sample_saidata,
            target_providers=["apt", "brew"],
        )

        assert isinstance(summary, str)
        assert "1 similar packages" in summary
        assert "1 similar saidata" in summary
        assert "apt, brew" in summary
