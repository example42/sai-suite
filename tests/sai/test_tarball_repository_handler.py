"""Tests for TarballRepositoryHandler."""

import json
import tarfile
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from sai.core.tarball_repository_handler import (
    ProgressReporter,
    ReleaseInfo,
    TarballOperationResult,
    TarballRepositoryHandler,
)
from sai.models.config import RepositoryAuthType


class TestProgressReporter:
    """Test ProgressReporter class."""

    def test_progress_reporter_with_callback(self):
        """Test progress reporter with callback function."""
        callback_calls = []

        def callback(downloaded, total):
            callback_calls.append((downloaded, total))

        reporter = ProgressReporter(callback)

        # Simulate progress updates
        reporter(0, 1024, 10240)  # 0 blocks
        reporter(5, 1024, 10240)  # 5 blocks = 5120 bytes
        reporter(10, 1024, 10240)  # 10 blocks = 10240 bytes (complete)

        assert len(callback_calls) == 3
        assert callback_calls[0] == (0, 10240)
        assert callback_calls[1] == (5120, 10240)
        assert callback_calls[2] == (10240, 10240)

    def test_progress_reporter_without_callback(self):
        """Test progress reporter without callback function."""
        reporter = ProgressReporter()

        # Should not raise any errors
        reporter(0, 1024, 10240)
        reporter(5, 1024, 10240)
        reporter(10, 1024, 10240)

        assert reporter.downloaded == 10240
        assert reporter.total == 10240


