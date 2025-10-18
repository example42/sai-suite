"""Parser registry and common parsing functions for repository data."""

import json
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, List, Optional

import yaml

from saigen.models.repository import RepositoryInfo, RepositoryPackage
from saigen.utils.errors import RepositoryError

logger = logging.getLogger(__name__)

# Type alias for parser functions
ParserFunction = Callable[[str, Dict[str, Any], RepositoryInfo], Awaitable[List[RepositoryPackage]]]


class ParserRegistry:
    """Registry of parsing functions for different repository formats."""

    def __init__(self):
        """Initialize parser registry with built-in parsers."""
        self._parsers: Dict[str, ParserFunction] = {}

        # Register built-in parsers
        self._register_builtin_parsers()

    def _register_builtin_parsers(self) -> None:
        """Register built-in parsing functions."""
        self.register_parser("json", parse_json_format)
        self.register_parser("yaml", parse_yaml_format)
        self.register_parser("xml", parse_xml_format)
        self.register_parser("text", parse_text_format)
        self.register_parser("debian_packages", parse_debian_packages)
        self.register_parser("rpm_metadata", parse_rpm_metadata)
        self.register_parser("html", parse_html_format)
        self.register_parser("csv", parse_csv_format)
        self.register_parser("tsv", parse_tsv_format)

        # GitHub-specific parsers
        from saigen.repositories.parsers.github import parse_github_directory

        self.register_parser("github_directory", parse_github_directory)

    def register_parser(self, format_name: str, parser_func: ParserFunction) -> None:
        """Register a parser function for a format.

        Args:
            format_name: Name of the format
            parser_func: Async parser function
        """
        self._parsers[format_name] = parser_func
        logger.debug(f"Registered parser for format: {format_name}")

    def get_parser(self, format_name: str) -> Optional[ParserFunction]:
        """Get parser function for a format.

        Args:
            format_name: Name of the format

        Returns:
            Parser function or None if not found
        """
        return self._parsers.get(format_name)


# Built-in parser functions


async def parse_json_format(
    content: str, config: Dict[str, Any], repository_info: RepositoryInfo
) -> List[RepositoryPackage]:
    """Parse JSON format repository data."""
    try:
        data = json.loads(content)
        return extract_packages_from_data(data, config, repository_info, "json")
    except json.JSONDecodeError as e:
        raise RepositoryError(f"Invalid JSON format: {str(e)}")


async def parse_yaml_format(
    content: str, config: Dict[str, Any], repository_info: RepositoryInfo
) -> List[RepositoryPackage]:
    """Parse YAML format repository data."""
    try:
        data = yaml.safe_load(content)
        return extract_packages_from_data(data, config, repository_info, "yaml")
    except yaml.YAMLError as e:
        raise RepositoryError(f"Invalid YAML format: {str(e)}")


async def parse_xml_format(
    content: str, config: Dict[str, Any], repository_info: RepositoryInfo
) -> List[RepositoryPackage]:
    """Parse XML format repository data."""
    try:
        root = ET.fromstring(content)
        return extract_packages_from_xml(root, config, repository_info)
    except ET.ParseError as e:
        raise RepositoryError(f"Invalid XML format: {str(e)}")


async def parse_text_format(
    content: str, config: Dict[str, Any], repository_info: RepositoryInfo
) -> List[RepositoryPackage]:
    """Parse plain text format repository data."""
    lines = content.strip().split("\n")
    packages = []

    # Get parsing patterns from config
    patterns = config.get("patterns", {})
    line_pattern = patterns.get("line_pattern", r"^(\S+)\s+(\S+)(?:\s+(.*))?$")
    name_group = patterns.get("name_group", 1)
    version_group = patterns.get("version_group", 2)
    description_group = patterns.get("description_group", 3)

    pattern = re.compile(line_pattern)

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        match = pattern.match(line)
        if match:
            try:
                name = match.group(name_group) if name_group <= len(match.groups()) else None
                version = (
                    match.group(version_group)
                    if version_group <= len(match.groups())
                    else "unknown"
                )
                description = (
                    match.group(description_group)
                    if description_group <= len(match.groups())
                    else None
                )

                if name:
                    package = RepositoryPackage(
                        name=name,
                        version=version,
                        description=description,
                        repository_name=repository_info.name,
                        platform=repository_info.platform,
                    )
                    packages.append(package)
            except IndexError:
                continue

    return packages


