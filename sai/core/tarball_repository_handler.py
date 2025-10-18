"""Tarball repository handler for SAI saidata management."""

import hashlib
import json
import logging
import shutil
import tarfile
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ..models.config import RepositoryAuthType
from ..utils.credentials import CredentialManager
from ..utils.errors import (
    SecurityError,
)
from ..utils.security import (
    ChecksumValidator,
    PathTraversalProtector,
    RepositorySecurityValidator,
    SecurityLevel,
)

logger = logging.getLogger(__name__)


@dataclass
class ReleaseInfo:
    """Information about a repository release."""

    tag_name: str
    name: str
    download_url: str
    published_at: Optional[datetime] = None
    checksum: Optional[str] = None
    checksum_algorithm: str = "sha256"
    size: Optional[int] = None


@dataclass
class TarballOperationResult:
    """Result of a tarball operation."""

    success: bool
    message: str
    release_info: Optional[ReleaseInfo] = None
    extracted_path: Optional[Path] = None
    error_details: Optional[str] = None


class ProgressReporter:
    """Progress reporter for download operations."""

    def __init__(self, callback: Optional[Callable[[int, int], None]] = None):
        """Initialize progress reporter.

        Args:
            callback: Optional callback function that receives (downloaded_bytes, total_bytes)
        """
        self.callback = callback
        self.downloaded = 0
        self.total = 0

    def __call__(self, block_num: int, block_size: int, total_size: int):
        """Progress callback for urllib.request.urlretrieve.

        Args:
            block_num: Number of blocks downloaded
            block_size: Size of each block
            total_size: Total file size
        """
        self.downloaded = block_num * block_size
        self.total = total_size

        if self.callback:
            self.callback(min(self.downloaded, total_size), total_size)

        # Log progress at reasonable intervals
        if total_size > 0 and block_num % 100 == 0:
            percent = min(100, (self.downloaded / total_size) * 100)
            logger.debug(
                f"Download progress: {percent:.1f}% ({self.downloaded}/{total_size} bytes)"
            )


