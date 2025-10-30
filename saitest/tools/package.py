"""Package installation tool for saitest.

This module provides a unified LangGraph tool for installing packages
using any provider via providerdata commands.
"""

import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from langchain_core.tools import tool

from saitest.utils.provider_executor import ProviderCommandExecutor, ProviderExecutorError
from saitest.utils.fs_monitor import FilesystemMonitor
from saitest.utils.docker_manager import ContainerManager
from saitest.models.observation import Observation
from saigen.models.saidata import SaiData


logger = logging.getLogger(__name__)


# Global container manager instance
_container_manager = None


def get_container_manager() -> ContainerManager:
    """Get or create global container manager instance.
    
    Returns:
        ContainerManager instance
    """
    global _container_manager
    if _container_manager is None:
        _container_manager = ContainerManager()
    return _container_manager


@tool
def install_package(
    platform: str,
    provider: str,
    package: str,
    saidata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Install package using specified provider and providerdata commands.
    
    This tool installs a package on a specified platform using the provider's
    commands from providerdata. It monitors filesystem changes during installation
    and returns structured results with observations.
    
    Args:
        platform: Platform identifier (e.g., "ubuntu:22.04", "debian:12")
        provider: Provider name (e.g., "apt", "dnf", "pip", "gem")
        package: Package name to install
        saidata: Optional SaiData dictionary for template resolution
    
    Returns:
        Dictionary with:
            - provider: Provider name used
            - platform: Platform identifier
            - success: Whether installation succeeded
            - output: Installation command output
            - test_output: Test command output (if available)
            - test_success: Whether test command succeeded (if available)
            - files_created: List of file paths created
            - services_found: List of service file paths
            - binaries_found: List of binary paths
            - observations: List of Observation dictionaries
            - errors: List of error messages
            - duration: Installation duration in seconds
    
    Example:
        >>> result = install_package(
        ...     platform="ubuntu:22.04",
        ...     provider="apt",
        ...     package="nginx"
        ... )
        >>> print(result["success"])
        True
        >>> print(len(result["files_created"]))
        42
    """
    start_time = time.time()
    tool_logger = logging.getLogger(f"{__name__}.{platform}.{provider}")
    
    tool_logger.info(
        f"Installing {package} on {platform} using {provider}"
    )
    
    # Initialize result structure
    result = {
        "provider": provider,
        "platform": platform,
        "success": False,
        "output": "",
        "test_output": None,
        "test_success": None,
        "files_created": [],
        "services_found": [],
        "binaries_found": [],
        "observations": [],
        "errors": [],
        "duration": 0.0
    }
    
    try:
        # Initialize provider executor
        executor = ProviderCommandExecutor()
        
        # Convert saidata dict to SaiData object if provided
        saidata_obj = None
        if saidata:
            try:
                saidata_obj = SaiData(**saidata)
            except Exception as e:
                tool_logger.warning(
                    f"Failed to parse saidata dictionary: {e}. "
                    "Using package name for template resolution."
                )
        
        # Get install command from providerdata
        try:
            install_cmd = executor.get_install_command(
                provider_name=provider,
                saidata=saidata_obj,
                package_name=package
            )
            tool_logger.debug(f"Install command: {install_cmd}")
        except ProviderExecutorError as e:
            error_msg = f"Failed to get install command: {e}"
            tool_logger.error(error_msg)
            result["errors"].append(error_msg)
            result["duration"] = time.time() - start_time
            return result
        
        # Spawn container and execute installation
        container_manager = get_container_manager()
        
        with container_manager.spawn_container(platform) as container:
            # Initialize filesystem monitor
            monitor = FilesystemMonitor(container)
            
            # Capture baseline
            tool_logger.info("Capturing filesystem baseline")
            monitor.capture_baseline()
            
            # Execute installation command
            tool_logger.info(f"Executing install command: {install_cmd}")
            install_result = container.exec(install_cmd, timeout=600)
            
            result["output"] = install_result["output"]
            result["success"] = install_result["success"]
            
            if not install_result["success"]:
                error_msg = (
                    f"Installation failed with exit code {install_result['exit_code']}"
                )
                tool_logger.error(error_msg)
                result["errors"].append(error_msg)
                result["duration"] = time.time() - start_time
                return result
            
            tool_logger.info("Installation command succeeded")
            
            # Capture filesystem changes
            tool_logger.info("Capturing filesystem changes")
            file_changes = monitor.capture_changes()
            result["files_created"] = [fc.path for fc in file_changes]
            tool_logger.info(f"Found {len(file_changes)} new files")
            
            # Find services
            tool_logger.info("Finding service files")
            services = monitor.get_service_files()
            result["services_found"] = services
            tool_logger.info(f"Found {len(services)} service files")
            
            # Find binaries
            tool_logger.info("Finding binaries")
            binaries = monitor.get_binaries()
            result["binaries_found"] = binaries
            tool_logger.info(f"Found {len(binaries)} binaries")
            
            # Execute test command if available
            try:
                test_cmd = executor.get_test_command(
                    provider_name=provider,
                    saidata=saidata_obj,
                    package_name=package
                )
                
                if test_cmd:
                    tool_logger.info(f"Executing test command: {test_cmd}")
                    test_result = container.exec(test_cmd, timeout=60)
                    result["test_output"] = test_result["output"]
                    result["test_success"] = test_result["success"]
                    
                    if test_result["success"]:
                        tool_logger.info("Test command succeeded")
                    else:
                        tool_logger.warning(
                            f"Test command failed with exit code {test_result['exit_code']}"
                        )
                else:
                    tool_logger.debug("No test command available for this provider")
                    
            except Exception as e:
                tool_logger.warning(f"Error executing test command: {e}")
                # Don't fail the whole operation if test fails
            
            # Create observations
            timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            observations = []
            
            # File observations
            for file_path in result["files_created"]:
                obs = Observation(
                    type="file",
                    platform=platform,
                    provider=provider,
                    timestamp=timestamp,
                    data={"path": file_path},
                    confidence=1.0
                )
                observations.append(obs)
            
            # Service observations
            for service_path in result["services_found"]:
                obs = Observation(
                    type="service",
                    platform=platform,
                    provider=provider,
                    timestamp=timestamp,
                    data={"path": service_path},
                    confidence=0.9
                )
                observations.append(obs)
            
            # Binary observations
            for binary_path in result["binaries_found"]:
                obs = Observation(
                    type="binary",
                    platform=platform,
                    provider=provider,
                    timestamp=timestamp,
                    data={"path": binary_path},
                    confidence=0.95
                )
                observations.append(obs)
            
            # Package observation
            obs = Observation(
                type="package",
                platform=platform,
                provider=provider,
                timestamp=timestamp,
                data={
                    "package_name": package,
                    "provider": provider
                },
                confidence=1.0
            )
            observations.append(obs)
            
            # Convert observations to dictionaries for JSON serialization
            result["observations"] = [obs.model_dump() for obs in observations]
            
            tool_logger.info(
                f"Created {len(observations)} observations from installation"
            )
    
    except Exception as e:
        error_msg = f"Unexpected error during installation: {e}"
        tool_logger.error(error_msg, exc_info=True)
        result["errors"].append(error_msg)
        result["success"] = False
    
    finally:
        result["duration"] = time.time() - start_time
        tool_logger.info(
            f"Installation completed in {result['duration']:.2f}s "
            f"(success={result['success']})"
        )
    
    return result
