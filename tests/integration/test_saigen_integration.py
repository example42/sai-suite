"""Integration tests for saigen with real LLM providers."""

import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import yaml

from saigen.core.batch_engine import BatchEngine
from saigen.core.generation_engine import GenerationEngine
from saigen.core.tester import SaidataTester
from saigen.core.validator import SaidataValidator
from saigen.models.generation import GenerationRequest, LLMProvider
from saigen.repositories.manager import RepositoryManager

# Skip integration tests if API keys are not available
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

skip_openai = pytest.mark.skipif(
    not OPENAI_API_KEY,
    reason="OpenAI API key not available (set OPENAI_API_KEY environment variable)",
)

skip_anthropic = pytest.mark.skipif(
    not ANTHROPIC_API_KEY,
    reason="Anthropic API key not available (set ANTHROPIC_API_KEY environment variable)",
)


@pytest.mark.integration
class TestOpenAIIntegration:
    """Integration tests with OpenAI API."""

    @pytest.fixture
    def openai_config(self):
        """Create OpenAI configuration."""
        return {
            "llm_providers": {
                "openai": {
                    "api_key": OPENAI_API_KEY,
                    "model": "gpt-4o-mini",
                    "max_tokens": 2000,
                    "temperature": 0.1,
                }
            },
            "generation": {"retry_attempts": 2, "timeout": 60},
        }

    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @skip_openai
    @pytest.mark.asyncio
    async def test_openai_simple_generation(self, openai_config, temp_output_dir):
        """Test simple saidata generation with OpenAI."""
        engine = GenerationEngine(openai_config)

        request = GenerationRequest(
            software_name="curl",
            target_providers=["apt", "brew"],
            llm_provider=LLMProvider.OPENAI,
            use_rag=False,  # Disable RAG for simpler test
        )

        result = await engine.generate_saidata(request)

        # Verify generation succeeded
        assert result.success, f"Generation failed: {result.validation_errors}"
        assert result.saidata is not None
        assert result.saidata.metadata.name == "curl"
        assert result.llm_provider_used == "openai"
        assert result.tokens_used > 0
        assert result.generation_time > 0

        # Verify saidata structure
        assert result.saidata.version == "0.2"
        assert result.saidata.metadata.description is not None
        assert len(result.saidata.providers) > 0

        # Save and verify file
        output_file = temp_output_dir / "curl.yaml"
        await engine.save_saidata(result.saidata, output_file)

        assert output_file.exists()

        # Verify file content
        with open(output_file, "r") as f:
            content = yaml.safe_load(f)

        assert content["version"] == "0.2"
        assert content["metadata"]["name"] == "curl"

    @skip_openai
    @pytest.mark.asyncio
    async def test_openai_complex_software_generation(self, openai_config, temp_output_dir):
        """Test generation for complex software with OpenAI."""
        engine = GenerationEngine(openai_config)

        request = GenerationRequest(
            software_name="docker",
            target_providers=["apt", "brew", "yum"],
            llm_provider=LLMProvider.OPENAI,
            use_rag=False,
        )

        result = await engine.generate_saidata(request)

        # Verify generation succeeded
        assert result.success, f"Generation failed: {result.validation_errors}"
        assert result.saidata is not None

        # Docker should have multiple providers and services
        assert len(result.saidata.providers) >= 2

        # Should include service configuration for Docker
        if hasattr(result.saidata, "services") and result.saidata.services:
            docker_services = [s for s in result.saidata.services if "docker" in s.name.lower()]
            assert len(docker_services) > 0

    @skip_openai
    @pytest.mark.asyncio
    async def test_openai_validation_retry(self, openai_config):
        """Test OpenAI generation with validation retry."""
        engine = GenerationEngine(openai_config)

        # Request generation for software that might need retry
        request = GenerationRequest(
            software_name="nginx",
            target_providers=["apt", "brew"],
            llm_provider=LLMProvider.OPENAI,
            use_rag=False,
        )

        result = await engine.generate_saidata(request)

        # Should eventually succeed even if first attempt fails validation
        assert result.success, f"Generation failed after retries: {result.validation_errors}"
        assert len(result.validation_errors) == 0

    @skip_openai
    @pytest.mark.asyncio
    async def test_openai_batch_processing(self, openai_config, temp_output_dir):
        """Test batch processing with OpenAI."""
        generation_engine = GenerationEngine(openai_config)
        batch_engine = BatchEngine(
            config={
                "batch": {
                    "max_concurrent": 2,  # Limit concurrency for API rate limits
                    "retry_attempts": 1,
                    "timeout": 120,
                }
            },
            generation_engine=generation_engine,
        )

        software_list = ["git", "vim", "htop"]

        result = await batch_engine.process_batch(
            software_list=software_list,
            output_directory=temp_output_dir,
            llm_provider=LLMProvider.OPENAI,
        )

        # Most should succeed (allow for some API failures)
        assert result.successful >= len(software_list) * 0.7  # At least 70% success rate

        # Verify files were created for successful generations
        successful_files = list(temp_output_dir.glob("*.yaml"))
        assert len(successful_files) == result.successful

    @skip_openai
    @pytest.mark.asyncio
    async def test_openai_with_validation(self, openai_config, temp_output_dir):
        """Test OpenAI generation with comprehensive validation."""
        engine = GenerationEngine(openai_config)
        validator = SaidataValidator()

        request = GenerationRequest(
            software_name="redis",
            target_providers=["apt", "brew"],
            llm_provider=LLMProvider.OPENAI,
            use_rag=False,
        )

        result = await engine.generate_saidata(request)

        assert result.success

        # Save to file for validation
        output_file = temp_output_dir / "redis.yaml"
        await engine.save_saidata(result.saidata, output_file)

        # Validate the generated file
        validation_result = await validator.validate_file(output_file)

        assert validation_result.is_valid, f"Validation failed: {validation_result.errors}"
        assert len(validation_result.errors) == 0