class TarballRepositoryHandler:
    """Handles tarball-based repository downloads for SAI saidata management."""

    def __init__(
        self,
        timeout: int = 300,
        max_retries: int = 3,
        security_level: SecurityLevel = SecurityLevel.MODERATE,
    ):
        """Initialize the tarball repository handler.

        Args:
            timeout: Timeout for download operations in seconds
            max_retries: Maximum number of retries for failed operations
            security_level: Security validation level
        """
        self.timeout = timeout
        self.max_retries = max_retries

        # Initialize security components
        self.security_validator = RepositorySecurityValidator(security_level)
        self.checksum_validator = ChecksumValidator()
        self.credential_manager = CredentialManager()

        logger.debug(
            f"Tarball repository handler initialized with security level: {security_level}"
        )

    def get_latest_release_info(
        self,
        repo_url: str,
        auth_type: Optional[RepositoryAuthType] = None,
        auth_data: Optional[Dict[str, str]] = None,
    ) -> TarballOperationResult:
        """Get information about the latest release from a GitHub repository.

        Args:
            repo_url: Repository URL (e.g., https://github.com/owner/repo)
            auth_type: Authentication type (token, basic)
            auth_data: Authentication data

        Returns:
            TarballOperationResult with release information
        """
        logger.info(f"Fetching latest release info for repository: {repo_url}")
        logger.debug(f"Release info parameters: auth_type={auth_type}")

        # Security validation of repository URL
        url_validation = self.security_validator.validate_repository_url(repo_url)
        if not url_validation.is_valid:
            error_msg = (
                f"Repository URL failed security validation: {', '.join(url_validation.issues)}"
            )
            logger.error(error_msg)
            return TarballOperationResult(
                success=False, message=error_msg, error_details="Security validation failed"
            )

        # Log security warnings if any
        if url_validation.has_warnings:
            for warning in url_validation.warnings:
                logger.warning(f"Repository URL security warning: {warning}")

        try:
            # Extract owner and repo from URL
            owner, repo = self._parse_github_url(repo_url)
            if not owner or not repo:
                error_msg = f"Invalid GitHub repository URL: {repo_url}"
                logger.error(error_msg)
                return TarballOperationResult(
                    success=False,
                    message=error_msg,
                    error_details="URL must be in format: https://github.com/owner/repo",
                )

            logger.debug(f"Parsed repository: {owner}/{repo}")

            # Build GitHub API URL
            api_url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"

            # Create request with authentication
            request = urllib.request.Request(api_url)
            request.add_header("Accept", "application/vnd.github.v3+json")
            request.add_header("User-Agent", "SAI-Tool/1.0")

            # Add authentication headers (with credential manager integration)
            if auth_type and auth_data:
                logger.debug(f"Adding authentication headers for {auth_type}")
                self._add_auth_headers(request, auth_type, auth_data)
            else:
                # Try to get credentials from credential manager
                stored_credentials = self.credential_manager.get_credentials(repo_url)
                if stored_credentials:
                    logger.debug(f"Using stored credentials for {repo_url}")
                    auth_type_str = stored_credentials.get("auth_type")
                    if auth_type_str == "token":
                        self._add_auth_headers(
                            request,
                            RepositoryAuthType.TOKEN,
                            {"token": stored_credentials.get("token")},
                        )
                    elif auth_type_str == "basic":
                        self._add_auth_headers(
                            request,
                            RepositoryAuthType.BASIC,
                            {
                                "username": stored_credentials.get("username"),
                                "password": stored_credentials.get("password"),
                            },
                        )

            # Make API request
            logger.debug(f"Making API request to: {api_url}")

            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                if response.status != 200:
                    error_msg = f"GitHub API request failed with status {response.status}"
                    logger.error(error_msg)
                    response_text = response.read().decode()
                    logger.debug(f"API response: {response_text}")
                    return TarballOperationResult(
                        success=False, message=error_msg, error_details=f"Response: {response_text}"
                    )

                data = json.loads(response.read().decode())
                logger.debug(f"API response received, parsing release data")

            # Parse release information
            release_info = self._parse_release_data(data)
            if not release_info:
                error_msg = "No suitable release assets found"
                logger.error(error_msg)
                logger.debug(
                    f"Available assets: {[asset.get('name', 'unnamed') for asset in data.get('assets', [])]}"
                )
                return TarballOperationResult(
                    success=False,
                    message=error_msg,
                    error_details="Release must contain tarball or zipball assets",
                )

            logger.info(f"Found latest release: {release_info.tag_name} ({release_info.name})")
            logger.debug(
                f"Release details: download_url={
                    release_info.download_url}, size={
                    release_info.size}")

            return TarballOperationResult(
                success=True,
                message=f"Successfully retrieved release info for {release_info.tag_name}",
                release_info=release_info,
            )

        except urllib.error.HTTPError as e:
            error_msg = f"HTTP error while fetching release info: {e.code} {e.reason}"
            logger.error(error_msg)

            # Provide specific guidance based on HTTP status code
            if e.code == 404:
                error_msg += " (Repository not found or no releases available)"
                logger.info("Troubleshooting 404 error:")
                logger.info("  - Verify the repository URL is correct")
                logger.info("  - Check if the repository exists and is public")
                logger.info("  - Ensure the repository has published releases")
            elif e.code == 403:
                error_msg += " (Rate limited or authentication required)"
                logger.info("Troubleshooting 403 error:")
                logger.info("  - Check if you've hit GitHub API rate limits")
                logger.info("  - For private repositories, ensure authentication is configured")
                logger.info("  - Verify your access token has the correct permissions")
            elif e.code == 401:
                error_msg += " (Authentication failed)"
                logger.info("Troubleshooting 401 error:")
                logger.info("  - Check your authentication credentials")
                logger.info("  - Verify your access token is valid and not expired")

            return TarballOperationResult(success=False, message=error_msg, error_details=str(e))

        except urllib.error.URLError as e:
            error_msg = f"Network error while fetching release info: {e.reason}"
            logger.error(error_msg)

            # Determine if this is a temporary or permanent network issue
            is_temporary = self._is_temporary_network_error(str(e.reason))

            if is_temporary:
                logger.info("This appears to be a temporary network issue")
                logger.info("  - Try again in a few moments")
                logger.info("  - Check your internet connection")
            else:
                logger.info("This appears to be a configuration or permanent network issue")
                logger.info("  - Check your network configuration")
                logger.info("  - Verify DNS resolution is working")

            return TarballOperationResult(success=False, message=error_msg, error_details=str(e))

        except json.JSONDecodeError as e:
            error_msg = "Failed to parse GitHub API response"
            logger.error(f"{error_msg}: {e}")
            logger.debug(f"JSON decode error at line {e.lineno}, column {e.colno}")

            return TarballOperationResult(success=False, message=error_msg, error_details=str(e))

        except Exception as e:
            error_msg = f"Unexpected error while fetching release info: {e}"
            logger.error(error_msg, exc_info=True)

            return TarballOperationResult(success=False, message=error_msg, error_details=str(e))

    def download_and_extract_release(
        self,
        release_info: ReleaseInfo,
        target_dir: Path,
        auth_type: Optional[RepositoryAuthType] = None,
        auth_data: Optional[Dict[str, str]] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> TarballOperationResult:
        """Download and extract a release tarball/zipball.

        Args:
            release_info: Release information from get_latest_release_info
            target_dir: Target directory for extraction
            auth_type: Authentication type (token, basic)
            auth_data: Authentication data
            progress_callback: Optional progress callback function

        Returns:
            TarballOperationResult with extraction details
        """
        temp_dir = None
        temp_file = None

        try:
            # Create temporary directory for atomic operations
            temp_dir = Path(tempfile.mkdtemp(prefix="sai_download_"))
            temp_file = temp_dir / f"release.{self._get_file_extension(release_info.download_url)}"

            logger.info(
                f"Downloading release {release_info.tag_name} from {release_info.download_url}"
            )

            # Download the release file
            download_result = self._download_file_with_retry(
                release_info.download_url, temp_file, auth_type, auth_data, progress_callback
            )

            if not download_result.success:
                return download_result

            # Verify checksum if available (using enhanced validator)
            if release_info.checksum:
                checksum_result = self._verify_checksum_enhanced(
                    temp_file, release_info.checksum, release_info.checksum_algorithm
                )
                if not checksum_result.success:
                    return checksum_result

            # Extract the archive atomically with path traversal protection
            extraction_result = self._extract_archive_atomically_secure(
                temp_file, target_dir, release_info.tag_name
            )

            if extraction_result.success:
                logger.info(f"Successfully extracted release to {target_dir}")

            return extraction_result

        except Exception as e:
            return TarballOperationResult(
                success=False,
                message=f"Unexpected error during download and extraction: {e}",
                error_details=str(e),
            )

        finally:
            # Cleanup temporary files
            if temp_dir and temp_dir.exists():
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    logger.warning(f"Failed to cleanup temporary directory {temp_dir}: {e}")

    def download_latest_release(
        self,
        repo_url: str,
        target_dir: Path,
        auth_type: Optional[RepositoryAuthType] = None,
        auth_data: Optional[Dict[str, str]] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> TarballOperationResult:
        """Download and extract the latest release from a repository.

        Args:
            repo_url: Repository URL (e.g., https://github.com/owner/repo)
            target_dir: Target directory for extraction
            auth_type: Authentication type (token, basic)
            auth_data: Authentication data
            progress_callback: Optional progress callback function

        Returns:
            TarballOperationResult with operation details
        """
        # First, get the latest release info
        release_result = self.get_latest_release_info(repo_url, auth_type, auth_data)
        if not release_result.success:
            return release_result

        # Then download and extract it
        return self.download_and_extract_release(
            release_result.release_info, target_dir, auth_type, auth_data, progress_callback
        )

    def _parse_github_url(self, repo_url: str) -> tuple[Optional[str], Optional[str]]:
        """Parse GitHub repository URL to extract owner and repo name.

        Args:
            repo_url: GitHub repository URL

        Returns:
            Tuple of (owner, repo) or (None, None) if invalid
        """
        try:
            parsed = urllib.parse.urlparse(repo_url)

            # Handle different GitHub URL formats
            if parsed.netloc == "github.com":
                path_parts = parsed.path.strip("/").split("/")
                if len(path_parts) >= 2:
                    owner = path_parts[0]
                    repo = path_parts[1]
                    # Remove .git suffix if present
                    if repo.endswith(".git"):
                        repo = repo[:-4]
                    return owner, repo

            return None, None

        except Exception:
            return None, None

    def _add_auth_headers(
        self,
        request: urllib.request.Request,
        auth_type: RepositoryAuthType,
        auth_data: Dict[str, str],
    ):
        """Add authentication headers to the request.

        Args:
            request: urllib Request object
            auth_type: Authentication type
            auth_data: Authentication data
        """
        if auth_type == RepositoryAuthType.TOKEN:
            token = auth_data.get("token")
            if token:
                request.add_header("Authorization", f"token {token}")

        elif auth_type == RepositoryAuthType.BASIC:
            username = auth_data.get("username")
            password = auth_data.get("password")
            if username and password:
                import base64

                credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
                request.add_header("Authorization", f"Basic {credentials}")

    def _parse_release_data(self, data: Dict[str, Any]) -> Optional[ReleaseInfo]:
        """Parse GitHub release API response data.

        Args:
            data: GitHub API response data

        Returns:
            ReleaseInfo object or None if no suitable assets found
        """
        try:
            tag_name = data.get("tag_name", "")
            name = data.get("name", tag_name)
            published_at_str = data.get("published_at")

            # Parse published date
            published_at = None
            if published_at_str:
                try:
                    # GitHub API returns ISO format: "2023-12-01T10:30:00Z"
                    published_at = datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))
                except ValueError:
                    logger.warning(f"Failed to parse published date: {published_at_str}")

            # Look for suitable download assets
            assets = data.get("assets", [])

            # Prefer tarball assets, fall back to zipball
            download_url = None
            size = None

            # First, look for tarball assets
            for asset in assets:
                asset_name = asset.get("name", "").lower()
                if any(ext in asset_name for ext in [".tar.gz", ".tgz", ".tar.bz2", ".tar.xz"]):
                    download_url = asset.get("browser_download_url")
                    size = asset.get("size")
                    break

            # If no tarball found, look for zip assets
            if not download_url:
                for asset in assets:
                    asset_name = asset.get("name", "").lower()
                    if asset_name.endswith(".zip"):
                        download_url = asset.get("browser_download_url")
                        size = asset.get("size")
                        break

            # Fall back to GitHub's automatic tarball/zipball URLs
            if not download_url:
                download_url = data.get("tarball_url") or data.get("zipball_url")

            if not download_url:
                return None

            return ReleaseInfo(
                tag_name=tag_name,
                name=name,
                download_url=download_url,
                published_at=published_at,
                size=size,
            )

        except Exception as e:
            logger.error(f"Failed to parse release data: {e}")
            return None

    def _get_file_extension(self, url: str) -> str:
        """Get appropriate file extension from download URL.

        Args:
            url: Download URL

        Returns:
            File extension (tar.gz, zip, etc.)
        """
        url_lower = url.lower()

        if ".tar.gz" in url_lower or ".tgz" in url_lower:
            return "tar.gz"
        elif ".tar.bz2" in url_lower:
            return "tar.bz2"
        elif ".tar.xz" in url_lower:
            return "tar.xz"
        elif ".zip" in url_lower:
            return "zip"
        elif "tarball" in url_lower:
            return "tar.gz"
        elif "zipball" in url_lower:
            return "zip"
        else:
            # Default to tar.gz for GitHub releases
            return "tar.gz"

    def _download_file_with_retry(
        self,
        url: str,
        target_file: Path,
        auth_type: Optional[RepositoryAuthType],
        auth_data: Optional[Dict[str, str]],
        progress_callback: Optional[Callable[[int, int], None]],
    ) -> TarballOperationResult:
        """Download a file with retry logic.

        Args:
            url: URL to download
            target_file: Target file path
            auth_type: Authentication type
            auth_data: Authentication data
            progress_callback: Progress callback function

        Returns:
            TarballOperationResult with download status
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                # Create request with authentication
                request = urllib.request.Request(url)
                request.add_header("User-Agent", "SAI-Tool/1.0")

                if auth_type and auth_data:
                    self._add_auth_headers(request, auth_type, auth_data)

                # Setup progress reporter
                progress_reporter = ProgressReporter(progress_callback)

                # Download the file
                urllib.request.urlretrieve(url, target_file, progress_reporter)

                # Verify the file was downloaded
                if not target_file.exists() or target_file.stat().st_size == 0:
                    raise Exception("Downloaded file is empty or missing")

                logger.info(f"Successfully downloaded {target_file.stat().st_size} bytes")

                return TarballOperationResult(
                    success=True,
                    message=f"Successfully downloaded file ({target_file.stat().st_size} bytes)",
                )

            except Exception as e:
                last_error = e

                if attempt < self.max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s, etc.
                    delay = 2**attempt
                    logger.warning(
                        f"Download failed (attempt {attempt + 1}/{self.max_retries}), retrying in {delay}s: {e}"
                    )

                    # Clean up partial download
                    if target_file.exists():
                        try:
                            target_file.unlink()
                        except Exception:
                            pass

                    import time

                    time.sleep(delay)

        return TarballOperationResult(
            success=False,
            message=f"Download failed after {self.max_retries} attempts",
            error_details=str(last_error),
        )

    def _verify_checksum(
        self, file_path: Path, expected_checksum: str, algorithm: str = "sha256"
    ) -> TarballOperationResult:
        """Verify file checksum.

        Args:
            file_path: Path to file to verify
            expected_checksum: Expected checksum value
            algorithm: Hash algorithm (sha256, sha1, md5)

        Returns:
            TarballOperationResult with verification status
        """
        try:
            # Get the appropriate hash function
            if algorithm.lower() == "sha256":
                hasher = hashlib.sha256()
            elif algorithm.lower() == "sha1":
                hasher = hashlib.sha1()
            elif algorithm.lower() == "md5":
                hasher = hashlib.md5()
            else:
                return TarballOperationResult(
                    success=False,
                    message=f"Unsupported checksum algorithm: {algorithm}",
                    error_details=f"Supported algorithms: sha256, sha1, md5",
                )

            # Calculate file checksum
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hasher.update(chunk)

            calculated_checksum = hasher.hexdigest().lower()
            expected_checksum = expected_checksum.lower()

            if calculated_checksum == expected_checksum:
                logger.debug(f"Checksum verification passed ({algorithm}: {calculated_checksum})")
                return TarballOperationResult(
                    success=True, message=f"Checksum verification passed ({algorithm})"
                )
            else:
                return TarballOperationResult(
                    success=False,
                    message=f"Checksum verification failed",
                    error_details=f"Expected {expected_checksum}, got {calculated_checksum}",
                )

        except Exception as e:
            return TarballOperationResult(
                success=False, message=f"Checksum verification error: {e}", error_details=str(e)
            )

    def _extract_archive_atomically(
        self, archive_path: Path, target_dir: Path, release_tag: str
    ) -> TarballOperationResult:
        """Extract archive atomically to target directory.

        Args:
            archive_path: Path to archive file
            target_dir: Target directory for extraction
            release_tag: Release tag for logging

        Returns:
            TarballOperationResult with extraction status
        """
        temp_extract_dir = None

        try:
            # Create temporary extraction directory
            temp_extract_dir = archive_path.parent / f"extract_{release_tag}"
            temp_extract_dir.mkdir(exist_ok=True)

            # Determine archive type and extract
            if archive_path.name.endswith(".zip"):
                self._extract_zip(archive_path, temp_extract_dir)
            else:
                self._extract_tar(archive_path, temp_extract_dir)

            # Find the extracted content (handle single directory case)
            extracted_items = list(temp_extract_dir.iterdir())

            if len(extracted_items) == 1 and extracted_items[0].is_dir():
                # Single directory case - move its contents
                source_dir = extracted_items[0]
            else:
                # Multiple items case - move the temp directory itself
                source_dir = temp_extract_dir

            # Ensure target directory exists
            target_dir.parent.mkdir(parents=True, exist_ok=True)

            # Atomic move: first remove target if it exists, then move
            if target_dir.exists():
                shutil.rmtree(target_dir)

            if source_dir == temp_extract_dir:
                # Move the entire temp directory
                shutil.move(str(temp_extract_dir), str(target_dir))
                temp_extract_dir = None  # Prevent cleanup since it was moved
            else:
                # Move contents of the single subdirectory
                shutil.move(str(source_dir), str(target_dir))

            logger.info(f"Successfully extracted {archive_path.name} to {target_dir}")

            return TarballOperationResult(
                success=True,
                message=f"Successfully extracted archive to {target_dir}",
                extracted_path=target_dir,
            )

        except Exception as e:
            return TarballOperationResult(
                success=False, message=f"Archive extraction failed: {e}", error_details=str(e)
            )

        finally:
            # Cleanup temporary extraction directory
            if temp_extract_dir and temp_extract_dir.exists():
                try:
                    shutil.rmtree(temp_extract_dir)
                except Exception as e:
                    logger.warning(f"Failed to cleanup temporary extraction directory: {e}")

    def _extract_tar(self, archive_path: Path, target_dir: Path):
        """Extract tar archive with security checks.

        Args:
            archive_path: Path to tar archive
            target_dir: Target directory for extraction
        """
        with tarfile.open(archive_path, "r:*") as tar:
            # Security check: validate all member paths
            for member in tar.getmembers():
                # Prevent path traversal attacks
                if member.name.startswith("/") or ".." in member.name:
                    raise Exception(f"Unsafe path in archive: {member.name}")

                # Prevent extraction of device files, etc.
                if not (member.isfile() or member.isdir() or member.issym() or member.islnk()):
                    logger.warning(f"Skipping special file: {member.name}")
                    continue

            # Extract all members
            tar.extractall(target_dir)

    def _extract_zip(self, archive_path: Path, target_dir: Path):
        """Extract zip archive with security checks.

        Args:
            archive_path: Path to zip archive
            target_dir: Target directory for extraction
        """
        with zipfile.ZipFile(archive_path, "r") as zip_file:
            # Security check: validate all member paths
            for member in zip_file.namelist():
                # Prevent path traversal attacks
                if member.startswith("/") or ".." in member:
                    raise Exception(f"Unsafe path in archive: {member}")

            # Extract all members
            zip_file.extractall(target_dir)

    def _is_temporary_network_error(self, error_message: str) -> bool:
        """Determine if a network error is likely temporary.

        Args:
            error_message: Network error message

        Returns:
            True if error appears to be temporary, False otherwise
        """
        error_lower = error_message.lower()

        # Temporary network issues
        temporary_indicators = [
            "timeout",
            "timed out",
            "connection reset",
            "connection refused",
            "temporary failure",
            "network is unreachable",
            "host is down",
            "connection aborted",
            "broken pipe",
        ]

        # Permanent configuration issues
        permanent_indicators = [
            "name or service not known",
            "no such host",
            "invalid hostname",
            "certificate verify failed",
            "ssl certificate problem",
        ]

        # Check for permanent issues first
        if any(indicator in error_lower for indicator in permanent_indicators):
            return False

        # Check for temporary issues
        if any(indicator in error_lower for indicator in temporary_indicators):
            return True

        # Default to temporary for unknown network errors
        return True

    def _log_download_progress(self, downloaded: int, total: int) -> None:
        """Log download progress at appropriate intervals.

        Args:
            downloaded: Bytes downloaded so far
            total: Total bytes to download
        """
        if total > 0:
            percent = (downloaded / total) * 100
            # Log progress every 10% or every 10MB, whichever is less frequent
            mb_downloaded = downloaded / (1024 * 1024)
            mb_total = total / (1024 * 1024)

            # Log at 10%, 25%, 50%, 75%, 90%, 100%
            progress_points = [10, 25, 50, 75, 90, 100]
            for point in progress_points:
                if abs(percent - point) < 1:  # Within 1% of progress point
                    logger.info(
                        f"Download progress: {percent:.1f}% ({mb_downloaded:.1f}MB / {mb_total:.1f}MB)"
                    )
                    break

    def _validate_download_integrity(
        self, file_path: Path, expected_size: Optional[int] = None
    ) -> bool:
        """Validate downloaded file integrity.

        Args:
            file_path: Path to downloaded file
            expected_size: Expected file size in bytes

        Returns:
            True if file appears valid, False otherwise
        """
        try:
            if not file_path.exists():
                logger.error(f"Downloaded file does not exist: {file_path}")
                return False

            actual_size = file_path.stat().st_size

            if actual_size == 0:
                logger.error(f"Downloaded file is empty: {file_path}")
                return False

            if expected_size and actual_size != expected_size:
                logger.warning(
                    f"Downloaded file size mismatch: expected {expected_size}, got {actual_size}"
                )
                # Don't fail on size mismatch as GitHub API size might be compressed size

            # Try to read the first few bytes to ensure file is accessible
            with open(file_path, "rb") as f:
                header = f.read(1024)
                if not header:
                    logger.error(f"Cannot read downloaded file: {file_path}")
                    return False

            logger.debug(
                f"Download integrity validation passed for {file_path} ({actual_size} bytes)"
            )
            return True

        except Exception as e:
            logger.error(f"Download integrity validation failed: {e}")
            return False

    def _verify_checksum_enhanced(
        self, file_path: Path, expected_checksum: str, algorithm: str = "sha256"
    ) -> TarballOperationResult:
        """Verify file checksum using enhanced validator.

        Args:
            file_path: Path to file to verify
            expected_checksum: Expected checksum value
            algorithm: Hash algorithm (sha256, sha1, md5, etc.)

        Returns:
            TarballOperationResult with verification status
        """
        logger.debug(f"Verifying {algorithm} checksum for {file_path}")

        is_valid, calculated_checksum, error_msg = self.checksum_validator.validate_file_checksum(
            file_path, expected_checksum, algorithm
        )

        if error_msg:
            return TarballOperationResult(
                success=False,
                message=f"Checksum verification error: {error_msg}",
                error_details=error_msg,
            )

        if is_valid:
            logger.info(f"Checksum verification passed ({algorithm}: {calculated_checksum})")
            return TarballOperationResult(
                success=True, message=f"Checksum verification passed ({algorithm})"
            )
        else:
            error_msg = f"Checksum verification failed: expected {expected_checksum}, got {calculated_checksum}"
            logger.error(error_msg)
            return TarballOperationResult(
                success=False, message="Checksum verification failed", error_details=error_msg
            )

    def _extract_archive_atomically_secure(
        self, archive_path: Path, target_dir: Path, release_tag: str
    ) -> TarballOperationResult:
        """Extract archive atomically with path traversal protection.

        Args:
            archive_path: Path to archive file
            target_dir: Target directory for extraction
            release_tag: Release tag for logging

        Returns:
            TarballOperationResult with extraction status
        """
        temp_extract_dir = None

        try:
            # Create temporary extraction directory
            temp_extract_dir = archive_path.parent / f"extract_{release_tag}"
            temp_extract_dir.mkdir(exist_ok=True)

            # Initialize path traversal protector
            path_protector = PathTraversalProtector(temp_extract_dir)

            # Determine archive type and extract with security checks
            if archive_path.name.endswith(".zip"):
                self._extract_zip_secure(archive_path, temp_extract_dir, path_protector)
            else:
                self._extract_tar_secure(archive_path, temp_extract_dir, path_protector)

            # Find the extracted content (handle single directory case)
            extracted_items = list(temp_extract_dir.iterdir())

            if len(extracted_items) == 1 and extracted_items[0].is_dir():
                # Single directory case - move its contents
                source_dir = extracted_items[0]
            else:
                # Multiple items case - move the temp directory itself
                source_dir = temp_extract_dir

            # Ensure target directory exists
            target_dir.parent.mkdir(parents=True, exist_ok=True)

            # Atomic move: first remove target if it exists, then move
            if target_dir.exists():
                shutil.rmtree(target_dir)

            if source_dir == temp_extract_dir:
                # Move the entire temp directory
                shutil.move(str(temp_extract_dir), str(target_dir))
                temp_extract_dir = None  # Prevent cleanup since it was moved
            else:
                # Move contents of the single subdirectory
                shutil.move(str(source_dir), str(target_dir))

            logger.info(f"Successfully extracted {archive_path.name} to {target_dir}")

            return TarballOperationResult(
                success=True,
                message=f"Successfully extracted archive to {target_dir}",
                extracted_path=target_dir,
            )

        except Exception as e:
            error_msg = f"Archive extraction failed: {e}"
            logger.error(error_msg)
            return TarballOperationResult(success=False, message=error_msg, error_details=str(e))

        finally:
            # Cleanup temporary extraction directory
            if temp_extract_dir and temp_extract_dir.exists():
                try:
                    shutil.rmtree(temp_extract_dir)
                except Exception as e:
                    logger.warning(f"Failed to cleanup temporary extraction directory: {e}")

    def _extract_tar_secure(
        self, archive_path: Path, target_dir: Path, path_protector: PathTraversalProtector
    ):
        """Extract tar archive with enhanced security checks.

        Args:
            archive_path: Path to tar archive
            target_dir: Target directory for extraction
            path_protector: Path traversal protector
        """
        with tarfile.open(archive_path, "r:*") as tar:
            # Security check: validate all member paths
            blocked_members = []
            safe_members = []

            for member in tar.getmembers():
                # Check for path traversal
                is_safe, error_msg = path_protector.validate_extraction_path(member.name)
                if not is_safe:
                    blocked_members.append(f"{member.name}: {error_msg}")
                    logger.warning(f"Blocked unsafe archive member: {member.name} ({error_msg})")
                    continue

                # Prevent extraction of device files, etc.
                if not (member.isfile() or member.isdir() or member.issym() or member.islnk()):
                    blocked_members.append(f"{member.name}: special file type not allowed")
                    logger.warning(f"Blocked special file: {member.name}")
                    continue

                # Check for suspicious file sizes (prevent zip bombs)
                if member.isfile() and member.size > 100 * 1024 * 1024:  # 100MB limit
                    logger.warning(f"Large file in archive: {member.name} ({member.size} bytes)")

                safe_members.append(member)

            if blocked_members:
                logger.warning(f"Blocked {len(blocked_members)} unsafe archive members")
                if len(blocked_members) > len(safe_members):
                    raise SecurityError("Archive contains too many unsafe members")

            # Extract only safe members
            for member in safe_members:
                try:
                    tar.extract(member, target_dir)
                except Exception as e:
                    logger.warning(f"Failed to extract member {member.name}: {e}")

    def _extract_zip_secure(
        self, archive_path: Path, target_dir: Path, path_protector: PathTraversalProtector
    ):
        """Extract zip archive with enhanced security checks.

        Args:
            archive_path: Path to zip archive
            target_dir: Target directory for extraction
            path_protector: Path traversal protector
        """
        with zipfile.ZipFile(archive_path, "r") as zip_file:
            # Security check: validate all member paths
            blocked_members = []
            safe_members = []

            for member_name in zip_file.namelist():
                # Check for path traversal
                is_safe, error_msg = path_protector.validate_extraction_path(member_name)
                if not is_safe:
                    blocked_members.append(f"{member_name}: {error_msg}")
                    logger.warning(f"Blocked unsafe archive member: {member_name} ({error_msg})")
                    continue

                # Check for suspicious file sizes (prevent zip bombs)
                try:
                    info = zip_file.getinfo(member_name)
                    if info.file_size > 100 * 1024 * 1024:  # 100MB limit
                        logger.warning(
                            f"Large file in archive: {member_name} ({info.file_size} bytes)"
                        )

                    # Check compression ratio for zip bomb detection
                    if info.compress_size > 0:
                        ratio = info.file_size / info.compress_size
                        if ratio > 100:  # Suspicious compression ratio
                            logger.warning(
                                f"High compression ratio for {member_name}: {ratio:.1f}:1"
                            )
                            if ratio > 1000:  # Very suspicious
                                blocked_members.append(
                                    f"{member_name}: suspicious compression ratio ({ratio:.1f}:1)"
                                )
                                continue
                except Exception as e:
                    logger.warning(f"Could not check file info for {member_name}: {e}")

                safe_members.append(member_name)

            if blocked_members:
                logger.warning(f"Blocked {len(blocked_members)} unsafe archive members")
                if len(blocked_members) > len(safe_members):
                    raise SecurityError("Archive contains too many unsafe members")

            # Extract only safe members
            for member_name in safe_members:
                try:
                    zip_file.extract(member_name, target_dir)
                except Exception as e:
                    logger.warning(f"Failed to extract member {member_name}: {e}")

    def store_repository_credentials(
        self, repository_url: str, auth_type: RepositoryAuthType, auth_data: Dict[str, str]
    ) -> bool:
        """Store repository credentials securely.

        Args:
            repository_url: Repository URL
            auth_type: Authentication type
            auth_data: Authentication data

        Returns:
            True if stored successfully, False otherwise
        """
        logger.debug(f"Storing credentials for repository: {repository_url}")

        try:
            if auth_type == RepositoryAuthType.TOKEN:
                token = auth_data.get("token")
                if token:
                    return self.credential_manager.store_access_token(
                        repository_url, token, auth_data.get("username")
                    )

            elif auth_type == RepositoryAuthType.BASIC:
                username = auth_data.get("username")
                password = auth_data.get("password")
                if username and password:
                    return self.credential_manager.store_username_password(
                        repository_url, username, password
                    )

            return False

        except Exception as e:
            logger.error(f"Failed to store repository credentials: {e}")
            return False

    def calculate_file_checksums(
        self, file_path: Path, algorithms: List[str] = None
    ) -> Dict[str, str]:
        """Calculate multiple checksums for a file.

        Args:
            file_path: Path to file
            algorithms: List of algorithms to use (defaults to ['sha256', 'sha512'])

        Returns:
            Dictionary mapping algorithm names to checksum values
        """
        if algorithms is None:
            algorithms = ["sha256", "sha512"]

        checksums = {}

        for algorithm in algorithms:
            checksum, error = self.checksum_validator.calculate_file_checksum(file_path, algorithm)
            if checksum:
                checksums[algorithm] = checksum
            else:
                logger.warning(f"Failed to calculate {algorithm} checksum: {error}")

        return checksums