class TestTarballRepositoryHandler:
    """Test TarballRepositoryHandler class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.handler = TarballRepositoryHandler(timeout=30, max_retries=2)

    def test_init(self):
        """Test handler initialization."""
        assert self.handler.timeout == 30
        assert self.handler.max_retries == 2

    def test_parse_github_url_valid(self):
        """Test parsing valid GitHub URLs."""
        test_cases = [
            ("https://github.com/owner/repo", ("owner", "repo")),
            ("https://github.com/owner/repo.git", ("owner", "repo")),
            ("https://github.com/owner/repo/", ("owner", "repo")),
            ("https://github.com/example42/saidata", ("example42", "saidata")),
        ]

        for url, expected in test_cases:
            result = self.handler._parse_github_url(url)
            assert result == expected, f"Failed for URL: {url}"

    def test_parse_github_url_invalid(self):
        """Test parsing invalid GitHub URLs."""
        test_cases = [
            "https://gitlab.com/owner/repo",
            "https://github.com/owner",
            "https://github.com/",
            "not-a-url",
            "",
        ]

        for url in test_cases:
            result = self.handler._parse_github_url(url)
            assert result == (None, None), f"Should fail for URL: {url}"

    def test_get_file_extension(self):
        """Test file extension detection."""
        test_cases = [
            ("https://example.com/file.tar.gz", "tar.gz"),
            ("https://example.com/file.tgz", "tar.gz"),
            ("https://example.com/file.tar.bz2", "tar.bz2"),
            ("https://example.com/file.tar.xz", "tar.xz"),
            ("https://example.com/file.zip", "zip"),
            ("https://api.github.com/repos/owner/repo/tarball/main", "tar.gz"),
            ("https://api.github.com/repos/owner/repo/zipball/main", "zip"),
            ("https://example.com/unknown", "tar.gz"),  # Default
        ]

        for url, expected in test_cases:
            result = self.handler._get_file_extension(url)
            assert result == expected, f"Failed for URL: {url}"

    def test_add_auth_headers_token(self):
        """Test adding token authentication headers."""
        import urllib.request

        request = urllib.request.Request("https://example.com")
        auth_data = {"token": "test-token"}

        self.handler._add_auth_headers(request, RepositoryAuthType.TOKEN, auth_data)

        assert request.get_header("Authorization") == "token test-token"

    def test_add_auth_headers_basic(self):
        """Test adding basic authentication headers."""
        import base64
        import urllib.request

        request = urllib.request.Request("https://example.com")
        auth_data = {"username": "user", "password": "pass"}

        self.handler._add_auth_headers(request, RepositoryAuthType.BASIC, auth_data)

        expected_creds = base64.b64encode("user:pass".encode()).decode()
        assert request.get_header("Authorization") == f"Basic {expected_creds}"

    def test_parse_release_data_with_assets(self):
        """Test parsing release data with assets."""
        release_data = {
            "tag_name": "v1.0.0",
            "name": "Release 1.0.0",
            "published_at": "2023-12-01T10:30:00Z",
            "assets": [
                {
                    "name": "release.tar.gz",
                    "browser_download_url": "https://example.com/release.tar.gz",
                    "size": 1024000,
                },
                {
                    "name": "release.zip",
                    "browser_download_url": "https://example.com/release.zip",
                    "size": 1100000,
                },
            ],
        }

        result = self.handler._parse_release_data(release_data)

        assert result is not None
        assert result.tag_name == "v1.0.0"
        assert result.name == "Release 1.0.0"
        assert result.download_url == "https://example.com/release.tar.gz"  # Prefers tarball
        assert result.size == 1024000
        assert result.published_at == datetime.fromisoformat("2023-12-01T10:30:00+00:00")

    def test_parse_release_data_with_fallback_urls(self):
        """Test parsing release data with fallback URLs."""
        release_data = {
            "tag_name": "v1.0.0",
            "name": "Release 1.0.0",
            "assets": [],  # No assets
            "tarball_url": "https://api.github.com/repos/owner/repo/tarball/v1.0.0",
        }

        result = self.handler._parse_release_data(release_data)

        assert result is not None
        assert result.tag_name == "v1.0.0"
        assert result.download_url == "https://api.github.com/repos/owner/repo/tarball/v1.0.0"

    def test_parse_release_data_no_assets(self):
        """Test parsing release data with no suitable assets."""
        release_data = {
            "tag_name": "v1.0.0",
            "name": "Release 1.0.0",
            "assets": [],  # No assets and no fallback URLs
        }

        result = self.handler._parse_release_data(release_data)

        assert result is None

    @patch("urllib.request.urlopen")
    def test_get_latest_release_info_success(self, mock_urlopen):
        """Test successful release info retrieval."""
        # Mock API response
        response_data = {
            "tag_name": "v1.0.0",
            "name": "Release 1.0.0",
            "published_at": "2023-12-01T10:30:00Z",
            "tarball_url": "https://api.github.com/repos/example42/saidata/tarball/v1.0.0",
        }

        mock_response = Mock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps(response_data).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = self.handler.get_latest_release_info("https://github.com/example42/saidata")

        assert result.success
        assert result.release_info is not None
        assert result.release_info.tag_name == "v1.0.0"
        assert (
            result.release_info.download_url
            == "https://api.github.com/repos/example42/saidata/tarball/v1.0.0"
        )

    @patch("urllib.request.urlopen")
    def test_get_latest_release_info_http_error(self, mock_urlopen):
        """Test release info retrieval with HTTP error."""
        import urllib.error

        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://api.github.com/repos/example42/saidata/releases/latest",
            code=404,
            msg="Not Found",
            hdrs={},
            fp=None,
        )

        result = self.handler.get_latest_release_info("https://github.com/example42/saidata")

        assert not result.success
        assert "404" in result.message
        assert "Repository not found" in result.message

    def test_get_latest_release_info_invalid_url(self):
        """Test release info retrieval with invalid URL."""
        result = self.handler.get_latest_release_info("https://gitlab.com/owner/repo")

        assert not result.success
        assert "Invalid GitHub repository URL" in result.message

    def test_verify_checksum_success(self):
        """Test successful checksum verification."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(b"test content")

        try:
            # Calculate expected SHA256
            import hashlib

            expected_checksum = hashlib.sha256(b"test content").hexdigest()

            result = self.handler._verify_checksum(temp_path, expected_checksum, "sha256")

            assert result.success
            assert "verification passed" in result.message.lower()
        finally:
            temp_path.unlink()

    def test_verify_checksum_failure(self):
        """Test failed checksum verification."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(b"test content")

        try:
            # Use wrong checksum
            wrong_checksum = "0" * 64

            result = self.handler._verify_checksum(temp_path, wrong_checksum, "sha256")

            assert not result.success
            assert "verification failed" in result.message.lower()
        finally:
            temp_path.unlink()

    def test_verify_checksum_unsupported_algorithm(self):
        """Test checksum verification with unsupported algorithm."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(b"test content")

        try:
            result = self.handler._verify_checksum(temp_path, "checksum", "unsupported")

            assert not result.success
            assert "Unsupported checksum algorithm" in result.message
        finally:
            temp_path.unlink()

    def test_extract_tar_archive(self):
        """Test tar archive extraction."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a test tar.gz archive
            archive_path = temp_path / "test.tar.gz"
            extract_path = temp_path / "extract"

            with tarfile.open(archive_path, "w:gz") as tar:
                # Add a test file
                test_content = b"test file content"
                import io

                tarinfo = tarfile.TarInfo(name="test_file.txt")
                tarinfo.size = len(test_content)
                tarinfo.mode = 0o644  # Set proper permissions
                tar.addfile(tarinfo, io.BytesIO(test_content))

                # Add a directory
                dirinfo = tarfile.TarInfo(name="test_dir/")
                dirinfo.type = tarfile.DIRTYPE
                dirinfo.mode = 0o755  # Set proper permissions
                tar.addfile(dirinfo)

            # Test extraction
            self.handler._extract_tar(archive_path, extract_path)

            # Verify extraction
            assert (extract_path / "test_file.txt").exists()
            assert (extract_path / "test_dir").is_dir()
            assert (extract_path / "test_file.txt").read_bytes() == test_content

    def test_extract_zip_archive(self):
        """Test zip archive extraction."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a test zip archive
            archive_path = temp_path / "test.zip"
            extract_path = temp_path / "extract"

            with zipfile.ZipFile(archive_path, "w") as zip_file:
                zip_file.writestr("test_file.txt", "test file content")
                zip_file.writestr("test_dir/nested_file.txt", "nested content")

            # Test extraction
            self.handler._extract_zip(archive_path, extract_path)

            # Verify extraction
            assert (extract_path / "test_file.txt").exists()
            assert (extract_path / "test_dir" / "nested_file.txt").exists()
            assert (extract_path / "test_file.txt").read_text() == "test file content"

    def test_extract_tar_security_check(self):
        """Test tar extraction security checks."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a malicious tar archive with path traversal
            archive_path = temp_path / "malicious.tar.gz"
            extract_path = temp_path / "extract"

            with tarfile.open(archive_path, "w:gz") as tar:
                # Try to add a file with path traversal
                import io

                tarinfo = tarfile.TarInfo(name="../../../etc/passwd")
                tarinfo.size = 0
                tar.addfile(tarinfo, io.BytesIO(b""))

            # Test that extraction fails with security error
            with pytest.raises(Exception, match="Unsafe path in archive"):
                self.handler._extract_tar(archive_path, extract_path)

    def test_extract_zip_security_check(self):
        """Test zip extraction security checks."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a malicious zip archive with path traversal
            archive_path = temp_path / "malicious.zip"
            extract_path = temp_path / "extract"

            with zipfile.ZipFile(archive_path, "w") as zip_file:
                # Try to add a file with path traversal
                zip_file.writestr("../../../etc/passwd", "malicious content")

            # Test that extraction fails with security error
            with pytest.raises(Exception, match="Unsafe path in archive"):
                self.handler._extract_zip(archive_path, extract_path)

    @patch("urllib.request.urlretrieve")
    def test_download_file_with_retry_success(self, mock_urlretrieve):
        """Test successful file download."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            target_file = temp_path / "download.tar.gz"

            # Mock successful download
            def mock_download(url, filename, reporthook=None):
                Path(filename).write_bytes(b"downloaded content")
                if reporthook:
                    reporthook(1, 1024, 1024)  # Simulate progress

            mock_urlretrieve.side_effect = mock_download

            result = self.handler._download_file_with_retry(
                "https://example.com/file.tar.gz", target_file, None, None, None
            )

            assert result.success
            assert target_file.exists()
            assert target_file.read_bytes() == b"downloaded content"

    @patch("urllib.request.urlretrieve")
    def test_download_file_with_retry_failure(self, mock_urlretrieve):
        """Test file download with retries and final failure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            target_file = temp_path / "download.tar.gz"

            # Mock download failure
            mock_urlretrieve.side_effect = Exception("Network error")

            result = self.handler._download_file_with_retry(
                "https://example.com/file.tar.gz", target_file, None, None, None
            )

            assert not result.success
            assert "failed after" in result.message.lower()
            assert "Network error" in result.error_details

    def test_extract_archive_atomically_single_directory(self):
        """Test atomic extraction with single directory in archive."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create archive with single directory
            archive_path = temp_path / "test.tar.gz"
            target_dir = temp_path / "target"

            with tarfile.open(archive_path, "w:gz") as tar:
                # Add files in a single directory
                import io

                for i in range(3):
                    content = f"file {i} content".encode()
                    tarinfo = tarfile.TarInfo(name=f"repo-main/file{i}.txt")
                    tarinfo.size = len(content)
                    tarinfo.mode = 0o644  # Set proper permissions
                    tar.addfile(tarinfo, io.BytesIO(content))

            result = self.handler._extract_archive_atomically(archive_path, target_dir, "v1.0.0")

            assert result.success
            assert target_dir.exists()
            assert (target_dir / "file0.txt").exists()
            assert (target_dir / "file1.txt").exists()
            assert (target_dir / "file2.txt").exists()

    def test_extract_archive_atomically_multiple_items(self):
        """Test atomic extraction with multiple items in archive."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create archive with multiple top-level items
            archive_path = temp_path / "test.tar.gz"
            target_dir = temp_path / "target"

            with tarfile.open(archive_path, "w:gz") as tar:
                # Add multiple top-level files/directories
                import io

                # Add a file
                content = b"file content"
                tarinfo = tarfile.TarInfo(name="file.txt")
                tarinfo.size = len(content)
                tarinfo.mode = 0o644  # Set proper permissions
                tar.addfile(tarinfo, io.BytesIO(content))

                # Add a directory with content
                dirinfo = tarfile.TarInfo(name="dir/")
                dirinfo.type = tarfile.DIRTYPE
                dirinfo.mode = 0o755  # Set proper permissions
                tar.addfile(dirinfo)

                content2 = b"nested content"
                tarinfo2 = tarfile.TarInfo(name="dir/nested.txt")
                tarinfo2.size = len(content2)
                tarinfo2.mode = 0o644  # Set proper permissions
                tar.addfile(tarinfo2, io.BytesIO(content2))

            result = self.handler._extract_archive_atomically(archive_path, target_dir, "v1.0.0")

            assert result.success
            assert target_dir.exists()
            assert (target_dir / "file.txt").exists()
            assert (target_dir / "dir" / "nested.txt").exists()

    @patch.object(TarballRepositoryHandler, "get_latest_release_info")
    @patch.object(TarballRepositoryHandler, "download_and_extract_release")
    def test_download_latest_release_success(self, mock_download, mock_get_info):
        """Test successful download of latest release."""
        # Mock release info
        release_info = ReleaseInfo(
            tag_name="v1.0.0",
            name="Release 1.0.0",
            download_url="https://example.com/release.tar.gz",
        )

        mock_get_info.return_value = TarballOperationResult(
            success=True, message="Success", release_info=release_info
        )

        mock_download.return_value = TarballOperationResult(
            success=True, message="Downloaded and extracted successfully"
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir) / "target"

            result = self.handler.download_latest_release(
                "https://github.com/example42/saidata", target_dir
            )

            assert result.success
            mock_get_info.assert_called_once()
            mock_download.assert_called_once_with(release_info, target_dir, None, None, None)

    @patch.object(TarballRepositoryHandler, "get_latest_release_info")
    def test_download_latest_release_info_failure(self, mock_get_info):
        """Test download failure when release info cannot be retrieved."""
        mock_get_info.return_value = TarballOperationResult(
            success=False, message="Failed to get release info"
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir) / "target"

            result = self.handler.download_latest_release(
                "https://github.com/example42/saidata", target_dir
            )

            assert not result.success
            assert "Failed to get release info" in result.message