async def parse_debian_packages(
    content: str, config: Dict[str, Any], repository_info: RepositoryInfo
) -> List[RepositoryPackage]:
    """Parse Debian Packages file format."""
    packages = []
    current_package = {}

    lines = content.split("\n")

    for line in lines:
        line = line.rstrip()

        # Empty line indicates end of package entry
        if not line:
            if current_package:
                package = create_package_from_debian_fields(current_package, repository_info)
                if package:
                    packages.append(package)
                current_package = {}
            continue

        # Continuation line (starts with space or tab)
        if line.startswith(" ") or line.startswith("\t"):
            if current_package:
                # Get the last field and append to it
                last_field = list(current_package.keys())[-1] if current_package else None
                if last_field:
                    current_package[last_field] += "\n" + line.strip()
            continue

        # Field line
        if ":" in line:
            field, value = line.split(":", 1)
            field = field.strip().lower()
            value = value.strip()
            current_package[field] = value

    # Handle last package if file doesn't end with empty line
    if current_package:
        package = create_package_from_debian_fields(current_package, repository_info)
        if package:
            packages.append(package)

    return packages


async def parse_rpm_metadata(
    content: str, config: Dict[str, Any], repository_info: RepositoryInfo
) -> List[RepositoryPackage]:
    """Parse RPM repository metadata (repomd.xml format)."""
    try:
        root = ET.fromstring(content)

        # Handle different RPM metadata formats
        packages = []

        # Try to find package elements
        for package_elem in root.findall(".//package"):
            package = create_package_from_rpm_element(package_elem, repository_info)
            if package:
                packages.append(package)

        return packages

    except ET.ParseError as e:
        raise RepositoryError(f"Invalid RPM metadata XML: {str(e)}")


async def parse_html_format(
    content: str, config: Dict[str, Any], repository_info: RepositoryInfo
) -> List[RepositoryPackage]:
    """Parse HTML format (basic link extraction)."""
    packages = []

    # Simple regex-based HTML parsing for package links
    # This is a basic implementation - more sophisticated parsing may be needed
    link_pattern = r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]+)</a>'

    for match in re.finditer(link_pattern, content, re.IGNORECASE):
        href = match.group(1)
        text = match.group(2).strip()

        # Try to extract package name and version from link text
        if text and not text.startswith(".."):
            # Basic package name extraction
            name = text
            version = "unknown"

            # Try to extract version from filename
            version_match = re.search(r"[-_](\d+(?:\.\d+)*)", text)
            if version_match:
                version = version_match.group(1)
                name = text[: version_match.start()]

            package = RepositoryPackage(
                name=name,
                version=version,
                download_url=href,
                repository_name=repository_info.name,
                platform=repository_info.platform,
            )
            packages.append(package)

    return packages


async def parse_csv_format(
    content: str, config: Dict[str, Any], repository_info: RepositoryInfo
) -> List[RepositoryPackage]:
    """Parse CSV format repository data."""
    import csv
    from io import StringIO

    packages = []

    # Get field mapping from config
    fields = config.get("fields", {})

    try:
        reader = csv.DictReader(StringIO(content))

        for row in reader:
            name = row.get(fields.get("name", "name"))
            if name:
                package = RepositoryPackage(
                    name=name,
                    version=row.get(fields.get("version", "version"), "unknown"),
                    description=row.get(fields.get("description", "description")),
                    homepage=row.get(fields.get("homepage", "homepage")),
                    license=row.get(fields.get("license", "license")),
                    maintainer=row.get(fields.get("maintainer", "maintainer")),
                    repository_name=repository_info.name,
                    platform=repository_info.platform,
                )
                packages.append(package)

    except Exception as e:
        raise RepositoryError(f"Failed to parse CSV: {e}")

    return packages


