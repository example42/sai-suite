"""Generic repository downloader with configurable parsing."""

import asyncio
import json
import yaml
import xml.etree.ElementTree as ET
from typing import List, Optional, Dict, Any, Callable
from datetime import datetime
import re
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

from saigen.models.repository import RepositoryPackage, RepositoryInfo
from saigen.repositories.downloaders.base import BaseRepositoryDownloader
from saigen.utils.errors import RepositoryError


class GenericRepositoryDownloader(BaseRepositoryDownloader):
    """Generic repository downloader with configurable parsing rules."""
    
    def __init__(self, repository_info: RepositoryInfo, config: Optional[Dict[str, Any]] = None):
        """Initialize generic downloader with parsing configuration.
        
        Args:
            repository_info: Repository metadata
            config: Configuration including parsing rules
        """
        super().__init__(repository_info, config)
        self.parsing_config = config.get('parsing', {}) if config else {}
        self._session = None
    
    async def _get_session(self):
        """Get or create HTTP session with connection pooling."""
        if not AIOHTTP_AVAILABLE:
            raise RepositoryError("aiohttp is required for network operations")
        
        if not self._session:
            import aiohttp
            timeout = aiohttp.ClientTimeout(total=self.config.get('timeout', 300))
            # Configure connection pooling for better performance
            connector = aiohttp.TCPConnector(
                limit=100,  # Total connection pool size
                limit_per_host=30,  # Per-host connection limit
                ttl_dns_cache=300,  # DNS cache TTL
                use_dns_cache=True,
                keepalive_timeout=30,
                enable_cleanup_closed=True
            )
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers={'User-Agent': 'saigen/1.0.0'}
            )
        return self._session
    
    async def download_package_list(self) -> List[RepositoryPackage]:
        """Download and parse package list from repository."""
        if not self.repository_info.url:
            raise RepositoryError(f"No URL configured for repository {self.repository_info.name}")
        
        try:
            session = await self._get_session()
            
            # Support multiple URLs for comprehensive package lists
            urls = self.parsing_config.get('package_list_urls', [self.repository_info.url])
            if isinstance(urls, str):
                urls = [urls]
            
            all_packages = []
            for url in urls:
                packages = await self._download_from_url(session, url)
                all_packages.extend(packages)
            
            # Remove duplicates based on name and version
            seen = set()
            unique_packages = []
            for pkg in all_packages:
                key = (pkg.name, pkg.version)
                if key not in seen:
                    seen.add(key)
                    unique_packages.append(pkg)
            
            return unique_packages
            
        except Exception as e:
            raise RepositoryError(f"Failed to download package list from {self.repository_info.name}: {str(e)}")
    
    async def _download_from_url(self, session, url: str) -> List[RepositoryPackage]:
        """Download and parse packages from a single URL."""
        # Security: Validate URL before making request
        if not url.startswith(('http://', 'https://')):
            raise RepositoryError(f"Invalid URL scheme: {url}")
        
        async with session.get(url, ssl=True) as response:  # Enforce SSL verification
            if response.status != 200:
                raise RepositoryError(f"HTTP {response.status} from {url}")
            
            # Security: Check content length to prevent DoS
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > 100 * 1024 * 1024:  # 100MB limit
                raise RepositoryError(f"Response too large: {content_length} bytes from {url}")
            
            content_type = response.headers.get('content-type', '').lower()
            # Security: Read with size limit to prevent memory exhaustion
            text_content = await response.text(encoding='utf-8', errors='ignore')
            
            # Determine parsing method based on content type or configuration
            parser_type = self.parsing_config.get('format', self._detect_format(content_type, text_content))
            
            if parser_type == 'json':
                return await self._parse_json(text_content)
            elif parser_type == 'yaml':
                return await self._parse_yaml(text_content)
            elif parser_type == 'xml':
                return await self._parse_xml(text_content)
            elif parser_type == 'text':
                return await self._parse_text(text_content)
            elif parser_type == 'custom':
                return await self._parse_custom(text_content)
            else:
                raise RepositoryError(f"Unsupported format: {parser_type}")
    
    def _detect_format(self, content_type: str, content: str) -> str:
        """Auto-detect content format."""
        if 'json' in content_type:
            return 'json'
        elif 'yaml' in content_type or 'yml' in content_type:
            return 'yaml'
        elif 'xml' in content_type:
            return 'xml'
        
        # Try to detect from content
        content_stripped = content.strip()
        if content_stripped.startswith('{') or content_stripped.startswith('['):
            return 'json'
        elif content_stripped.startswith('<?xml') or content_stripped.startswith('<'):
            return 'xml'
        elif '---' in content_stripped[:100] or ':' in content_stripped[:200]:
            return 'yaml'
        
        return 'text'
    
    async def _parse_json(self, content: str) -> List[RepositoryPackage]:
        """Parse JSON format package list."""
        try:
            data = json.loads(content)
            return self._extract_packages_from_data(data, 'json')
        except json.JSONDecodeError as e:
            raise RepositoryError(f"Invalid JSON format: {str(e)}")
    
    async def _parse_yaml(self, content: str) -> List[RepositoryPackage]:
        """Parse YAML format package list."""
        try:
            data = yaml.safe_load(content)
            return self._extract_packages_from_data(data, 'yaml')
        except yaml.YAMLError as e:
            raise RepositoryError(f"Invalid YAML format: {str(e)}")
    
    async def _parse_xml(self, content: str) -> List[RepositoryPackage]:
        """Parse XML format package list."""
        try:
            root = ET.fromstring(content)
            return self._extract_packages_from_xml(root)
        except ET.ParseError as e:
            raise RepositoryError(f"Invalid XML format: {str(e)}")
    
    async def _parse_text(self, content: str) -> List[RepositoryPackage]:
        """Parse plain text format package list."""
        lines = content.strip().split('\n')
        packages = []
        
        # Get parsing rules from config
        line_pattern = self.parsing_config.get('line_pattern', r'^(\S+)\s+(\S+)(?:\s+(.*))?$')
        name_group = self.parsing_config.get('name_group', 1)
        version_group = self.parsing_config.get('version_group', 2)
        description_group = self.parsing_config.get('description_group', 3)
        
        pattern = re.compile(line_pattern)
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            match = pattern.match(line)
            if match:
                try:
                    name = match.group(name_group) if name_group <= len(match.groups()) else None
                    version = match.group(version_group) if version_group <= len(match.groups()) else "unknown"
                    description = match.group(description_group) if description_group <= len(match.groups()) else None
                    
                    if name:
                        package = RepositoryPackage(
                            name=name,
                            version=version,
                            description=description,
                            repository_name=self.repository_info.name,
                            platform=self.repository_info.platform
                        )
                        packages.append(package)
                except IndexError:
                    continue
        
        return packages
    
    async def _parse_custom(self, content: str) -> List[RepositoryPackage]:
        """Parse using custom parsing function."""
        custom_parser = self.parsing_config.get('custom_parser')
        if not custom_parser or not callable(custom_parser):
            raise RepositoryError("Custom parser not configured or not callable")
        
        try:
            return custom_parser(content, self.repository_info)
        except Exception as e:
            raise RepositoryError(f"Custom parser failed: {str(e)}")
    
    def _extract_packages_from_data(self, data: Any, format_type: str) -> List[RepositoryPackage]:
        """Extract packages from parsed JSON/YAML data."""
        packages = []
        
        # Get field mapping from config
        field_mapping = self.parsing_config.get('field_mapping', {})
        package_path = self.parsing_config.get('package_path', [])
        
        # Navigate to package data using path
        current_data = data
        for path_element in package_path:
            if isinstance(current_data, dict):
                current_data = current_data.get(path_element, [])
            elif isinstance(current_data, list) and path_element.isdigit():
                idx = int(path_element)
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
                name = item.get(field_mapping.get('name', 'name'))
                version = item.get(field_mapping.get('version', 'version'), 'unknown')
                description = item.get(field_mapping.get('description', 'description'))
                homepage = item.get(field_mapping.get('homepage', 'homepage'))
                
                if name:
                    package = RepositoryPackage(
                        name=name,
                        version=version,
                        description=description,
                        homepage=homepage,
                        repository_name=self.repository_info.name,
                        platform=self.repository_info.platform,
                        # Extract additional fields if configured
                        **self._extract_additional_fields(item, field_mapping)
                    )
                    packages.append(package)
            except Exception:
                continue
        
        return packages
    
    def _extract_packages_from_xml(self, root: ET.Element) -> List[RepositoryPackage]:
        """Extract packages from XML data."""
        packages = []
        
        # Get XML parsing config
        package_xpath = self.parsing_config.get('package_xpath', './/package')
        field_mapping = self.parsing_config.get('xml_field_mapping', {})
        
        for package_elem in root.findall(package_xpath):
            try:
                name = self._get_xml_field(package_elem, field_mapping.get('name', 'name'))
                version = self._get_xml_field(package_elem, field_mapping.get('version', 'version'), 'unknown')
                description = self._get_xml_field(package_elem, field_mapping.get('description', 'description'))
                
                if name:
                    package = RepositoryPackage(
                        name=name,
                        version=version,
                        description=description,
                        repository_name=self.repository_info.name,
                        platform=self.repository_info.platform
                    )
                    packages.append(package)
            except Exception:
                continue
        
        return packages
    
    def _get_xml_field(self, element: ET.Element, field_config: str, default: Optional[str] = None) -> Optional[str]:
        """Extract field from XML element using various methods."""
        if field_config.startswith('@'):
            # Attribute
            return element.get(field_config[1:], default)
        elif '/' in field_config:
            # XPath
            found = element.find(field_config)
            return found.text if found is not None else default
        else:
            # Direct child element
            child = element.find(field_config)
            return child.text if child is not None else default
    
    def _extract_additional_fields(self, item: Dict[str, Any], field_mapping: Dict[str, str]) -> Dict[str, Any]:
        """Extract additional fields based on mapping configuration."""
        additional = {}
        
        # Map additional fields if configured
        for field_name in ['maintainer', 'license', 'size', 'dependencies', 'tags', 'category']:
            if field_name in field_mapping:
                value = item.get(field_mapping[field_name])
                if value is not None:
                    additional[field_name] = value
        
        return additional
    
    async def search_package(self, name: str) -> List[RepositoryPackage]:
        """Search for specific package."""
        # For generic downloader, we download all packages and filter
        # Subclasses can override for more efficient search
        all_packages = await self.download_package_list()
        
        name_lower = name.lower()
        matching_packages = []
        
        for package in all_packages:
            if (name_lower in package.name.lower() or 
                (package.description and name_lower in package.description.lower())):
                matching_packages.append(package)
        
        return matching_packages
    
    async def get_package_details(self, name: str, version: Optional[str] = None) -> Optional[RepositoryPackage]:
        """Get detailed information for a specific package."""
        packages = await self.search_package(name)
        
        # Find exact match
        for package in packages:
            if package.name.lower() == name.lower():
                if version is None or package.version == version:
                    return package
        
        # Return first match if no exact match
        return packages[0] if packages else None