"""Advanced validation and quality metrics for saidata files."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from ..models.repository import RepositoryPackage
from ..models.saidata import SaiData
from ..repositories.manager import RepositoryManager
from .validator import SaidataValidator, ValidationError, ValidationResult, ValidationSeverity


class QualityMetric(str, Enum):
    """Quality metric types."""

    COMPLETENESS = "completeness"
    ACCURACY = "accuracy"
    CONSISTENCY = "consistency"
    REPOSITORY_ALIGNMENT = "repository_alignment"
    METADATA_RICHNESS = "metadata_richness"
    CROSS_REFERENCE_INTEGRITY = "cross_reference_integrity"


@dataclass
class QualityScore:
    """Quality score for a specific metric."""

    metric: QualityMetric
    score: float  # 0.0 to 1.0
    max_score: float
    details: Dict[str, Any]
    issues: List[str]
    suggestions: List[str]


@dataclass
class QualityReport:
    """Comprehensive quality report for saidata."""

    overall_score: float
    metric_scores: Dict[QualityMetric, QualityScore]
    validation_result: ValidationResult
    repository_accuracy: Dict[str, float]
    cross_reference_issues: List[ValidationError]
    recommendations: List[str]
    generated_at: datetime


class AdvancedSaidataValidator:
    """Advanced validation system with quality metrics and repository accuracy checking."""

    def __init__(
        self,
        repository_manager: RepositoryManager,
        base_validator: Optional[SaidataValidator] = None,
    ):
        """Initialize advanced validator.

        Args:
            repository_manager: Repository manager for accuracy checking
            base_validator: Base validator for schema validation
        """
        self.repository_manager = repository_manager
        self.base_validator = base_validator or SaidataValidator()

        # Quality metric weights
        self.metric_weights = {
            QualityMetric.COMPLETENESS: 0.20,
            QualityMetric.ACCURACY: 0.25,
            QualityMetric.CONSISTENCY: 0.15,
            QualityMetric.REPOSITORY_ALIGNMENT: 0.20,
            QualityMetric.METADATA_RICHNESS: 0.10,
            QualityMetric.CROSS_REFERENCE_INTEGRITY: 0.10,
        }

    async def validate_comprehensive(
        self, saidata: SaiData, check_repository_accuracy: bool = True
    ) -> QualityReport:
        """Perform comprehensive validation with quality metrics.

        Args:
            saidata: SaiData to validate
            check_repository_accuracy: Whether to check against repository data

        Returns:
            Comprehensive quality report
        """
        # Start with base validation
        base_validation = self.base_validator.validate_pydantic_model(saidata)

        # Initialize quality scores
        metric_scores = {}

        # Run all quality metrics
        metric_scores[QualityMetric.COMPLETENESS] = await self._assess_completeness(saidata)
        metric_scores[QualityMetric.CONSISTENCY] = await self._assess_consistency(saidata)
        metric_scores[QualityMetric.METADATA_RICHNESS] = await self._assess_metadata_richness(
            saidata
        )
        metric_scores[
            QualityMetric.CROSS_REFERENCE_INTEGRITY
        ] = await self._assess_cross_reference_integrity(saidata)

        # Repository-dependent metrics
        repository_accuracy = {}
        if check_repository_accuracy:
            metric_scores[
                QualityMetric.REPOSITORY_ALIGNMENT
            ] = await self._assess_repository_alignment(saidata)
            metric_scores[QualityMetric.ACCURACY] = await self._assess_accuracy(saidata)
            repository_accuracy = await self._check_repository_accuracy(saidata)
        else:
            # Provide default scores when repository checking is disabled
            metric_scores[QualityMetric.REPOSITORY_ALIGNMENT] = QualityScore(
                metric=QualityMetric.REPOSITORY_ALIGNMENT,
                score=0.5,
                max_score=1.0,
                details={"status": "skipped"},
                issues=[],
                suggestions=["Enable repository checking for accurate assessment"],
            )
            metric_scores[QualityMetric.ACCURACY] = QualityScore(
                metric=QualityMetric.ACCURACY,
                score=0.5,
                max_score=1.0,
                details={"status": "skipped"},
                issues=[],
                suggestions=["Enable repository checking for accurate assessment"],
            )

        # Calculate overall score
        overall_score = self._calculate_overall_score(metric_scores)

        # Generate cross-reference issues
        cross_ref_issues = await self._validate_cross_references_advanced(saidata)

        # Generate recommendations
        recommendations = self._generate_recommendations(metric_scores, base_validation)

        return QualityReport(
            overall_score=overall_score,
            metric_scores=metric_scores,
            validation_result=base_validation,
            repository_accuracy=repository_accuracy,
            cross_reference_issues=cross_ref_issues,
            recommendations=recommendations,
            generated_at=datetime.utcnow(),
        )

    async def _assess_completeness(self, saidata: SaiData) -> QualityScore:
        """Assess completeness of saidata."""
        issues = []
        suggestions = []
        details = {}

        # Required fields score
        required_fields = ["metadata.name", "metadata.description", "version"]
        missing_required = []

        if not saidata.metadata.name:
            missing_required.append("metadata.name")
        if not saidata.metadata.description:
            missing_required.append("metadata.description")
        if not saidata.version:
            missing_required.append("version")

        required_score = max(0.0, 1.0 - (len(missing_required) / len(required_fields)))
        details["required_fields_score"] = required_score
        details["missing_required"] = missing_required

        # Optional but important fields
        important_fields = [
            ("metadata.category", saidata.metadata.category),
            ("metadata.license", saidata.metadata.license),
            (
                "metadata.urls.website",
                saidata.metadata.urls.website if saidata.metadata.urls else None,
            ),
            ("providers", bool(saidata.providers)),
            ("packages", bool(saidata.packages)),
        ]

        missing_important = []
        for field_name, field_value in important_fields:
            if not field_value:
                missing_important.append(field_name)

        important_score = max(0.0, 1.0 - (len(missing_important) / len(important_fields)))
        details["important_fields_score"] = important_score
        details["missing_important"] = missing_important

        # Provider coverage score
        provider_score = 0.0
        if saidata.providers:
            common_providers = ["apt", "dnf", "brew", "winget", "docker"]
            covered_providers = [p for p in common_providers if p in saidata.providers]
            provider_score = len(covered_providers) / len(common_providers)
            details["provider_coverage"] = len(covered_providers)
            details["covered_providers"] = covered_providers

        details["provider_score"] = provider_score

        # Calculate weighted completeness score
        completeness_score = (
            (required_score * 0.5) + (important_score * 0.3) + (provider_score * 0.2)
        )

        # Generate issues and suggestions
        if missing_required:
            issues.append(f"Missing required fields: {', '.join(missing_required)}")
            suggestions.append("Add all required metadata fields")

        if missing_important:
            suggestions.append(f"Consider adding important fields: {', '.join(missing_important)}")

        if provider_score < 0.5:
            suggestions.append("Add support for more common package managers")

        return QualityScore(
            metric=QualityMetric.COMPLETENESS,
            score=completeness_score,
            max_score=1.0,
            details=details,
            issues=issues,
            suggestions=suggestions,
        )

    async def _assess_consistency(self, saidata: SaiData) -> QualityScore:
        """Assess internal consistency of saidata."""
        issues = []
        suggestions = []
        details = {}
        consistency_score = 1.0

        # Name consistency across metadata
        name_issues = []
        if saidata.metadata.name and saidata.metadata.display_name:
            if saidata.metadata.name.lower() != saidata.metadata.display_name.lower():
                # Check if they're reasonably similar
                similarity = self._calculate_string_similarity(
                    saidata.metadata.name.lower(), saidata.metadata.display_name.lower()
                )
                if similarity < 0.7:
                    name_issues.append("name and display_name are significantly different")
                    consistency_score -= 0.1

        details["name_consistency"] = len(name_issues) == 0

        # Version consistency
        version_issues = []
        if saidata.metadata.version and saidata.version:
            if saidata.metadata.version != saidata.version:
                version_issues.append("metadata.version differs from root version")
                consistency_score -= 0.1

        details["version_consistency"] = len(version_issues) == 0

        # Package name consistency across providers
        package_name_issues = []
        if saidata.providers:
            all_package_names = set()
            for provider_name, provider_config in saidata.providers.items():
                if provider_config.packages:
                    for package in provider_config.packages:
                        all_package_names.add(package.name)

            # Check if package names are reasonable variations
            if len(all_package_names) > 1:
                base_name = saidata.metadata.name.lower() if saidata.metadata.name else ""
                inconsistent_names = []
                for pkg_name in all_package_names:
                    similarity = self._calculate_string_similarity(base_name, pkg_name.lower())
                    if similarity < 0.5:
                        inconsistent_names.append(pkg_name)

                if inconsistent_names:
                    package_name_issues.append(
                        f"Package names inconsistent with metadata name: {inconsistent_names}"
                    )
                    consistency_score -= 0.1

        details["package_name_consistency"] = len(package_name_issues) == 0

        # Port consistency
        port_issues = []
        if saidata.ports and saidata.providers:
            global_ports = {port.port for port in saidata.ports}
            for provider_name, provider_config in saidata.providers.items():
                if provider_config.ports:
                    provider_ports = {port.port for port in provider_config.ports}
                    if not provider_ports.issubset(global_ports):
                        port_issues.append(
                            f"Provider {provider_name} has ports not in global ports"
                        )
                        consistency_score -= 0.05

        details["port_consistency"] = len(port_issues) == 0

        # Collect all issues
        all_issues = name_issues + version_issues + package_name_issues + port_issues
        issues.extend(all_issues)

        # Generate suggestions
        if name_issues:
            suggestions.append("Ensure name and display_name are consistent or clearly related")
        if version_issues:
            suggestions.append("Synchronize version fields across metadata and root level")
        if package_name_issues:
            suggestions.append("Verify package names are correct for each provider")
        if port_issues:
            suggestions.append("Ensure provider-specific ports are also defined globally")

        details["total_issues"] = len(all_issues)
        consistency_score = max(0.0, consistency_score)

        return QualityScore(
            metric=QualityMetric.CONSISTENCY,
            score=consistency_score,
            max_score=1.0,
            details=details,
            issues=issues,
            suggestions=suggestions,
        )

    async def _assess_metadata_richness(self, saidata: SaiData) -> QualityScore:
        """Assess richness of metadata."""
        issues = []
        suggestions = []
        details = {}

        # Count populated metadata fields
        metadata_fields = [
            ("name", saidata.metadata.name),
            ("display_name", saidata.metadata.display_name),
            ("description", saidata.metadata.description),
            ("version", saidata.metadata.version),
            ("category", saidata.metadata.category),
            ("subcategory", saidata.metadata.subcategory),
            ("tags", saidata.metadata.tags),
            ("license", saidata.metadata.license),
            ("language", saidata.metadata.language),
            ("maintainer", saidata.metadata.maintainer),
        ]

        populated_basic = sum(1 for _, value in metadata_fields if value)
        basic_richness = populated_basic / len(metadata_fields)
        details["basic_metadata_richness"] = basic_richness
        details["populated_basic_fields"] = populated_basic

        # URL richness
        url_richness = 0.0
        if saidata.metadata.urls:
            url_fields = [
                ("website", saidata.metadata.urls.website),
                ("documentation", saidata.metadata.urls.documentation),
                ("source", saidata.metadata.urls.source),
                ("issues", saidata.metadata.urls.issues),
                ("download", saidata.metadata.urls.download),
            ]
            populated_urls = sum(1 for _, value in url_fields if value)
            url_richness = populated_urls / len(url_fields)

        details["url_richness"] = url_richness

        # Security metadata richness
        security_richness = 0.0
        if saidata.metadata.security:
            security_fields = [
                ("cve_exceptions", saidata.metadata.security.cve_exceptions),
                ("security_contact", saidata.metadata.security.security_contact),
                ("vulnerability_disclosure", saidata.metadata.security.vulnerability_disclosure),
                ("sbom_url", saidata.metadata.security.sbom_url),
                ("signing_key", saidata.metadata.security.signing_key),
            ]
            populated_security = sum(1 for _, value in security_fields if value)
            security_richness = populated_security / len(security_fields)

        details["security_richness"] = security_richness

        # Description quality
        description_quality = 0.0
        if saidata.metadata.description:
            desc_len = len(saidata.metadata.description)
            if desc_len < 20:
                description_quality = 0.3
                suggestions.append("Provide a more detailed description (at least 20 characters)")
            elif desc_len < 50:
                description_quality = 0.6
                suggestions.append("Consider expanding the description for better clarity")
            elif desc_len < 100:
                description_quality = 0.8
            else:
                description_quality = 1.0
        else:
            issues.append("Missing description")

        details["description_quality"] = description_quality

        # Tags quality
        tags_quality = 0.0
        if saidata.metadata.tags:
            tag_count = len(saidata.metadata.tags)
            if tag_count >= 3:
                tags_quality = 1.0
            elif tag_count >= 2:
                tags_quality = 0.7
            elif tag_count >= 1:
                tags_quality = 0.4
        else:
            suggestions.append("Add relevant tags to improve discoverability")

        details["tags_quality"] = tags_quality

        # Calculate overall richness score
        richness_score = (
            basic_richness * 0.4
            + url_richness * 0.2
            + security_richness * 0.1
            + description_quality * 0.2
            + tags_quality * 0.1
        )

        # Generate suggestions based on missing elements
        if basic_richness < 0.7:
            suggestions.append(
                "Add more basic metadata fields (category, license, maintainer, etc.)"
            )
        if url_richness < 0.5:
            suggestions.append("Add relevant URLs (website, documentation, source)")
        if security_richness == 0.0:
            suggestions.append("Consider adding security metadata if applicable")

        return QualityScore(
            metric=QualityMetric.METADATA_RICHNESS,
            score=richness_score,
            max_score=1.0,
            details=details,
            issues=issues,
            suggestions=suggestions,
        )

    async def _assess_cross_reference_integrity(self, saidata: SaiData) -> QualityScore:
        """Assess cross-reference integrity within saidata."""
        issues = []
        suggestions = []
        details = {}
        integrity_score = 1.0

        # Collect all repository names
        repository_names = set()
        if saidata.providers:
            for provider_config in saidata.providers.values():
                if provider_config.repositories:
                    for repo in provider_config.repositories:
                        repository_names.add(repo.name)

        details["total_repositories"] = len(repository_names)

        # Check repository references in packages
        undefined_repo_refs = set()
        total_package_refs = 0

        if saidata.providers:
            for provider_name, provider_config in saidata.providers.items():
                if provider_config.packages:
                    for package in provider_config.packages:
                        if package.repository:
                            total_package_refs += 1
                            if package.repository not in repository_names:
                                undefined_repo_refs.add(package.repository)
                                issues.append(
                                    f"Package '{
                                        package.name}' references undefined repository '{
                                        package.repository}'")
                                integrity_score -= 0.1

        details["total_package_repository_refs"] = total_package_refs
        details["undefined_repository_refs"] = list(undefined_repo_refs)

        # Check service references
        undefined_service_refs = set()
        service_names = set()

        # Collect service names
        if saidata.services:
            for service in saidata.services:
                service_names.add(service.name)

        if saidata.providers:
            for provider_config in saidata.providers.values():
                if provider_config.services:
                    for service in provider_config.services:
                        service_names.add(service.name)

        # Check port service references
        if saidata.ports:
            for port in saidata.ports:
                if port.service and port.service not in service_names:
                    undefined_service_refs.add(port.service)
                    issues.append(f"Port {port.port} references undefined service '{port.service}'")
                    integrity_score -= 0.05

        details["undefined_service_refs"] = list(undefined_service_refs)

        # Check file/directory consistency
        file_path_conflicts = []
        all_file_paths = set()

        # Collect all file paths
        if saidata.files:
            for file in saidata.files:
                if file.path in all_file_paths:
                    file_path_conflicts.append(file.path)
                all_file_paths.add(file.path)

        if saidata.providers:
            for provider_config in saidata.providers.values():
                if provider_config.files:
                    for file in provider_config.files:
                        if file.path in all_file_paths:
                            file_path_conflicts.append(file.path)
                        all_file_paths.add(file.path)

        if file_path_conflicts:
            issues.extend([f"Duplicate file path: {path}" for path in file_path_conflicts])
            integrity_score -= len(file_path_conflicts) * 0.02

        details["file_path_conflicts"] = file_path_conflicts

        # Check command name conflicts
        command_name_conflicts = []
        all_command_names = set()

        if saidata.commands:
            for command in saidata.commands:
                if command.name in all_command_names:
                    command_name_conflicts.append(command.name)
                all_command_names.add(command.name)

        if saidata.providers:
            for provider_config in saidata.providers.values():
                if provider_config.commands:
                    for command in provider_config.commands:
                        if command.name in all_command_names:
                            command_name_conflicts.append(command.name)
                        all_command_names.add(command.name)

        if command_name_conflicts:
            issues.extend([f"Duplicate command name: {name}" for name in command_name_conflicts])
            integrity_score -= len(command_name_conflicts) * 0.02

        details["command_name_conflicts"] = command_name_conflicts

        # Generate suggestions
        if undefined_repo_refs:
            suggestions.append("Define all repositories referenced by packages")
        if undefined_service_refs:
            suggestions.append("Define all services referenced by ports")
        if file_path_conflicts:
            suggestions.append("Resolve duplicate file path definitions")
        if command_name_conflicts:
            suggestions.append("Resolve duplicate command name definitions")

        integrity_score = max(0.0, integrity_score)
        details["integrity_issues"] = len(issues)

        return QualityScore(
            metric=QualityMetric.CROSS_REFERENCE_INTEGRITY,
            score=integrity_score,
            max_score=1.0,
            details=details,
            issues=issues,
            suggestions=suggestions,
        )

    async def _assess_repository_alignment(self, saidata: SaiData) -> QualityScore:
        """Assess alignment with repository data."""
        issues = []
        suggestions = []
        details = {}
        alignment_score = 1.0

        if not saidata.providers:
            return QualityScore(
                metric=QualityMetric.REPOSITORY_ALIGNMENT,
                score=0.0,
                max_score=1.0,
                details={"status": "no_providers"},
                issues=["No providers defined"],
                suggestions=["Add provider configurations"],
            )

        # Check each provider's packages against repository data
        provider_alignments = {}

        for provider_name, provider_config in saidata.providers.items():
            if not provider_config.packages:
                continue

            provider_alignment = await self._check_provider_alignment(
                provider_name, provider_config.packages
            )
            provider_alignments[provider_name] = provider_alignment

            if provider_alignment["score"] < 0.8:
                issues.append(
                    f"Low repository alignment for provider {provider_name}: {
                        provider_alignment['score']:.2f}")

            alignment_score *= provider_alignment["score"]

        details["provider_alignments"] = provider_alignments

        # Generate suggestions based on alignment issues
        for provider_name, alignment in provider_alignments.items():
            if alignment["missing_packages"]:
                suggestions.append(
                    f"Verify package names for {provider_name}: {alignment['missing_packages']}"
                )
            if alignment["version_mismatches"]:
                suggestions.append(f"Check version specifications for {provider_name}")

        return QualityScore(
            metric=QualityMetric.REPOSITORY_ALIGNMENT,
            score=alignment_score,
            max_score=1.0,
            details=details,
            issues=issues,
            suggestions=suggestions,
        )

    async def _assess_accuracy(self, saidata: SaiData) -> QualityScore:
        """Assess overall accuracy against repository data."""
        issues = []
        suggestions = []
        details = {}

        # This is a comprehensive accuracy check
        accuracy_factors = []

        # Package name accuracy
        if saidata.providers:
            total_packages = 0
            accurate_packages = 0

            for provider_name, provider_config in saidata.providers.items():
                if provider_config.packages:
                    for package in provider_config.packages:
                        total_packages += 1
                        # Check if package exists in repository
                        if await self._package_exists_in_repository(provider_name, package.name):
                            accurate_packages += 1
                        else:
                            issues.append(
                                f"Package '{package.name}' not found in {provider_name} repository"
                            )

            package_accuracy = accurate_packages / total_packages if total_packages > 0 else 0.0
            accuracy_factors.append(package_accuracy)
            details["package_accuracy"] = package_accuracy
            details["accurate_packages"] = accurate_packages
            details["total_packages"] = total_packages

        # Metadata accuracy (based on repository data)
        metadata_accuracy = await self._check_metadata_accuracy(saidata)
        accuracy_factors.append(metadata_accuracy)
        details["metadata_accuracy"] = metadata_accuracy

        # Calculate overall accuracy
        overall_accuracy = (
            sum(accuracy_factors) / len(accuracy_factors) if accuracy_factors else 0.0
        )

        if overall_accuracy < 0.8:
            suggestions.append(
                "Review and verify package names and metadata against repository sources"
            )
        if overall_accuracy < 0.6:
            suggestions.append("Consider regenerating saidata with updated repository data")

        return QualityScore(
            metric=QualityMetric.ACCURACY,
            score=overall_accuracy,
            max_score=1.0,
            details=details,
            issues=issues,
            suggestions=suggestions,
        )

    async def _check_repository_accuracy(self, saidata: SaiData) -> Dict[str, float]:
        """Check accuracy against repository data for each provider."""
        accuracy_scores = {}

        if not saidata.providers:
            return accuracy_scores

        for provider_name, provider_config in saidata.providers.items():
            if not provider_config.packages:
                accuracy_scores[provider_name] = 1.0
                continue

            total_packages = len(provider_config.packages)
            accurate_count = 0

            for package in provider_config.packages:
                if await self._package_exists_in_repository(provider_name, package.name):
                    accurate_count += 1

            accuracy_scores[provider_name] = (
                accurate_count / total_packages if total_packages > 0 else 0.0
            )

        return accuracy_scores

    async def _validate_cross_references_advanced(self, saidata: SaiData) -> List[ValidationError]:
        """Advanced cross-reference validation."""
        errors = []

        # This extends the base validator's cross-reference checking
        # with more sophisticated analysis

        # Check for circular dependencies in packages
        if saidata.providers:
            for provider_name, provider_config in saidata.providers.items():
                if provider_config.packages:
                    circular_deps = self._detect_circular_dependencies(provider_config.packages)
                    for cycle in circular_deps:
                        errors.append(
                            ValidationError(
                                severity=ValidationSeverity.WARNING,
                                message=f"Potential circular dependency detected: {
                                    ' -> '.join(cycle)}",
                                path=f"providers.{provider_name}.packages",
                                code="circular_dependency",
                                suggestion="Review package dependencies to avoid circular references",
                            ))

        # Check for orphaned configurations
        orphaned_configs = self._detect_orphaned_configurations(saidata)
        for config_type, items in orphaned_configs.items():
            for item in items:
                errors.append(
                    ValidationError(
                        severity=ValidationSeverity.INFO,
                        message=f"Orphaned {config_type}: {item}",
                        path=config_type,
                        code="orphaned_configuration",
                        suggestion=f"Consider removing unused {config_type} or link it to a provider",
                    ))

        return errors

    async def _check_provider_alignment(
        self, provider_name: str, packages: List[Any]
    ) -> Dict[str, Any]:
        """Check alignment of provider packages with repository data."""
        alignment_result = {
            "score": 1.0,
            "total_packages": len(packages),
            "found_packages": 0,
            "missing_packages": [],
            "version_mismatches": [],
            "details": {},
        }

        for package in packages:
            exists = await self._package_exists_in_repository(provider_name, package.name)
            if exists:
                alignment_result["found_packages"] += 1

                # Check version if specified
                if package.version:
                    repo_package = await self._get_repository_package(provider_name, package.name)
                    if repo_package and repo_package.version != package.version:
                        alignment_result["version_mismatches"].append(
                            {
                                "package": package.name,
                                "saidata_version": package.version,
                                "repository_version": repo_package.version,
                            }
                        )
            else:
                alignment_result["missing_packages"].append(package.name)

        # Calculate alignment score
        if alignment_result["total_packages"] > 0:
            base_score = alignment_result["found_packages"] / alignment_result["total_packages"]
            version_penalty = len(alignment_result["version_mismatches"]) * 0.1
            alignment_result["score"] = max(0.0, base_score - version_penalty)

        return alignment_result

    async def _package_exists_in_repository(self, provider_name: str, package_name: str) -> bool:
        """Check if package exists in repository."""
        try:
            # Map provider names to repository types
            provider_mapping = {
                "apt": "apt",
                "dnf": "dnf",
                "yum": "yum",
                "brew": "brew",
                "winget": "winget",
                "docker": "docker",
            }

            repo_type = provider_mapping.get(provider_name.lower())
            if not repo_type:
                return True  # Assume valid if we can't check

            # Search for package in repository
            search_result = await self.repository_manager.search_packages(
                query=package_name, repository_type=repo_type, limit=1
            )

            # Check for exact match
            for pkg in search_result.packages:
                if pkg.name.lower() == package_name.lower():
                    return True

            return False

        except Exception:
            # If we can't check, assume it's valid
            return True

    async def _get_repository_package(
        self, provider_name: str, package_name: str
    ) -> Optional[RepositoryPackage]:
        """Get package details from repository."""
        try:
            provider_mapping = {
                "apt": "apt",
                "dnf": "dnf",
                "yum": "yum",
                "brew": "brew",
                "winget": "winget",
                "docker": "docker",
            }

            repo_type = provider_mapping.get(provider_name.lower())
            if not repo_type:
                return None

            return await self.repository_manager.get_package_details(
                package_name=package_name, repository_type=repo_type
            )

        except Exception:
            return None

    async def _check_metadata_accuracy(self, saidata: SaiData) -> float:
        """Check metadata accuracy against repository data."""
        if not saidata.metadata.name:
            return 0.0

        try:
            # Search for the software across repositories
            search_result = await self.repository_manager.search_packages(
                query=saidata.metadata.name, limit=5
            )

            if not search_result.packages:
                return 0.5  # No repository data to compare against

            # Find best matching package
            best_match = None
            best_similarity = 0.0

            for pkg in search_result.packages:
                similarity = self._calculate_string_similarity(
                    saidata.metadata.name.lower(), pkg.name.lower()
                )
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = pkg

            if not best_match or best_similarity < 0.7:
                return 0.5

            # Compare metadata fields
            accuracy_factors = []

            # Description similarity
            if saidata.metadata.description and best_match.description:
                desc_similarity = self._calculate_string_similarity(
                    saidata.metadata.description.lower(), best_match.description.lower()
                )
                accuracy_factors.append(desc_similarity)

            # Homepage URL match
            if saidata.metadata.urls and saidata.metadata.urls.website and best_match.homepage:
                url_match = saidata.metadata.urls.website.lower() == best_match.homepage.lower()
                accuracy_factors.append(1.0 if url_match else 0.5)

            # License match
            if saidata.metadata.license and best_match.license:
                license_similarity = self._calculate_string_similarity(
                    saidata.metadata.license.lower(), best_match.license.lower()
                )
                accuracy_factors.append(license_similarity)

            return sum(accuracy_factors) / len(accuracy_factors) if accuracy_factors else 0.8

        except Exception:
            return 0.5

    def _calculate_overall_score(self, metric_scores: Dict[QualityMetric, QualityScore]) -> float:
        """Calculate weighted overall quality score."""
        total_weighted_score = 0.0
        total_weight = 0.0

        for metric, score in metric_scores.items():
            weight = self.metric_weights.get(metric, 0.1)
            total_weighted_score += score.score * weight
            total_weight += weight

        return total_weighted_score / total_weight if total_weight > 0 else 0.0

    def _generate_recommendations(
        self, metric_scores: Dict[QualityMetric, QualityScore], validation_result: ValidationResult
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        # Schema validation recommendations
        if validation_result.has_errors:
            recommendations.append("Fix schema validation errors before proceeding")

        # Metric-specific recommendations
        for metric, score in metric_scores.items():
            if score.score < 0.7:
                recommendations.extend(score.suggestions[:2])  # Top 2 suggestions per metric

        # Priority recommendations based on scores
        lowest_score_metric = min(metric_scores.items(), key=lambda x: x[1].score)
        if lowest_score_metric[1].score < 0.5:
            recommendations.insert(
                0, f"Priority: Improve {
                    lowest_score_metric[0].value} (score: {
                    lowest_score_metric[1].score:.2f})", )

        return recommendations[:10]  # Limit to top 10 recommendations

    def _calculate_string_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings using Levenshtein distance."""
        # Handle empty strings
        if len(str1) == 0 and len(str2) == 0:
            return 1.0
        if len(str1) == 0 or len(str2) == 0:
            return 0.0

        # Simple Levenshtein distance implementation
        len1, len2 = len(str1), len(str2)

        # Create matrix
        matrix = [[0] * (len2 + 1) for _ in range(len1 + 1)]

        # Initialize first row and column
        for i in range(len1 + 1):
            matrix[i][0] = i
        for j in range(len2 + 1):
            matrix[0][j] = j

        # Fill matrix
        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                cost = 0 if str1[i - 1] == str2[j - 1] else 1
                matrix[i][j] = min(
                    matrix[i - 1][j] + 1,  # deletion
                    matrix[i][j - 1] + 1,  # insertion
                    matrix[i - 1][j - 1] + cost,  # substitution
                )

        # Calculate similarity
        max_len = max(len1, len2)
        distance = matrix[len1][len2]
        return 1.0 - (distance / max_len)

    def _detect_circular_dependencies(self, packages: List[Any]) -> List[List[str]]:
        """Detect circular dependencies in package list."""
        # Note: Current Package model doesn't have dependencies field
        # This is a placeholder for future enhancement when dependencies are added
        # For now, return empty list as no circular dependencies can be detected
        return []

    def _detect_orphaned_configurations(self, saidata: SaiData) -> Dict[str, List[str]]:
        """Detect configurations not linked to any provider."""
        orphaned = {
            "services": [],
            "files": [],
            "directories": [],
            "commands": [],
            "ports": [],
            "containers": [],
        }

        # Collect items used by providers
        provider_items = {
            "services": set(),
            "files": set(),
            "directories": set(),
            "commands": set(),
            "ports": set(),
            "containers": set(),
        }

        if saidata.providers:
            for provider_config in saidata.providers.values():
                if provider_config.services:
                    provider_items["services"].update(s.name for s in provider_config.services)
                if provider_config.files:
                    provider_items["files"].update(f.name for f in provider_config.files)
                if provider_config.directories:
                    provider_items["directories"].update(
                        d.name for d in provider_config.directories
                    )
                if provider_config.commands:
                    provider_items["commands"].update(c.name for c in provider_config.commands)
                if provider_config.ports:
                    provider_items["ports"].update(str(p.port) for p in provider_config.ports)
                if provider_config.containers:
                    provider_items["containers"].update(c.name for c in provider_config.containers)

        # Check global items
        if saidata.services:
            for service in saidata.services:
                if service.name not in provider_items["services"]:
                    orphaned["services"].append(service.name)

        if saidata.files:
            for file in saidata.files:
                if file.name not in provider_items["files"]:
                    orphaned["files"].append(file.name)

        if saidata.directories:
            for directory in saidata.directories:
                if directory.name not in provider_items["directories"]:
                    orphaned["directories"].append(directory.name)

        if saidata.commands:
            for command in saidata.commands:
                if command.name not in provider_items["commands"]:
                    orphaned["commands"].append(command.name)

        if saidata.ports:
            for port in saidata.ports:
                if str(port.port) not in provider_items["ports"]:
                    orphaned["ports"].append(str(port.port))

        if saidata.containers:
            for container in saidata.containers:
                if container.name not in provider_items["containers"]:
                    orphaned["containers"].append(container.name)

        # Remove empty lists
        return {k: v for k, v in orphaned.items() if v}

    def format_quality_report(self, report: QualityReport, detailed: bool = False) -> str:
        """Format quality report as human-readable text.

        Args:
            report: Quality report to format
            detailed: Whether to include detailed information

        Returns:
            Formatted quality report string
        """
        lines = []

        # Header
        lines.append("=" * 60)
        lines.append("SAIDATA QUALITY REPORT")
        lines.append("=" * 60)
        lines.append(f"Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        lines.append("")

        # Overall score
        score_emoji = (
            "🟢" if report.overall_score >= 0.8 else "🟡" if report.overall_score >= 0.6 else "🔴"
        )
        lines.append(f"Overall Quality Score: {score_emoji} {report.overall_score:.2f}/1.00")
        lines.append("")

        # Schema validation summary
        if report.validation_result.has_errors:
            lines.append("❌ Schema Validation: FAILED")
            lines.append(f"   Errors: {len(report.validation_result.errors)}")
        else:
            lines.append("✅ Schema Validation: PASSED")

        if report.validation_result.has_warnings:
            lines.append(f"   Warnings: {len(report.validation_result.warnings)}")
        lines.append("")

        # Quality metrics
        lines.append("Quality Metrics:")
        lines.append("-" * 40)

        for metric, score in report.metric_scores.items():
            score_bar = self._create_score_bar(score.score)
            lines.append(
                f"{metric.value.replace('_', ' ').title():<25} {score_bar} {score.score:.2f}"
            )

            if detailed and score.issues:
                for issue in score.issues[:3]:  # Show top 3 issues
                    lines.append(f"  ⚠️  {issue}")

        lines.append("")

        # Repository accuracy
        if report.repository_accuracy:
            lines.append("Repository Accuracy:")
            lines.append("-" * 40)
            for provider, accuracy in report.repository_accuracy.items():
                accuracy_bar = self._create_score_bar(accuracy)
                lines.append(f"{provider:<15} {accuracy_bar} {accuracy:.2f}")
            lines.append("")

        # Cross-reference issues
        if report.cross_reference_issues:
            lines.append("Cross-Reference Issues:")
            lines.append("-" * 40)
            for issue in report.cross_reference_issues[:5]:  # Show top 5
                severity_icon = "❌" if issue.severity == ValidationSeverity.ERROR else "⚠️"
                lines.append(f"{severity_icon} {issue.message}")

            if len(report.cross_reference_issues) > 5:
                lines.append(f"... and {len(report.cross_reference_issues) - 5} more issues")
            lines.append("")

        # Recommendations
        if report.recommendations:
            lines.append("Recommendations:")
            lines.append("-" * 40)
            for i, rec in enumerate(report.recommendations[:8], 1):  # Show top 8
                lines.append(f"{i}. {rec}")
            lines.append("")

        # Detailed metrics (if requested)
        if detailed:
            lines.append("Detailed Metrics:")
            lines.append("=" * 40)
            for metric, score in report.metric_scores.items():
                lines.append(f"\n{metric.value.replace('_', ' ').title()}:")
                lines.append(f"Score: {score.score:.3f}/{score.max_score}")

                if score.details:
                    lines.append("Details:")
                    for key, value in score.details.items():
                        if isinstance(value, (int, float)):
                            lines.append(f"  {key}: {value}")
                        elif isinstance(value, list) and len(value) <= 5:
                            lines.append(f"  {key}: {value}")
                        elif isinstance(value, bool):
                            lines.append(f"  {key}: {'✅' if value else '❌'}")

                if score.suggestions:
                    lines.append("Suggestions:")
                    for suggestion in score.suggestions:
                        lines.append(f"  • {suggestion}")

        return "\n".join(lines)

    def _create_score_bar(self, score: float, width: int = 20) -> str:
        """Create a visual score bar."""
        filled = int(score * width)
        empty = width - filled

        if score >= 0.8:
            pass
        elif score >= 0.6:
            pass
        else:
            pass

        return f"[{'█' * filled}{'░' * empty}]"
