"""Enhanced RPM repository metadata parser for repomd.xml format."""

import gzip
import logging
import xml.etree.ElementTree as ET
from typing import Any, Dict, List
from urllib.parse import urljoin, urlparse

from saigen.models.repository import RepositoryInfo, RepositoryPackage
from saigen.utils.errors import RepositoryError

logger = logging.getLogger(__name__)

# XML namespaces used in RPM metadata
REPO_NS = {"repo": "http://linux.duke.edu/metadata/repo"}
COMMON_NS = {"common": "http://linux.duke.edu/metadata/common"}
RPM_NS = {"rpm": "http://linux.duke.edu/metadata/rpm"}


async def parse_rpm_repomd(
    content: str, config: Dict[str, Any], repository_info: RepositoryInfo
) -> List[RepositoryPackage]:
    """Parse RPM repository metadata (repomd.xml format).
    
    This parser handles the two-step process:
    1. Parse repomd.xml to find primary.xml.gz location
    2. Download and parse primary.xml.gz for package list
    
    Also handles Fedora metalink format that redirects to mirrors.
    
    Args:
        content: The repomd.xml content (or metalink XML)
        config: Parsing configuration (should include 'base_url' key)
        repository_info: Repository metadata
        
    Returns:
        List of packages found in the repository
    """
    try:
        logger.debug(f"Parsing repomd.xml for {repository_info.name}, content length: {len(content)}")
        root = ET.fromstring(content)
        
        # Check if this is a metalink file (Fedora uses this)
        if root.tag.endswith("metalink") or "metalink" in root.tag.lower():
            logger.debug(f"Detected metalink format for {repository_info.name}")
            # Extract first mirror URL and download repomd.xml from there
            mirror_url = await _get_mirror_from_metalink(root, repository_info)
            if mirror_url:
                # Download repomd.xml from mirror
                repomd_content = await _download_repomd_from_mirror(mirror_url, repository_info)
                # Update config with the mirror's base URL for recursive parsing
                mirror_config = config.copy()
                # Extract base URL from mirror_url (remove /repodata/repomd.xml)
                if "/repodata/repomd.xml" in mirror_url:
                    mirror_config["base_url"] = mirror_url.rsplit("/repodata/", 1)[0] + "/"
                # Recursively parse the actual repomd.xml
                return await parse_rpm_repomd(repomd_content, mirror_config, repository_info)
            else:
                logger.warning(f"No mirrors found in metalink for {repository_info.name}")
                return []
        
        # Find the primary.xml.gz location in repomd.xml
        primary_location = _find_primary_location(root)
        
        if not primary_location:
            logger.warning(f"No primary metadata found in repomd.xml for {repository_info.name}")
            logger.debug(f"Content preview: {content[:500]}")
            return []
        
        # Get the base URL from config (passed by downloader) or repository info
        base_url = config.get("base_url") or _get_base_url(repository_info)
        logger.debug(f"Base URL: {base_url}")
        
        # Construct full URL to primary.xml.gz
        primary_url = urljoin(base_url, primary_location)
        
        logger.debug(f"Downloading primary metadata from: {primary_url}")
        
        # Download and parse primary.xml.gz
        packages = await _download_and_parse_primary(primary_url, config, repository_info)
        
        logger.info(f"Parsed {len(packages)} packages from {repository_info.name}")
        return packages
        
    except ET.ParseError as e:
        raise RepositoryError(f"Invalid RPM repomd.xml: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to parse RPM metadata: {e}")
        raise RepositoryError(f"Failed to parse RPM metadata: {str(e)}")


async def _get_mirror_from_metalink(root: ET.Element, repository_info: RepositoryInfo) -> str:
    """Extract a mirror URL from metalink XML.
    
    Args:
        root: Root element of metalink XML
        repository_info: Repository metadata
        
    Returns:
        Mirror URL or empty string if not found
    """
    # Try to find repomd.xml URL in metalink
    # Metalink format: <file name="repomd.xml"><resources><url>http://mirror.../repodata/repomd.xml</url></resources></file>
    
    # Try with namespace - prefer https URLs
    https_urls = []
    http_urls = []
    
    for url_elem in root.findall(".//{http://www.metalinker.org/}url"):
        url_text = url_elem.text
        protocol = url_elem.get("protocol", "")
        
        if url_text and "repodata/repomd.xml" in url_text:
            if protocol == "https" or url_text.startswith("https://"):
                https_urls.append(url_text)
            elif protocol == "http" or url_text.startswith("http://"):
                http_urls.append(url_text)
    
    # Try without namespace
    if not https_urls and not http_urls:
        for url_elem in root.findall(".//url"):
            url_text = url_elem.text
            protocol = url_elem.get("protocol", "")
            
            if url_text and "repodata/repomd.xml" in url_text:
                if protocol == "https" or url_text.startswith("https://"):
                    https_urls.append(url_text)
                elif protocol == "http" or url_text.startswith("http://"):
                    http_urls.append(url_text)
    
    # Prefer https over http
    if https_urls:
        mirror_url = https_urls[0]
        logger.debug(f"Found HTTPS mirror URL in metalink: {mirror_url}")
        return mirror_url
    elif http_urls:
        mirror_url = http_urls[0]
        logger.debug(f"Found HTTP mirror URL in metalink: {mirror_url}")
        return mirror_url
    
    return ""


