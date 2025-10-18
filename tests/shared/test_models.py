"""Tests for data models."""

import pytest
from pydantic import ValidationError

from saigen.models.generation import GenerationRequest, GenerationResult, LLMProvider
from saigen.models.repository import RepositoryPackage
from saigen.models.saidata import SaiData, ServiceType


class TestSaiDataModels:
    """Test SaiData model validation."""

    def test_minimal_saidata(self):
        """Test creating minimal valid SaiData."""
        data = {"version": "0.2.0", "metadata": {"name": "nginx"}}
        saidata = SaiData(**data)
        assert saidata.version == "0.2.0"
        assert saidata.metadata.name == "nginx"

    def test_complete_saidata(self):
        """Test creating complete SaiData with all fields."""
        data = {
            "version": "0.2.0",
            "metadata": {
                "name": "nginx",
                "display_name": "NGINX Web Server",
                "description": "High-performance HTTP server",
                "category": "web-server",
                "tags": ["web", "server", "proxy"],
            },
            "packages": [{"name": "nginx", "version": "1.24.0"}],
            "services": [{"name": "nginx", "type": "systemd", "enabled": True}],
        }
        saidata = SaiData(**data)
        assert len(saidata.packages) == 1
        assert len(saidata.services) == 1
        assert saidata.services[0].type == ServiceType.SYSTEMD

    def test_invalid_version_format(self):
        """Test validation of version format."""
        with pytest.raises(ValidationError):
            SaiData(version="invalid-version", metadata={"name": "test"})

    def test_missing_required_fields(self):
        """Test validation of required fields."""
        # Missing version
        with pytest.raises(ValidationError):
            SaiData(metadata={"name": "test"})

        # Missing metadata
        with pytest.raises(ValidationError):
            SaiData(version="0.2.0")

        # Missing metadata.name
        with pytest.raises(ValidationError):
            SaiData(version="0.2.0", metadata={})


class TestGenerationModels:
    """Test generation request and result models."""

    def test_generation_request(self):
        """Test GenerationRequest model."""
        request = GenerationRequest(
            software_name="nginx", target_providers=["apt", "brew"], llm_provider=LLMProvider.OPENAI
        )
        assert request.software_name == "nginx"
        assert request.llm_provider == LLMProvider.OPENAI
        assert request.use_rag is True  # default value

    def test_generation_result(self):
        """Test GenerationResult model."""
        result = GenerationResult(success=True, generation_time=1.5, llm_provider_used="openai")
        assert result.success is True
        assert result.generation_time == 1.5
        assert len(result.validation_errors) == 0  # default empty list


class TestRepositoryModels:
    """Test repository data models."""

    def test_repository_package(self):
        """Test RepositoryPackage model."""
        package = RepositoryPackage(
            name="nginx",
            version="1.24.0",
            description="HTTP server",
            repository_name="ubuntu-main",
            platform="linux",
        )
        assert package.name == "nginx"
        assert package.platform == "linux"

    def test_repository_package_extra_fields(self):
        """Test that extra fields are allowed in RepositoryPackage."""
        package = RepositoryPackage(
            name="nginx",
            version="1.24.0",
            repository_name="ubuntu-main",
            platform="linux",
            custom_field="custom_value",  # Extra field should be allowed
        )
        assert hasattr(package, "custom_field")
        assert package.custom_field == "custom_value"


if __name__ == "__main__":
    pytest.main([__file__])
