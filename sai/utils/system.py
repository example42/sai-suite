"""System detection utilities for SAI CLI tool."""

import logging
import os
import platform
import shutil
import socket
import subprocess
import time
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from urllib.parse import urlparse


logger = logging.getLogger(__name__)


def get_platform() -> str:
    """Get the current platform identifier.
    
    Returns:
        Platform identifier (e.g., 'linux', 'darwin', 'windows')
    """
    return platform.system().lower()


def is_executable_available(executable: str) -> bool:
    """Check if an executable is available in the system PATH.
    
    Args:
        executable: Name or path of the executable to check
        
    Returns:
        True if executable is available, False otherwise
    """
    try:
        # Use shutil.which to check if executable exists in PATH
        result = shutil.which(executable)
        available = result is not None
        
        if available:
            logger.debug(f"Executable '{executable}' found at: {result}")
        else:
            logger.debug(f"Executable '{executable}' not found in PATH")
            
        return available
        
    except Exception as e:
        logger.warning(f"Error checking executable '{executable}': {e}")
        return False


def get_executable_path(executable: str) -> Optional[str]:
    """Get the full path to an executable if it exists.
    
    Args:
        executable: Name of the executable to locate
        
    Returns:
        Full path to executable if found, None otherwise
    """
    try:
        path = shutil.which(executable)
        if path:
            logger.debug(f"Located executable '{executable}' at: {path}")
        return path
    except Exception as e:
        logger.warning(f"Error locating executable '{executable}': {e}")
        return None


def get_executable_version(executable: str, version_args: List[str] = None) -> Optional[str]:
    """Get version information for an executable.
    
    Args:
        executable: Name or path of the executable
        version_args: Arguments to pass to get version (defaults to ['--version'])
        
    Returns:
        Version string if available, None otherwise
    """
    if version_args is None:
        version_args = ['--version']
    
    try:
        # First check if executable exists
        if not is_executable_available(executable):
            return None
            
        # Run the version command
        result = subprocess.run(
            [executable] + version_args,
            capture_output=True,
            text=True,
            timeout=10,  # 10 second timeout
            check=False  # Don't raise exception on non-zero exit
        )
        
        # Some tools output version to stderr instead of stdout
        version_output = result.stdout.strip() or result.stderr.strip()
        
        if version_output:
            # Take first line of output (version info is usually on first line)
            version_line = version_output.split('\n')[0]
            logger.debug(f"Version for '{executable}': {version_line}")
            return version_line
        else:
            logger.debug(f"No version output from '{executable}'")
            return None
            
    except subprocess.TimeoutExpired:
        logger.warning(f"Timeout getting version for '{executable}'")
        return None
    except Exception as e:
        logger.warning(f"Error getting version for '{executable}': {e}")
        return None


def check_executable_functionality(executable: str, test_command: List[str], 
                                  expected_exit_code: int = 0, timeout: int = 30) -> bool:
    """Test if an executable is functional by running a test command.
    
    Args:
        executable: Name or path of the executable
        test_command: Complete command to test (including executable)
        expected_exit_code: Expected exit code for successful test
        timeout: Timeout in seconds for the test command
        
    Returns:
        True if test passes, False otherwise
    """
    try:
        # First check if executable exists
        if not is_executable_available(executable):
            logger.debug(f"Executable '{executable}' not available for functionality test")
            return False
            
        logger.debug(f"Testing functionality of '{executable}' with command: {test_command}")
        
        # Validate command arguments to prevent injection
        if not all(isinstance(arg, str) for arg in test_command):
            logger.warning(f"Invalid command arguments for '{executable}': non-string arguments detected")
            return False
        
        # Run the test command with security constraints
        # Use the full environment for compatibility, but this is safe since we're only
        # running version/test commands from known executables
        safe_env = os.environ.copy()
        
        result = subprocess.run(
            test_command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,  # Don't raise exception on non-zero exit
            shell=False,  # Never use shell=True for security
            env=safe_env,
        )
        
        success = result.returncode == expected_exit_code
        
        if success:
            logger.debug(f"Functionality test passed for '{executable}'")
        else:
            logger.debug(
                f"Functionality test failed for '{executable}': "
                f"exit code {result.returncode} (expected {expected_exit_code})"
            )
            
        return success
        
    except subprocess.TimeoutExpired:
        logger.warning(f"Timeout during functionality test for '{executable}'")
        return False
    except Exception as e:
        logger.warning(f"Error during functionality test for '{executable}': {e}")
        return False


def get_system_info() -> Dict[str, str]:
    """Get basic system information.
    
    Returns:
        Dictionary with system information
    """
    try:
        return {
            'platform': get_platform(),
            'system': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor(),
        }
    except Exception as e:
        logger.warning(f"Error getting system info: {e}")
        return {'platform': 'unknown'}


def is_platform_supported(supported_platforms: List[str]) -> bool:
    """Check if current platform is in the list of supported platforms.
    
    Args:
        supported_platforms: List of supported platform identifiers
        
    Returns:
        True if current platform is supported, False otherwise
    """
    if not supported_platforms:
        # If no platforms specified, assume all platforms are supported
        return True
        
    current_platform = get_platform()
    
    # Check for exact match
    if current_platform in supported_platforms:
        return True
        
    # Check for common aliases
    platform_aliases = {
        'darwin': ['macos', 'osx'],
        'linux': ['ubuntu', 'debian', 'centos', 'rhel', 'fedora', 'arch'],
        'windows': ['win32', 'win64'],
    }
    
    for platform_name, aliases in platform_aliases.items():
        if current_platform == platform_name:
            # Check if any alias is in supported platforms
            if any(alias in supported_platforms for alias in aliases):
                return True
        elif current_platform in aliases and platform_name in supported_platforms:
            return True
            
    return False