async def _download_repomd_from_mirror(url: str, repository_info: RepositoryInfo) -> str:
    """Download repomd.xml from a mirror URL.
    
    Args:
        url: URL to repomd.xml on mirror
        repository_info: Repository metadata
        
    Returns:
        Content of repomd.xml
    """
    try:
        import aiohttp
        
        timeout = aiohttp.ClientTimeout(total=60)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, ssl=True) as response:
                if response.status != 200:
                    raise RepositoryError(f"HTTP {response.status} from mirror {url}")
                
                content = await response.text()
                logger.debug(f"Downloaded repomd.xml from mirror, length: {len(content)}")
                return content
                
    except Exception as e:
        logger.error(f"Failed to download repomd.xml from mirror {url}: {e}")
        raise RepositoryError(f"Failed to download from mirror: {str(e)}")


def _find_primary_location(root: ET.Element) -> str:
    """Find the location of primary.xml.gz in repomd.xml.
    
    Args:
        root: Root element of repomd.xml
        
    Returns:
        Relative path to primary.xml.gz or empty string if not found
    """
    # Try with namespace
    for data in root.findall(".//repo:data[@type='primary']", REPO_NS):
        location = data.find("repo:location", REPO_NS)
        if location is not None:
            href = location.get("href")
            if href:
                logger.debug(f"Found primary location (with namespace): {href}")
                return href
    
    # Try without namespace (some repos don't use it)
    for data in root.findall(".//data[@type='primary']"):
        location = data.find("location")
        if location is not None:
            href = location.get("href")
            if href:
                logger.debug(f"Found primary location (without namespace): {href}")
                return href
    
    logger.warning("No primary location found in repomd.xml")
    return ""


def _get_base_url(repository_info: RepositoryInfo) -> str:
    """Extract base URL from repository info.
    
    Args:
        repository_info: Repository metadata
        
    Returns:
        Base URL for the repository
    """
    # Get the packages URL from repository info
    # This should be the repomd.xml URL, we need to get its directory
    if hasattr(repository_info, 'url') and repository_info.url:
        url = repository_info.url
    else:
        # Fallback: construct from name
        url = ""
    
    # Remove repomd.xml from the end if present
    if url.endswith("repomd.xml"):
        url = url.rsplit("/", 1)[0] + "/"
    elif not url.endswith("/"):
        url += "/"
    
    return url


async def _download_and_parse_primary(
    url: str, config: Dict[str, Any], repository_info: RepositoryInfo
) -> List[RepositoryPackage]:
    """Download and parse primary.xml.gz or primary.xml.zst file.
    
    Args:
        url: URL to primary.xml.gz or primary.xml.zst
        config: Parsing configuration
        repository_info: Repository metadata
        
    Returns:
        List of packages
    """
    try:
        # Import aiohttp here to avoid import errors if not installed
        import aiohttp
        
        # Create a session with timeout
        timeout = aiohttp.ClientTimeout(total=300)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, ssl=True) as response:
                if response.status != 200:
                    raise RepositoryError(f"HTTP {response.status} from {url}")
                
                # Read compressed content
                compressed_content = await response.read()
                
                # Decompress based on file extension
                if url.endswith(".zst"):
                    # Zstandard compression
                    try:
                        import zstandard as zstd
                        dctx = zstd.ZstdDecompressor()
                        xml_content = dctx.decompress(compressed_content, max_output_size=500*1024*1024)  # 500MB max
                    except ImportError:
                        raise RepositoryError(
                            f"Zstandard compression is required for {repository_info.name} but the 'zstandard' "
                            "package is not installed. Install it with: pip install zstandard"
                        )
                    except Exception as e:
                        # Try alternative decompression method
                        try:
                            import zstandard as zstd
                            dctx = zstd.ZstdDecompressor()
                            # Use streaming decompression for large files
                            xml_content = b""
                            with dctx.stream_reader(compressed_content) as reader:
                                while True:
                                    chunk = reader.read(16384)
                                    if not chunk:
                                        break
                                    xml_content += chunk
                        except Exception as e2:
                            raise RepositoryError(f"Failed to decompress primary.xml.zst: {e}, {e2}")
                else:
                    # Gzip compression (default)
                    try:
                        xml_content = gzip.decompress(compressed_content)
                    except Exception as e:
                        raise RepositoryError(f"Failed to decompress primary.xml.gz: {e}")
                
                # Parse XML
                xml_text = xml_content.decode("utf-8", errors="ignore")
                return _parse_primary_xml(xml_text, config, repository_info)
                
    except Exception as e:
        logger.error(f"Failed to download/parse primary metadata from {url}: {e}")
        raise RepositoryError(f"Failed to download primary metadata: {str(e)}")