@pytest.mark.integration
class TestAnthropicIntegration:
    """Integration tests with Anthropic Claude API."""

    @pytest.fixture
    def anthropic_config(self):
        """Create Anthropic configuration."""
        return {
            "llm_providers": {
                "anthropic": {
                    "api_key": ANTHROPIC_API_KEY,
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": 2000,
                    "temperature": 0.1,
                }
            },
            "generation": {"retry_attempts": 2, "timeout": 60},
        }

    @skip_anthropic
    @pytest.mark.asyncio
    async def test_anthropic_simple_generation(self, anthropic_config, temp_output_dir):
        """Test simple saidata generation with Anthropic."""
        engine = GenerationEngine(anthropic_config)

        request = GenerationRequest(
            software_name="wget",
            target_providers=["apt", "brew"],
            llm_provider=LLMProvider.ANTHROPIC,
            use_rag=False,
        )

        result = await engine.generate_saidata(request)

        # Verify generation succeeded
        assert result.success, f"Generation failed: {result.validation_errors}"
        assert result.saidata is not None
        assert result.saidata.metadata.name == "wget"
        assert result.llm_provider_used == "anthropic"
        assert result.tokens_used > 0

    @skip_anthropic
    @pytest.mark.asyncio
    async def test_anthropic_vs_openai_comparison(self, temp_output_dir):
        """Compare Anthropic and OpenAI generation for same software."""
        if not OPENAI_API_KEY or not ANTHROPIC_API_KEY:
            pytest.skip("Both OpenAI and Anthropic API keys required for comparison")

        software_name = "python3"

        # Generate with OpenAI
        openai_config = {
            "llm_providers": {
                "openai": {"api_key": OPENAI_API_KEY, "model": "gpt-4o-mini", "temperature": 0.1}
            }
        }

        openai_engine = GenerationEngine(openai_config)
        openai_request = GenerationRequest(
            software_name=software_name,
            target_providers=["apt", "brew"],
            llm_provider=LLMProvider.OPENAI,
            use_rag=False,
        )

        openai_result = await openai_engine.generate_saidata(openai_request)

        # Generate with Anthropic
        anthropic_config = {
            "llm_providers": {
                "anthropic": {
                    "api_key": ANTHROPIC_API_KEY,
                    "model": "claude-3-haiku-20240307",
                    "temperature": 0.1,
                }
            }
        }

        anthropic_engine = GenerationEngine(anthropic_config)
        anthropic_request = GenerationRequest(
            software_name=software_name,
            target_providers=["apt", "brew"],
            llm_provider=LLMProvider.ANTHROPIC,
            use_rag=False,
        )

        anthropic_result = await anthropic_engine.generate_saidata(anthropic_request)

        # Both should succeed
        assert openai_result.success
        assert anthropic_result.success

        # Both should generate valid saidata for the same software
        assert openai_result.saidata.metadata.name == software_name
        assert anthropic_result.saidata.metadata.name == software_name

        # Save both for comparison
        await openai_engine.save_saidata(
            openai_result.saidata, temp_output_dir / f"{software_name}_openai.yaml"
        )
        await anthropic_engine.save_saidata(
            anthropic_result.saidata, temp_output_dir / f"{software_name}_anthropic.yaml"
        )

        # Both files should exist and be valid
        assert (temp_output_dir / f"{software_name}_openai.yaml").exists()
        assert (temp_output_dir / f"{software_name}_anthropic.yaml").exists()