async def parse_tsv_format(
    content: str, config: Dict[str, Any], repository_info: RepositoryInfo
) -> List[RepositoryPackage]:
    """Parse TSV (Tab-Separated Values) format repository data."""
    import csv
    from io import StringIO

    packages = []

    # Get field mapping from config
    fields = config.get("fields", {})

    try:
        reader = csv.DictReader(StringIO(content), delimiter="\t")

        for row in reader:
            name = row.get(fields.get("name", "name"))
            if name:
                package = RepositoryPackage(
                    name=name,
                    version=row.get(fields.get("version", "version"), "unknown"),
                    description=row.get(fields.get("description", "description")),
                    homepage=row.get(fields.get("homepage", "homepage")),
                    license=row.get(fields.get("license", "license")),
                    maintainer=row.get(fields.get("maintainer", "maintainer")),
                    repository_name=repository_info.name,
                    platform=repository_info.platform,
                )
                packages.append(package)

    except Exception as e:
        raise RepositoryError(f"Failed to parse TSV: {e}")

    return packages


# Helper functions


def extract_packages_from_data(
    data: Any, config: Dict[str, Any], repository_info: RepositoryInfo, format_type: str
) -> List[RepositoryPackage]:
    """Extract packages from parsed JSON/YAML data."""
    packages = []

    # Get field mapping and path configuration
    fields = config.get("fields", {})
    patterns = config.get("patterns", {})
    json_path = patterns.get("json_path", "")

    # Navigate to package data using JSON path
    current_data = data
    if json_path:
        path_parts = json_path.split(".")
        for part in path_parts:
            if isinstance(current_data, dict):
                current_data = current_data.get(part, [])
            elif isinstance(current_data, list) and part.isdigit():
                idx = int(part)
                current_data = current_data[idx] if idx < len(current_data) else []

    # Ensure we have a list of packages
    if isinstance(current_data, dict):
        current_data = [current_data]
    elif not isinstance(current_data, list):
        current_data = []

    for item in current_data:
        if not isinstance(item, dict):
            continue

        try:
            # Extract fields using mapping or defaults
            name = get_nested_value(item, fields.get("name", "name"))
            version = get_nested_value(item, fields.get("version", "version")) or "unknown"
            description = get_nested_value(item, fields.get("description", "description"))
            homepage = get_nested_value(item, fields.get("homepage", "homepage"))
            license_info = get_nested_value(item, fields.get("license", "license"))
            maintainer = get_nested_value(item, fields.get("maintainer", "maintainer"))
            dependencies = get_nested_value(item, fields.get("dependencies", "dependencies"))
            size = get_nested_value(item, fields.get("size", "size"))
            category = get_nested_value(item, fields.get("category", "category"))
            tags = get_nested_value(item, fields.get("tags", "tags"))
            download_url = get_nested_value(item, fields.get("download_url", "download_url"))

            if name:
                # Convert dependencies to list if it's a string
                if isinstance(dependencies, str):
                    dependencies = [dep.strip() for dep in dependencies.split(",") if dep.strip()]

                # Convert tags to list if it's a string
                if isinstance(tags, str):
                    tags = [tag.strip() for tag in tags.split(",") if tag.strip()]

                # Convert size to integer if it's a string
                if isinstance(size, str) and size.isdigit():
                    size = int(size)

                package = RepositoryPackage(
                    name=name,
                    version=version,
                    description=description,
                    homepage=homepage,
                    license=license_info,
                    maintainer=maintainer,
                    dependencies=dependencies if dependencies else None,
                    size=size,
                    category=category,
                    tags=tags if tags else None,
                    download_url=download_url,
                    repository_name=repository_info.name,
                    platform=repository_info.platform,
                    last_updated=datetime.utcnow(),
                )
                packages.append(package)
        except Exception as e:
            logger.debug(f"Failed to parse package item: {e}")
            continue

    return packages


