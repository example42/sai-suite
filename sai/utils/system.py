"""System detection utilities for SAI CLI tool."""

import logging
import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Dict, List


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
        result = subprocess.run(
            test_command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,  # Don't raise exception on non-zero exit
            shell=False,  # Never use shell=True for security
            env={'PATH': os.environ.get('PATH', '')},  # Minimal environment
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