@pytest.mark.integration
class TestRepositoryIntegration:
    """Integration tests with real repository data."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.mark.asyncio
    async def test_repository_manager_real_data(self, temp_cache_dir):
        """Test repository manager with real repository data."""
        # Use a minimal config that doesn't require external dependencies
        config = {
            "repositories": {"test_repo": {"enabled": True, "priority": 80, "cache_ttl": 3600}},
            "cache_directory": str(temp_cache_dir),
        }

        manager = RepositoryManager(config)

        # Mock a simple downloader that simulates real data
        from saigen.models.repository import RepositoryPackage

        mock_packages = [
            RepositoryPackage(
                name="curl",
                version="7.68.0",
                description="Command line tool for transferring data",
                repository_name="test_repo",
                platform="linux",
                category="network",
                homepage="https://curl.se/",
            ),
            RepositoryPackage(
                name="wget",
                version="1.20.3",
                description="Network downloader",
                repository_name="test_repo",
                platform="linux",
                category="network",
                homepage="https://www.gnu.org/software/wget/",
            ),
        ]

        # Mock downloader
        from unittest.mock import AsyncMock, Mock

        mock_downloader = Mock()
        mock_downloader.download_packages = AsyncMock(return_value=mock_packages)

        with patch.object(manager, "_get_downloader", return_value=mock_downloader):
            # Test cache update
            update_result = await manager.update_cache(repositories=["test_repo"])

            assert update_result["updated_repositories"] == 1
            assert update_result["total_packages"] == 2

            # Test package retrieval
            packages = await manager.get_packages("test_repo")
            assert len(packages) == 2

            # Test search
            curl_results = await manager.search_packages("curl")
            assert len(curl_results) == 1
            assert curl_results[0].name == "curl"

            # Test package info
            curl_info = await manager.get_package_info("curl", "test_repo")
            assert curl_info is not None
            assert curl_info.name == "curl"

    @skip_openai
    @pytest.mark.asyncio
    async def test_generation_with_repository_context(self, temp_cache_dir):
        """Test generation with repository context."""
        if not OPENAI_API_KEY:
            pytest.skip("OpenAI API key required")

        # Set up repository manager with mock data
        config = {
            "llm_providers": {"openai": {"api_key": OPENAI_API_KEY, "model": "gpt-4o-mini"}},
            "repositories": {"apt": {"enabled": True, "priority": 80}},
            "cache_directory": str(temp_cache_dir),
        }

        engine = GenerationEngine(config)

        # Mock repository data for nginx
        from saigen.models.repository import RepositoryPackage

        nginx_package = RepositoryPackage(
            name="nginx",
            version="1.18.0",
            description="High-performance HTTP server and reverse proxy",
            repository_name="apt",
            platform="linux",
            category="web-server",
            homepage="https://nginx.org",
            maintainer="nginx team",
        )

        # Mock the repository manager
        with patch.object(engine, "_repository_manager") as mock_repo_manager:
            mock_repo_manager.search_packages = AsyncMock(return_value=[nginx_package])

            request = GenerationRequest(
                software_name="nginx",
                target_providers=["apt"],
                llm_provider=LLMProvider.OPENAI,
                use_rag=True,  # Enable RAG to use repository context
            )

            result = await engine.generate_saidata(request)

            assert result.success
            assert result.saidata.metadata.name == "nginx"

            # The generated saidata should reflect repository information
            assert "apt" in result.saidata.providers
            apt_config = result.saidata.providers["apt"]
            assert any(pkg.name == "nginx" for pkg in apt_config.packages)


@pytest.mark.integration
class TestEndToEndWorkflows:
    """End-to-end integration tests."""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "output").mkdir()
            (workspace / "cache").mkdir()
            yield workspace

    @skip_openai
    @pytest.mark.asyncio
    async def test_complete_generation_workflow(self, temp_workspace):
        """Test complete generation workflow from request to validation."""
        config = {
            "llm_providers": {"openai": {"api_key": OPENAI_API_KEY, "model": "gpt-4o-mini"}},
            "output_directory": str(temp_workspace / "output"),
            "cache_directory": str(temp_workspace / "cache"),
        }

        # Step 1: Generate saidata
        engine = GenerationEngine(config)
        request = GenerationRequest(
            software_name="jq",
            target_providers=["apt", "brew"],
            llm_provider=LLMProvider.OPENAI,
            use_rag=False,
        )

        result = await engine.generate_saidata(request)
        assert result.success

        # Step 2: Save to file
        output_file = temp_workspace / "output" / "jq.yaml"
        await engine.save_saidata(result.saidata, output_file)
        assert output_file.exists()

        # Step 3: Validate the generated file
        validator = SaidataValidator()
        validation_result = await validator.validate_file(output_file)
        assert validation_result.is_valid

        # Step 4: Test the saidata (dry run)
        tester = SaidataTester()
        test_result = await tester.test_saidata_file(output_file, dry_run=True)

        # Test should complete (may have warnings but shouldn't fail completely)
        assert test_result is not None

    @skip_openai
    @pytest.mark.asyncio
    async def test_batch_generation_workflow(self, temp_workspace):
        """Test complete batch generation workflow."""
        config = {
            "llm_providers": {"openai": {"api_key": OPENAI_API_KEY, "model": "gpt-4o-mini"}},
            "batch": {"max_concurrent": 2, "retry_attempts": 1, "timeout": 120},
            "output_directory": str(temp_workspace / "output"),
            "cache_directory": str(temp_workspace / "cache"),
        }

        # Create software list
        software_list = ["tree", "less", "grep"]

        # Step 1: Batch generation
        generation_engine = GenerationEngine(config)
        batch_engine = BatchEngine(config, generation_engine)

        batch_result = await batch_engine.process_batch(
            software_list=software_list,
            output_directory=temp_workspace / "output",
            llm_provider=LLMProvider.OPENAI,
        )

        # Should have reasonable success rate
        assert batch_result.successful >= len(software_list) * 0.6  # At least 60%

        # Step 2: Validate all generated files
        validator = SaidataValidator()
        output_files = list((temp_workspace / "output").glob("*.yaml"))

        for output_file in output_files:
            validation_result = await validator.validate_file(output_file)
            assert validation_result.is_valid, f"Validation failed for {output_file}"

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, temp_workspace):
        """Test error recovery in workflows."""
        # Test with invalid configuration
        config = {"llm_providers": {"openai": {"api_key": "invalid-key", "model": "gpt-4o-mini"}}}

        engine = GenerationEngine(config)
        request = GenerationRequest(software_name="test", llm_provider=LLMProvider.OPENAI)

        # Should handle invalid API key gracefully
        result = await engine.generate_saidata(request)
        assert not result.success
        assert len(result.validation_errors) > 0


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "-m", "integration", "--tb=short"])
