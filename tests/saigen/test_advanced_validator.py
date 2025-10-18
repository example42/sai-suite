"""Tests for advanced validation and quality metrics system."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest

from saigen.core.advanced_validator import (
    AdvancedSaidataValidator,
    QualityMetric,
    QualityReport,
    QualityScore,
)
from saigen.core.validator import SaidataValidator, ValidationResult
from saigen.models.repository import RepositoryPackage
from saigen.models.saidata import Metadata, Package, ProviderConfig, SaiData
from saigen.repositories.manager import RepositoryManager


@pytest.fixture
def sample_saidata():
    """Create a sample SaiData for testing."""
    return SaiData(
        version="0.2",
        metadata=Metadata(
            name="nginx",
            display_name="NGINX",
            description="High-performance web server and reverse proxy",
            category="web-server",
            license="BSD-2-Clause",
        ),
        providers={
            "apt": ProviderConfig(
                packages=[
                    Package(name="nginx", package_name="nginx", version="1.18.0"),
                    Package(name="nginx-common", package_name="nginx-common"),
                ]
            ),
            "brew": ProviderConfig(packages=[Package(name="nginx", package_name="nginx")]),
        },
    )


@pytest.fixture
def mock_repository_manager():
    """Create a mock repository manager."""
    manager = Mock(spec=RepositoryManager)
    manager.search_packages = AsyncMock()
    manager.get_package_details = AsyncMock()
    return manager


@pytest.fixture
def advanced_validator(mock_repository_manager):
    """Create an advanced validator with mocked dependencies."""
    base_validator = Mock(spec=SaidataValidator)
    base_validator.validate_pydantic_model.return_value = ValidationResult(
        is_valid=True, errors=[], warnings=[], info=[]
    )

    return AdvancedSaidataValidator(mock_repository_manager, base_validator)


class TestAdvancedSaidataValidator:
    """Test cases for AdvancedSaidataValidator."""

    @pytest.mark.asyncio
    async def test_validate_comprehensive_basic(self, advanced_validator, sample_saidata):
        """Test basic comprehensive validation."""
        # Mock repository responses
        advanced_validator.repository_manager.search_packages.return_value = Mock(
            packages=[
                RepositoryPackage(
                    name="nginx",
                    version="1.18.0",
                    description="High-performance web server",
                    repository_name="apt",
                    platform="linux",
                )
            ]
        )

        advanced_validator.repository_manager.get_package_details.return_value = RepositoryPackage(
            name="nginx",
            version="1.18.0",
            description="High-performance web server",
            repository_name="apt",
            platform="linux",
        )

        # Run validation
        report = await advanced_validator.validate_comprehensive(sample_saidata)

        # Assertions
        assert isinstance(report, QualityReport)
        assert 0.0 <= report.overall_score <= 1.0
        assert len(report.metric_scores) == 6  # All quality metrics
        assert QualityMetric.COMPLETENESS in report.metric_scores
        assert QualityMetric.CONSISTENCY in report.metric_scores
        assert QualityMetric.METADATA_RICHNESS in report.metric_scores
        assert QualityMetric.CROSS_REFERENCE_INTEGRITY in report.metric_scores
        assert QualityMetric.REPOSITORY_ALIGNMENT in report.metric_scores
        assert QualityMetric.ACCURACY in report.metric_scores

    @pytest.mark.asyncio
    async def test_validate_comprehensive_no_repository_check(
        self, advanced_validator, sample_saidata
    ):
        """Test comprehensive validation without repository checking."""
        report = await advanced_validator.validate_comprehensive(
            sample_saidata, check_repository_accuracy=False
        )

        # Should still have all metrics but repository-dependent ones should be skipped
        assert isinstance(report, QualityReport)
        assert len(report.metric_scores) == 6

        # Repository-dependent metrics should have default scores
        repo_alignment = report.metric_scores[QualityMetric.REPOSITORY_ALIGNMENT]
        accuracy = report.metric_scores[QualityMetric.ACCURACY]

        assert repo_alignment.details["status"] == "skipped"
        assert accuracy.details["status"] == "skipped"

    @pytest.mark.asyncio
    async def test_assess_completeness_high_score(self, advanced_validator):
        """Test completeness assessment with high-quality saidata."""
        saidata = SaiData(
            version="0.2",
            metadata=Metadata(
                name="nginx",
                display_name="NGINX",
                description="High-performance web server and reverse proxy server",
                category="web-server",
                subcategory="http-server",
                license="BSD-2-Clause",
                language="C",
                maintainer="NGINX Team",
                tags=["web", "server", "proxy"],
            ),
            providers={
                "apt": ProviderConfig(packages=[Package(name="nginx", package_name="nginx")]),
                "dnf": ProviderConfig(packages=[Package(name="nginx", package_name="nginx")]),
                "brew": ProviderConfig(packages=[Package(name="nginx", package_name="nginx")]),
            },
        )

        score = await advanced_validator._assess_completeness(saidata)

        assert isinstance(score, QualityScore)
        assert score.metric == QualityMetric.COMPLETENESS
        assert score.score >= 0.75  # Should be reasonably high due to complete metadata
        assert len(score.issues) == 0

    @pytest.mark.asyncio
    async def test_assess_completeness_low_score(self, advanced_validator):
        """Test completeness assessment with minimal saidata."""
        saidata = SaiData(version="0.2", metadata=Metadata(name="test"))  # Minimal metadata

        score = await advanced_validator._assess_completeness(saidata)

        assert isinstance(score, QualityScore)
        assert score.metric == QualityMetric.COMPLETENESS
        assert score.score < 0.5  # Should be low due to missing fields
        assert len(score.issues) > 0
        assert len(score.suggestions) > 0

    @pytest.mark.asyncio
    async def test_assess_consistency_name_mismatch(self, advanced_validator):
        """Test consistency assessment with name mismatches."""
        saidata = SaiData(
            version="0.2",
            metadata=Metadata(
                name="nginx",
                display_name="Apache HTTP Server",  # Inconsistent name
                version="1.0.0",
            ),
        )

        score = await advanced_validator._assess_consistency(saidata)

        assert isinstance(score, QualityScore)
        assert score.metric == QualityMetric.CONSISTENCY
        assert score.score < 1.0  # Should be penalized for inconsistency
        assert any("name" in issue.lower() for issue in score.issues)

    @pytest.mark.asyncio
    async def test_assess_metadata_richness(self, advanced_validator, sample_saidata):
        """Test metadata richness assessment."""
        score = await advanced_validator._assess_metadata_richness(sample_saidata)

        assert isinstance(score, QualityScore)
        assert score.metric == QualityMetric.METADATA_RICHNESS
        assert 0.0 <= score.score <= 1.0
        assert "basic_metadata_richness" in score.details
        assert "description_quality" in score.details

    @pytest.mark.asyncio
    async def test_assess_cross_reference_integrity_valid(self, advanced_validator):
        """Test cross-reference integrity with valid references."""
        from saigen.models.saidata import Repository

        saidata = SaiData(
            version="0.2",
            metadata=Metadata(name="test"),
            providers={
                "apt": ProviderConfig(
                    repositories=[Repository(name="main-repo", url="http://example.com")],
                    packages=[
                        Package(name="test-pkg", package_name="test-pkg", repository="main-repo")
                    ],
                )
            },
        )

        score = await advanced_validator._assess_cross_reference_integrity(saidata)

        assert isinstance(score, QualityScore)
        assert score.metric == QualityMetric.CROSS_REFERENCE_INTEGRITY
        assert score.score == 1.0  # Should be perfect with valid references
        assert len(score.issues) == 0

    @pytest.mark.asyncio
    async def test_assess_cross_reference_integrity_invalid(self, advanced_validator):
        """Test cross-reference integrity with invalid references."""
        saidata = SaiData(
            version="0.2",
            metadata=Metadata(name="test"),
            providers={
                "apt": ProviderConfig(
                    packages=[
                        Package(
                            name="test-pkg", package_name="test-pkg", repository="undefined-repo"
                        )
                    ]
                )
            },
        )

        score = await advanced_validator._assess_cross_reference_integrity(saidata)

        assert isinstance(score, QualityScore)
        assert score.metric == QualityMetric.CROSS_REFERENCE_INTEGRITY
        assert score.score < 1.0  # Should be penalized for undefined reference
        assert len(score.issues) > 0
        assert any("undefined repository" in issue.lower() for issue in score.issues)

    @pytest.mark.asyncio
    async def test_package_exists_in_repository_found(self, advanced_validator):
        """Test package existence checking when package is found."""
        # Mock search result with matching package
        mock_search_result = Mock()
        mock_search_result.packages = [
            RepositoryPackage(
                name="nginx", version="1.18.0", repository_name="apt", platform="linux"
            )
        ]

        advanced_validator.repository_manager.search_packages.return_value = mock_search_result

        exists = await advanced_validator._package_exists_in_repository("apt", "nginx")

        assert exists is True
        advanced_validator.repository_manager.search_packages.assert_called_once()

    @pytest.mark.asyncio
    async def test_package_exists_in_repository_not_found(self, advanced_validator):
        """Test package existence checking when package is not found."""
        # Mock empty search result
        mock_search_result = Mock()
        mock_search_result.packages = []

        advanced_validator.repository_manager.search_packages.return_value = mock_search_result

        exists = await advanced_validator._package_exists_in_repository("apt", "nonexistent")

        assert exists is False

    @pytest.mark.asyncio
    async def test_package_exists_in_repository_exception(self, advanced_validator):
        """Test package existence checking when exception occurs."""
        # Mock exception during search
        advanced_validator.repository_manager.search_packages.side_effect = Exception(
            "Network error"
        )

        exists = await advanced_validator._package_exists_in_repository("apt", "nginx")

        # Should return True when unable to check (assume valid)
        assert exists is True

    def test_calculate_string_similarity(self, advanced_validator):
        """Test string similarity calculation."""
        # Identical strings
        assert advanced_validator._calculate_string_similarity("nginx", "nginx") == 1.0

        # Similar strings
        similarity = advanced_validator._calculate_string_similarity("nginx", "nginx-common")
        assert 0.3 < similarity < 1.0  # Adjusted expectation

        # Different strings
        similarity = advanced_validator._calculate_string_similarity("nginx", "apache")
        assert 0.0 <= similarity < 0.5

        # Empty strings
        assert advanced_validator._calculate_string_similarity("", "") == 1.0
        assert advanced_validator._calculate_string_similarity("nginx", "") == 0.0
        assert advanced_validator._calculate_string_similarity("", "nginx") == 0.0

    def test_detect_circular_dependencies(self, advanced_validator):
        """Test circular dependency detection."""
        # Note: Current Package model doesn't have dependencies field
        # This test verifies the method returns empty list for now
        packages = [
            Package(name="pkg-a", package_name="pkg-a"),
            Package(name="pkg-b", package_name="pkg-b"),
            Package(name="pkg-c", package_name="pkg-c"),
        ]

        cycles = advanced_validator._detect_circular_dependencies(packages)

        # Should return empty list since Package model doesn't have dependencies
        assert len(cycles) == 0

    def test_detect_orphaned_configurations(self, advanced_validator):
        """Test orphaned configuration detection."""
        from saigen.models.saidata import File, Service

        saidata = SaiData(
            version="0.2",
            metadata=Metadata(name="test"),
            services=[Service(name="orphaned-service")],  # Not used by any provider
            files=[File(name="orphaned-file", path="/tmp/test")],  # Not used by any provider
            providers={
                "apt": ProviderConfig(
                    services=[Service(name="used-service")],
                    files=[File(name="used-file", path="/tmp/used")],
                )
            },
        )

        orphaned = advanced_validator._detect_orphaned_configurations(saidata)

        assert "services" in orphaned
        assert "orphaned-service" in orphaned["services"]
        assert "files" in orphaned
        assert "orphaned-file" in orphaned["files"]

    def test_calculate_overall_score(self, advanced_validator):
        """Test overall score calculation."""
        metric_scores = {
            QualityMetric.COMPLETENESS: QualityScore(
                metric=QualityMetric.COMPLETENESS,
                score=0.8,
                max_score=1.0,
                details={},
                issues=[],
                suggestions=[],
            ),
            QualityMetric.ACCURACY: QualityScore(
                metric=QualityMetric.ACCURACY,
                score=0.9,
                max_score=1.0,
                details={},
                issues=[],
                suggestions=[],
            ),
            QualityMetric.CONSISTENCY: QualityScore(
                metric=QualityMetric.CONSISTENCY,
                score=0.7,
                max_score=1.0,
                details={},
                issues=[],
                suggestions=[],
            ),
        }

        overall_score = advanced_validator._calculate_overall_score(metric_scores)

        # Should be weighted average based on metric weights
        assert 0.0 <= overall_score <= 1.0
        assert overall_score > 0.7  # Should be reasonably high given the input scores

    def test_format_quality_report_basic(self, advanced_validator):
        """Test basic quality report formatting."""
        # Create a minimal quality report
        validation_result = ValidationResult(is_valid=True, errors=[], warnings=[], info=[])

        metric_scores = {
            QualityMetric.COMPLETENESS: QualityScore(
                metric=QualityMetric.COMPLETENESS,
                score=0.8,
                max_score=1.0,
                details={"basic_metadata_richness": 0.8},
                issues=["Missing category"],
                suggestions=["Add category field"],
            )
        }

        report = QualityReport(
            overall_score=0.8,
            metric_scores=metric_scores,
            validation_result=validation_result,
            repository_accuracy={"apt": 0.9},
            cross_reference_issues=[],
            recommendations=["Improve metadata completeness"],
            generated_at=datetime.now(timezone.utc),
        )

        formatted = advanced_validator.format_quality_report(report, detailed=False)

        assert "SAIDATA QUALITY REPORT" in formatted
        assert "Overall Quality Score" in formatted
        assert "0.80" in formatted
        assert "Completeness" in formatted
        assert "Repository Accuracy" in formatted
        assert "Recommendations" in formatted

    def test_format_quality_report_detailed(self, advanced_validator):
        """Test detailed quality report formatting."""
        validation_result = ValidationResult(is_valid=True, errors=[], warnings=[], info=[])

        metric_scores = {
            QualityMetric.COMPLETENESS: QualityScore(
                metric=QualityMetric.COMPLETENESS,
                score=0.8,
                max_score=1.0,
                details={
                    "basic_metadata_richness": 0.8,
                    "populated_basic_fields": 6,
                    "missing_important": ["category", "license"],
                },
                issues=["Missing category"],
                suggestions=["Add category field", "Add license information"],
            )
        }

        report = QualityReport(
            overall_score=0.8,
            metric_scores=metric_scores,
            validation_result=validation_result,
            repository_accuracy={},
            cross_reference_issues=[],
            recommendations=["Improve metadata completeness"],
            generated_at=datetime.now(timezone.utc),
        )

        formatted = advanced_validator.format_quality_report(report, detailed=True)

        assert "SAIDATA QUALITY REPORT" in formatted
        assert "Detailed Metrics" in formatted
        assert "basic_metadata_richness" in formatted
        assert "populated_basic_fields" in formatted
        assert "Suggestions:" in formatted

    def test_create_score_bar(self, advanced_validator):
        """Test score bar creation."""
        # High score
        bar = advanced_validator._create_score_bar(0.9, width=10)
        assert len(bar) == 12  # [10 chars + 2 brackets]
        assert "█" in bar

        # Medium score
        bar = advanced_validator._create_score_bar(0.5, width=10)
        assert len(bar) == 12
        assert "█" in bar and "░" in bar

        # Low score
        bar = advanced_validator._create_score_bar(0.1, width=10)
        assert len(bar) == 12
        assert "░" in bar


class TestQualityMetrics:
    """Test cases for quality metric calculations."""

    @pytest.mark.asyncio
    async def test_completeness_metric_comprehensive(self):
        """Test completeness metric with comprehensive saidata."""
        from saigen.models.saidata import SecurityMetadata, Urls

        saidata = SaiData(
            version="0.2",
            metadata=Metadata(
                name="nginx",
                display_name="NGINX",
                description="High-performance web server and reverse proxy",
                category="web-server",
                subcategory="http-server",
                license="BSD-2-Clause",
                language="C",
                maintainer="NGINX Team",
                tags=["web", "server", "proxy"],
                urls=Urls(
                    website="https://nginx.org",
                    documentation="https://nginx.org/docs",
                    source="https://github.com/nginx/nginx",
                ),
                security=SecurityMetadata(security_contact="security@nginx.org"),
            ),
            providers={
                "apt": ProviderConfig(packages=[Package(name="nginx", package_name="nginx")]),
                "dnf": ProviderConfig(packages=[Package(name="nginx", package_name="nginx")]),
                "brew": ProviderConfig(packages=[Package(name="nginx", package_name="nginx")]),
                "winget": ProviderConfig(packages=[Package(name="nginx", package_name="nginx")]),
            },
        )

        validator = AdvancedSaidataValidator(Mock(), Mock())
        score = await validator._assess_completeness(saidata)

        # Should have high completeness score
        assert score.score > 0.8
        assert len(score.issues) == 0
        assert score.details["provider_coverage"] >= 4

    @pytest.mark.asyncio
    async def test_metadata_richness_comprehensive(self):
        """Test metadata richness with rich metadata."""
        from saigen.models.saidata import Urls

        saidata = SaiData(
            version="0.2",
            metadata=Metadata(
                name="nginx",
                display_name="NGINX Web Server",
                description="NGINX is a high-performance web server and reverse proxy server known for its stability, rich feature set, simple configuration, and low resource consumption.",
                category="web-server",
                subcategory="http-server",
                license="BSD-2-Clause",
                language="C",
                maintainer="NGINX Team",
                tags=["web", "server", "proxy", "http", "performance"],
                urls=Urls(
                    website="https://nginx.org",
                    documentation="https://nginx.org/docs",
                    source="https://github.com/nginx/nginx",
                    issues="https://trac.nginx.org",
                    download="https://nginx.org/download",
                ),
            ),
        )

        validator = AdvancedSaidataValidator(Mock(), Mock())
        score = await validator._assess_metadata_richness(saidata)

        # Should have high richness score
        assert score.score > 0.8
        assert score.details["basic_metadata_richness"] > 0.8
        assert score.details["url_richness"] > 0.6
        assert score.details["description_quality"] == 1.0  # Long, detailed description
        assert score.details["tags_quality"] == 1.0  # 5 tags


if __name__ == "__main__":
    pytest.main([__file__])
