#!/usr/bin/env python3
"""
Advanced Validation Demo

This script demonstrates the advanced validation and quality metrics system
for saidata files. It shows how to use the AdvancedSaidataValidator to assess
quality metrics and repository accuracy.
"""

import asyncio
from pathlib import Path
from unittest.mock import Mock

from saigen.core.advanced_validator import AdvancedSaidataValidator
from saigen.core.validator import SaidataValidator
from saigen.models.saidata import SaiData, Metadata, ProviderConfig, Package, Urls
from saigen.models.repository import RepositoryPackage


async def demo_advanced_validation():
    """Demonstrate advanced validation features."""
    print("🔍 Advanced Saidata Validation Demo")
    print("=" * 50)
    
    # Create sample saidata with varying quality levels
    samples = [
        create_high_quality_saidata(),
        create_medium_quality_saidata(),
        create_low_quality_saidata()
    ]
    
    sample_names = ["High Quality", "Medium Quality", "Low Quality"]
    
    # Mock repository manager for demonstration
    mock_repo_manager = create_mock_repository_manager()
    
    # Create advanced validator
    base_validator = SaidataValidator()
    advanced_validator = AdvancedSaidataValidator(mock_repo_manager, base_validator)
    
    for i, (saidata, name) in enumerate(zip(samples, sample_names)):
        print(f"\n📊 Analyzing {name} Sample:")
        print("-" * 30)
        
        # Run comprehensive validation
        report = await advanced_validator.validate_comprehensive(saidata, check_repository_accuracy=True)
        
        # Display results
        print(f"Overall Score: {report.overall_score:.2f}/1.00")
        print(f"Schema Valid: {'✅' if report.validation_result.is_valid else '❌'}")
        
        print("\nQuality Metrics:")
        for metric, score in report.metric_scores.items():
            score_emoji = "🟢" if score.score >= 0.8 else "🟡" if score.score >= 0.6 else "🔴"
            metric_name = metric.value.replace('_', ' ').title()
            print(f"  {score_emoji} {metric_name}: {score.score:.2f}")
        
        if report.repository_accuracy:
            print("\nRepository Accuracy:")
            for provider, accuracy in report.repository_accuracy.items():
                acc_emoji = "🟢" if accuracy >= 0.8 else "🟡" if accuracy >= 0.6 else "🔴"
                print(f"  {acc_emoji} {provider}: {accuracy:.2f}")
        
        if report.recommendations:
            print(f"\nTop Recommendations:")
            for j, rec in enumerate(report.recommendations[:3], 1):
                print(f"  {j}. {rec}")
        
        print()


def create_high_quality_saidata() -> SaiData:
    """Create a high-quality saidata sample."""
    return SaiData(
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
                issues="https://trac.nginx.org"
            )
        ),
        providers={
            "apt": ProviderConfig(packages=[Package(name="nginx", version="1.18.0")]),
            "dnf": ProviderConfig(packages=[Package(name="nginx", version="1.18.0")]),
            "brew": ProviderConfig(packages=[Package(name="nginx")]),
            "winget": ProviderConfig(packages=[Package(name="nginx")])
        }
    )


def create_medium_quality_saidata() -> SaiData:
    """Create a medium-quality saidata sample."""
    return SaiData(
        version="0.2",
        metadata=Metadata(
            name="redis",
            description="In-memory data structure store",
            category="database",
            license="BSD-3-Clause",
            tags=["database", "cache"]
        ),
        providers={
            "apt": ProviderConfig(packages=[Package(name="redis-server")]),
            "brew": ProviderConfig(packages=[Package(name="redis")])
        }
    )


def create_low_quality_saidata() -> SaiData:
    """Create a low-quality saidata sample."""
    return SaiData(
        version="0.2",
        metadata=Metadata(
            name="test-app",
            description="App"  # Very short description
        ),
        providers={
            "apt": ProviderConfig(packages=[Package(name="nonexistent-package")])
        }
    )


def create_mock_repository_manager():
    """Create a mock repository manager for demonstration."""
    mock_manager = Mock()
    
    # Mock search results for known packages
    def mock_search(query, **kwargs):
        mock_result = Mock()
        if query.lower() in ["nginx", "redis", "redis-server"]:
            mock_result.packages = [
                RepositoryPackage(
                    name=query,
                    version="1.18.0" if query == "nginx" else "6.2.0",
                    description=f"Mock description for {query}",
                    repository_name="mock-repo",
                    platform="linux"
                )
            ]
        else:
            mock_result.packages = []  # Package not found
        return mock_result
    
    def mock_get_package_details(package_name, **kwargs):
        if package_name.lower() in ["nginx", "redis", "redis-server"]:
            return RepositoryPackage(
                name=package_name,
                version="1.18.0" if package_name == "nginx" else "6.2.0",
                description=f"Mock description for {package_name}",
                repository_name="mock-repo",
                platform="linux"
            )
        return None
    
    mock_manager.search_packages = Mock(side_effect=mock_search)
    mock_manager.get_package_details = Mock(side_effect=mock_get_package_details)
    
    return mock_manager


async def demo_quality_metrics():
    """Demonstrate individual quality metrics."""
    print("\n🎯 Individual Quality Metrics Demo")
    print("=" * 50)
    
    # Create validator
    mock_repo_manager = create_mock_repository_manager()
    base_validator = SaidataValidator()
    advanced_validator = AdvancedSaidataValidator(mock_repo_manager, base_validator)
    
    # Test completeness metric
    print("\n📋 Completeness Metric:")
    saidata = create_high_quality_saidata()
    completeness_score = await advanced_validator._assess_completeness(saidata)
    print(f"Score: {completeness_score.score:.2f}")
    print(f"Details: {completeness_score.details}")
    if completeness_score.suggestions:
        print(f"Suggestions: {completeness_score.suggestions}")
    
    # Test consistency metric
    print("\n🔄 Consistency Metric:")
    consistency_score = await advanced_validator._assess_consistency(saidata)
    print(f"Score: {consistency_score.score:.2f}")
    print(f"Details: {consistency_score.details}")
    
    # Test metadata richness
    print("\n📝 Metadata Richness:")
    richness_score = await advanced_validator._assess_metadata_richness(saidata)
    print(f"Score: {richness_score.score:.2f}")
    print(f"Details: {richness_score.details}")


def demo_string_similarity():
    """Demonstrate string similarity calculation."""
    print("\n🔤 String Similarity Demo")
    print("=" * 50)
    
    mock_repo_manager = create_mock_repository_manager()
    base_validator = SaidataValidator()
    advanced_validator = AdvancedSaidataValidator(mock_repo_manager, base_validator)
    
    test_pairs = [
        ("nginx", "nginx"),
        ("nginx", "nginx-common"),
        ("nginx", "apache"),
        ("redis", "redis-server"),
        ("postgresql", "postgres"),
        ("", ""),
        ("test", "")
    ]
    
    print("String similarity calculations:")
    for str1, str2 in test_pairs:
        similarity = advanced_validator._calculate_string_similarity(str1, str2)
        print(f"  '{str1}' vs '{str2}': {similarity:.3f}")


async def main():
    """Run all demonstrations."""
    await demo_advanced_validation()
    await demo_quality_metrics()
    demo_string_similarity()
    
    print("\n✅ Advanced Validation Demo Complete!")
    print("\nTo use advanced validation in CLI:")
    print("  saigen validate --advanced --detailed your-file.yaml")
    print("  saigen quality --threshold 0.8 your-file.yaml")


if __name__ == "__main__":
    asyncio.run(main())