def extract_packages_from_xml(
    root: ET.Element, config: Dict[str, Any], repository_info: RepositoryInfo
) -> List[RepositoryPackage]:
    """Extract packages from XML data."""
    packages = []

    # Get XML parsing config
    patterns = config.get("patterns", {})
    package_xpath = patterns.get("package_xpath", ".//package")
    fields = config.get("fields", {})

    for package_elem in root.findall(package_xpath):
        try:
            name = get_xml_field(package_elem, fields.get("name", "name"))
            version = get_xml_field(package_elem, fields.get("version", "version"), "unknown")
            description = get_xml_field(package_elem, fields.get("description", "description"))
            homepage = get_xml_field(package_elem, fields.get("homepage", "homepage"))
            license_info = get_xml_field(package_elem, fields.get("license", "license"))
            maintainer = get_xml_field(package_elem, fields.get("maintainer", "maintainer"))

            if name:
                package = RepositoryPackage(
                    name=name,
                    version=version,
                    description=description,
                    homepage=homepage,
                    license=license_info,
                    maintainer=maintainer,
                    repository_name=repository_info.name,
                    platform=repository_info.platform,
                )
                packages.append(package)
        except Exception as e:
            logger.debug(f"Failed to parse XML package element: {e}")
            continue

    return packages


def get_nested_value(data: Dict[str, Any], field_path: str) -> Any:
    """Get nested value from dictionary using dot notation."""
    if not field_path:
        return None

    current = data
    for part in field_path.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None

        if current is None:
            return None

    return current


def get_xml_field(
    element: ET.Element, field_config: str, default: Optional[str] = None
) -> Optional[str]:
    """Extract field from XML element using various methods."""
    if not field_config:
        return default

    if field_config.startswith("@"):
        # Attribute
        return element.get(field_config[1:], default)
    elif "/" in field_config:
        # XPath
        found = element.find(field_config)
        return found.text if found is not None else default
    else:
        # Direct child element
        child = element.find(field_config)
        return child.text if child is not None else default


def create_package_from_debian_fields(
    fields: Dict[str, str], repository_info: RepositoryInfo
) -> Optional[RepositoryPackage]:
    """Create RepositoryPackage from Debian package fields."""
    name = fields.get("package")
    if not name:
        return None

    version = fields.get("version", "unknown")
    description = fields.get("description", fields.get("summary"))
    homepage = fields.get("homepage")
    maintainer = fields.get("maintainer")

    # Parse dependencies
    dependencies = []
    depends = fields.get("depends", "")
    if depends:
        deps = depends.replace("|", ",").split(",")
        for dep in deps:
            dep = dep.strip()
            if dep and "(" not in dep:  # Skip versioned dependencies for simplicity
                dependencies.append(dep)

    # Get size
    size = None
    installed_size = fields.get("installed-size")
    if installed_size:
        try:
            size = int(installed_size) * 1024  # Convert KB to bytes
        except ValueError:
            pass

    # Get section (category)
    section = fields.get("section")

    return RepositoryPackage(
        name=name,
        version=version,
        description=description,
        homepage=homepage,
        maintainer=maintainer,
        dependencies=dependencies if dependencies else None,
        size=size,
        category=section,
        repository_name=repository_info.name,
        platform=repository_info.platform,
    )


def create_package_from_rpm_element(
    element: ET.Element, repository_info: RepositoryInfo
) -> Optional[RepositoryPackage]:
    """Create RepositoryPackage from RPM package XML element."""
    name = element.get("name") or get_xml_field(element, "name")
    if not name:
        return None

    version = element.get("version") or get_xml_field(element, "version", "unknown")
    description = get_xml_field(element, "description") or get_xml_field(element, "summary")
    homepage = get_xml_field(element, "url") or get_xml_field(element, "homepage")
    license_info = get_xml_field(element, "license")
    maintainer = get_xml_field(element, "packager")

    return RepositoryPackage(
        name=name,
        version=version,
        description=description,
        homepage=homepage,
        license=license_info,
        maintainer=maintainer,
        repository_name=repository_info.name,
        platform=repository_info.platform,
    )