def _parse_primary_xml(
    xml_content: str, config: Dict[str, Any], repository_info: RepositoryInfo
) -> List[RepositoryPackage]:
    """Parse primary.xml content to extract package information.
    
    Args:
        xml_content: XML content of primary.xml
        config: Parsing configuration
        repository_info: Repository metadata
        
    Returns:
        List of packages
    """
    try:
        logger.debug(f"Parsing primary.xml, content length: {len(xml_content)}")
        root = ET.fromstring(xml_content)
        packages = []
        
        # Get field mapping from config
        fields = config.get("fields", {})
        
        # Find all package elements (try with and without namespace)
        package_elements = root.findall(".//common:package", COMMON_NS)
        logger.debug(f"Found {len(package_elements)} package elements with namespace")
        
        if not package_elements:
            package_elements = root.findall(".//package")
            logger.debug(f"Found {len(package_elements)} package elements without namespace")
        
        for pkg_elem in package_elements:
            try:
                package = _parse_package_element(pkg_elem, fields, repository_info)
                if package:
                    packages.append(package)
            except Exception as e:
                logger.debug(f"Failed to parse package element: {e}")
                continue
        
        logger.debug(f"Successfully parsed {len(packages)} packages")
        return packages
        
    except ET.ParseError as e:
        raise RepositoryError(f"Invalid primary.xml: {str(e)}")


def _parse_package_element(
    elem: ET.Element, fields: Dict[str, str], repository_info: RepositoryInfo
) -> RepositoryPackage:
    """Parse a single package element from primary.xml.
    
    Args:
        elem: Package XML element
        fields: Field mapping configuration
        repository_info: Repository metadata
        
    Returns:
        RepositoryPackage object or None if parsing fails
    """
    # Use full namespace URIs for reliable parsing
    ns_common = "{http://linux.duke.edu/metadata/common}"
    ns_rpm = "{http://linux.duke.edu/metadata/rpm}"
    
    # Extract name (required)
    name_elem = elem.find(f"{ns_common}name")
    if name_elem is None or not name_elem.text:
        return None
    name = name_elem.text.strip()
    
    # Extract version
    version = "unknown"
    version_elem = elem.find(f"{ns_common}version")
    if version_elem is not None:
        # Version is typically in attributes: ver, rel, epoch
        ver = version_elem.get("ver", "")
        rel = version_elem.get("rel", "")
        if ver:
            version = f"{ver}-{rel}" if rel else ver
    
    # Extract description/summary
    description = None
    desc_elem = elem.find(f"{ns_common}description")
    if desc_elem is not None and desc_elem.text:
        description = desc_elem.text.strip()
    else:
        # Try summary as fallback
        summary_elem = elem.find(f"{ns_common}summary")
        if summary_elem is not None and summary_elem.text:
            description = summary_elem.text.strip()
    
    # Extract URL/homepage
    homepage = None
    url_elem = elem.find(f"{ns_common}url")
    if url_elem is not None and url_elem.text:
        homepage = url_elem.text.strip()
    
    # Extract packager/maintainer
    maintainer = None
    packager_elem = elem.find(f"{ns_common}packager")
    if packager_elem is not None and packager_elem.text:
        maintainer = packager_elem.text.strip()
    
    # Extract license
    license_info = None
    format_elem = elem.find(f"{ns_common}format")
    if format_elem is not None:
        license_elem = format_elem.find(f"{ns_rpm}license")
        if license_elem is not None and license_elem.text:
            license_info = license_elem.text.strip()
    
    # Extract size
    size = None
    size_elem = elem.find(f"{ns_common}size")
    if size_elem is not None:
        package_size = size_elem.get("package")
        if package_size:
            try:
                size = int(package_size)
            except ValueError:
                pass
    
    # Extract group/category
    category = None
    if format_elem is not None:
        group_elem = format_elem.find(f"{ns_rpm}group")
        if group_elem is not None and group_elem.text:
            category = group_elem.text.strip()
    
    # Create package object
    return RepositoryPackage(
        name=name,
        version=version,
        description=description,
        homepage=homepage,
        license=license_info,
        maintainer=maintainer,
        size=size,
        category=category,
        repository_name=repository_info.name,
        platform=repository_info.platform,
    )