def check_network_connectivity(host: str = "8.8.8.8", port: int = 53, timeout: int = 5) -> bool:
    """Check if network connectivity is available.
    
    Args:
        host: Host to test connectivity to (default: Google DNS)
        port: Port to test (default: 53 for DNS)
        timeout: Timeout in seconds
        
    Returns:
        True if network is available, False otherwise
    """
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        logger.debug(f"Network connectivity check successful to {host}:{port}")
        return True
    except (socket.error, OSError) as e:
        logger.debug(f"Network connectivity check failed to {host}:{port}: {e}")
        return False
    except Exception as e:
        logger.warning(f"Unexpected error during network connectivity check: {e}")
        return False


def check_url_accessibility(url: str, timeout: int = 10) -> Tuple[bool, Optional[str]]:
    """Check if a specific URL is accessible.
    
    Args:
        url: URL to check accessibility
        timeout: Timeout in seconds
        
    Returns:
        Tuple of (is_accessible, error_message)
    """
    try:
        parsed_url = urlparse(url)
        if not parsed_url.hostname:
            return False, "Invalid URL format"
        
        # For git URLs, check if we can resolve the hostname
        if url.startswith(('git://', 'ssh://', 'git@')):
            # Extract hostname from git URLs
            if url.startswith('git@'):
                # Format: git@hostname:path
                hostname = url.split('@')[1].split(':')[0]
            else:
                hostname = parsed_url.hostname
            
            # Try to resolve hostname
            try:
                socket.gethostbyname(hostname)
                logger.debug(f"Git URL hostname resolution successful: {hostname}")
                return True, None
            except socket.gaierror as e:
                error_msg = f"Cannot resolve hostname {hostname}: {e}"
                logger.debug(error_msg)
                return False, error_msg
        
        # For HTTP/HTTPS URLs, try a simple connection test
        elif url.startswith(('http://', 'https://')):
            port = parsed_url.port or (443 if url.startswith('https://') else 80)
            
            try:
                socket.setdefaulttimeout(timeout)
                socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((parsed_url.hostname, port))
                logger.debug(f"HTTP URL accessibility check successful: {url}")
                return True, None
            except (socket.error, OSError) as e:
                error_msg = f"Cannot connect to {parsed_url.hostname}:{port}: {e}"
                logger.debug(error_msg)
                return False, error_msg
        
        else:
            return False, f"Unsupported URL scheme: {parsed_url.scheme}"
            
    except Exception as e:
        error_msg = f"Error checking URL accessibility: {e}"
        logger.warning(error_msg)
        return False, error_msg


def detect_offline_mode() -> Tuple[bool, str]:
    """Detect if the system should operate in offline mode.
    
    Returns:
        Tuple of (is_offline, reason)
    """
    # Check basic network connectivity
    if not check_network_connectivity():
        return True, "No network connectivity detected"
    
    # Check if we can reach common internet services
    test_hosts = [
        ("github.com", 443),
        ("gitlab.com", 443),
        ("bitbucket.org", 443)
    ]
    
    accessible_count = 0
    for host, port in test_hosts:
        try:
            socket.setdefaulttimeout(5)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
            accessible_count += 1
            logger.debug(f"Successfully connected to {host}:{port}")
        except (socket.error, OSError):
            logger.debug(f"Failed to connect to {host}:{port}")
            continue
    
    # If we can't reach any of the common git hosting services, consider offline
    if accessible_count == 0:
        return True, "Cannot reach common git hosting services"
    
    logger.debug(f"Network connectivity OK: {accessible_count}/{len(test_hosts)} services accessible")
    return False, "Network connectivity available"


class NetworkConnectivityTracker:
    """Track network connectivity and failure patterns for exponential backoff."""
    
    def __init__(self):
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._backoff_delay = 1.0  # Start with 1 second
        self._max_backoff_delay = 300.0  # Maximum 5 minutes
        self._reset_threshold = 3600.0  # Reset after 1 hour of no failures
    
    def record_failure(self) -> None:
        """Record a network operation failure."""
        self._failure_count += 1
        self._last_failure_time = time.time()
        
        # Exponential backoff with jitter
        self._backoff_delay = min(
            self._backoff_delay * 2,
            self._max_backoff_delay
        )
        
        logger.debug(f"Network failure recorded (count: {self._failure_count}, "
                    f"next backoff: {self._backoff_delay}s)")
    
    def record_success(self) -> None:
        """Record a successful network operation."""
        if self._failure_count > 0:
            logger.debug(f"Network operation successful after {self._failure_count} failures")
        
        self._failure_count = 0
        self._last_failure_time = None
        self._backoff_delay = 1.0
    
    def should_retry(self) -> Tuple[bool, float]:
        """Check if we should retry and return the delay.
        
        Returns:
            Tuple of (should_retry, delay_seconds)
        """
        if self._failure_count == 0:
            return True, 0.0
        
        # Reset failure count if enough time has passed
        if (self._last_failure_time and 
            time.time() - self._last_failure_time > self._reset_threshold):
            logger.debug("Resetting network failure count after threshold period")
            self.record_success()
            return True, 0.0
        
        # Apply exponential backoff
        return True, self._backoff_delay
    
    def get_failure_count(self) -> int:
        """Get the current failure count."""
        return self._failure_count
    
    def get_backoff_delay(self) -> float:
        """Get the current backoff delay."""
        return self._backoff_delay