class TestReleaseInfo:
    """Test ReleaseInfo dataclass."""

    def test_release_info_creation(self):
        """Test ReleaseInfo creation with all fields."""
        published_at = datetime.now()

        release_info = ReleaseInfo(
            tag_name="v1.0.0",
            name="Release 1.0.0",
            download_url="https://example.com/release.tar.gz",
            published_at=published_at,
            checksum="abc123",
            checksum_algorithm="sha256",
            size=1024000,
        )

        assert release_info.tag_name == "v1.0.0"
        assert release_info.name == "Release 1.0.0"
        assert release_info.download_url == "https://example.com/release.tar.gz"
        assert release_info.published_at == published_at
        assert release_info.checksum == "abc123"
        assert release_info.checksum_algorithm == "sha256"
        assert release_info.size == 1024000

    def test_release_info_minimal(self):
        """Test ReleaseInfo creation with minimal fields."""
        release_info = ReleaseInfo(
            tag_name="v1.0.0",
            name="Release 1.0.0",
            download_url="https://example.com/release.tar.gz",
        )

        assert release_info.tag_name == "v1.0.0"
        assert release_info.name == "Release 1.0.0"
        assert release_info.download_url == "https://example.com/release.tar.gz"
        assert release_info.published_at is None
        assert release_info.checksum is None
        assert release_info.checksum_algorithm == "sha256"
        assert release_info.size is None


class TestTarballOperationResult:
    """Test TarballOperationResult dataclass."""

    def test_operation_result_success(self):
        """Test successful operation result."""
        result = TarballOperationResult(success=True, message="Operation completed successfully")

        assert result.success
        assert result.message == "Operation completed successfully"
        assert result.release_info is None
        assert result.extracted_path is None
        assert result.error_details is None

    def test_operation_result_failure(self):
        """Test failed operation result."""
        result = TarballOperationResult(
            success=False, message="Operation failed", error_details="Detailed error information"
        )

        assert not result.success
        assert result.message == "Operation failed"
        assert result.error_details == "Detailed error information"
