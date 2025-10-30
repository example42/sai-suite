"""Docker container management for saitest.

This module provides container lifecycle management and operations for
testing software installations in isolated Docker environments.
"""

import logging
from contextlib import contextmanager
from typing import Dict, Any, List, Optional
import docker
from docker.models.containers import Container
from docker.errors import DockerException, ImageNotFound, APIError


logger = logging.getLogger(__name__)


# Platform to Docker image mapping
PLATFORM_IMAGE_MAP = {
    "ubuntu:22.04": "ubuntu:22.04",
    "ubuntu:24.04": "ubuntu:24.04",
    "ubuntu:20.04": "ubuntu:20.04",
    "debian:12": "debian:12",
    "debian:11": "debian:11",
    "debian:10": "debian:10",
    "fedora:40": "fedora:40",
    "fedora:39": "fedora:39",
    "centos:9": "quay.io/centos/centos:stream9",
    "centos:8": "quay.io/centos/centos:stream8",
    "rocky:9": "rockylinux:9",
    "rocky:8": "rockylinux:8",
    "alpine:3.19": "alpine:3.19",
    "alpine:3.18": "alpine:3.18",
}


class ContainerWrapper:
    """Wrapper for Docker container operations.
    
    Provides high-level methods for executing commands and accessing
    files within a Docker container.
    
    Attributes:
        container: Docker container instance
        platform: Platform identifier (e.g., "ubuntu:22.04")
    """
    
    def __init__(self, container: Container, platform: str):
        """Initialize container wrapper.
        
        Args:
            container: Docker container instance
            platform: Platform identifier
        """
        self.container = container
        self.platform = platform
        self._logger = logging.getLogger(f"{__name__}.{platform}")
    
    def exec(self, command: str, timeout: int = 300) -> Dict[str, Any]:
        """Execute command in container and return result.
        
        Args:
            command: Command to execute
            timeout: Command timeout in seconds (default: 300)
        
        Returns:
            Dictionary with:
                - exit_code: Command exit code
                - output: Combined stdout and stderr
                - success: Whether command succeeded (exit_code == 0)
        """
        self._logger.debug(f"Executing command: {command}")
        
        try:
            result = self.container.exec_run(
                cmd=["sh", "-c", command],
                demux=False,
                tty=False,
                privileged=True,
                user="root"
            )
            
            exit_code = result.exit_code
            output = result.output.decode('utf-8', errors='replace') if result.output else ""
            success = exit_code == 0
            
            if not success:
                self._logger.warning(
                    f"Command failed with exit code {exit_code}: {command[:100]}"
                )
            
            return {
                "exit_code": exit_code,
                "output": output,
                "success": success
            }
            
        except Exception as e:
            self._logger.error(f"Error executing command: {e}")
            return {
                "exit_code": -1,
                "output": str(e),
                "success": False
            }
    
    def read_file(self, path: str) -> Optional[str]:
        """Read file contents from container.
        
        Args:
            path: Absolute path to file in container
        
        Returns:
            File contents as string, or None if file doesn't exist or error occurs
        """
        self._logger.debug(f"Reading file: {path}")
        
        result = self.exec(f"cat {path}")
        if result["success"]:
            return result["output"]
        
        self._logger.warning(f"Failed to read file {path}: {result['output']}")
        return None
    
    def list_files(self, path: str, pattern: str = "*") -> List[str]:
        """List files in directory.
        
        Args:
            path: Directory path in container
            pattern: Glob pattern for filtering (default: "*")
        
        Returns:
            List of file paths
        """
        self._logger.debug(f"Listing files in {path} with pattern {pattern}")
        
        # Use find command for reliable file listing
        command = f"find {path} -name '{pattern}' -type f 2>/dev/null || true"
        result = self.exec(command)
        
        if result["success"] and result["output"]:
            files = [line.strip() for line in result["output"].split('\n') if line.strip()]
            return files
        
        return []


class ContainerManager:
    """Manage Docker container lifecycle for testing.
    
    Provides methods for spawning containers, tracking active containers,
    and ensuring proper cleanup.
    
    Attributes:
        client: Docker client instance
        active_containers: Dictionary of active containers by platform
    """
    
    def __init__(self):
        """Initialize container manager."""
        self._logger = logging.getLogger(__name__)
        self.client: Optional[docker.DockerClient] = None
        self.active_containers: Dict[str, Container] = {}
        
        try:
            self.client = docker.from_env()
            self._logger.info("Docker client initialized successfully")
        except DockerException as e:
            self._logger.error(f"Failed to initialize Docker client: {e}")
            raise RuntimeError(
                "Docker is not available. Please ensure Docker is installed and running."
            ) from e
    
    def get_image_for_platform(self, platform: str) -> str:
        """Map platform identifier to Docker image name.
        
        Args:
            platform: Platform identifier (e.g., "ubuntu:22.04")
        
        Returns:
            Docker image name
        
        Raises:
            ValueError: If platform is not supported
        """
        image = PLATFORM_IMAGE_MAP.get(platform)
        if not image:
            raise ValueError(
                f"Unsupported platform: {platform}. "
                f"Supported platforms: {', '.join(PLATFORM_IMAGE_MAP.keys())}"
            )
        return image
    
    def _pull_image_if_needed(self, image: str) -> None:
        """Pull Docker image if not already cached.
        
        Args:
            image: Docker image name
        """
        try:
            self.client.images.get(image)
            self._logger.debug(f"Image {image} already cached")
        except ImageNotFound:
            self._logger.info(f"Pulling image {image}...")
            try:
                self.client.images.pull(image)
                self._logger.info(f"Successfully pulled image {image}")
            except Exception as e:
                self._logger.error(f"Failed to pull image {image}: {e}")
                raise
    
    @contextmanager
    def spawn_container(self, platform: str):
        """Spawn a container for the specified platform.
        
        This is a context manager that ensures proper container cleanup.
        
        Args:
            platform: Platform identifier (e.g., "ubuntu:22.04")
        
        Yields:
            ContainerWrapper instance for container operations
        
        Raises:
            ValueError: If platform is not supported
            RuntimeError: If container creation fails
        
        Example:
            >>> manager = ContainerManager()
            >>> with manager.spawn_container("ubuntu:22.04") as container:
            ...     result = container.exec("apt-get update")
            ...     print(result["success"])
        """
        image = self.get_image_for_platform(platform)
        container = None
        
        try:
            # Pull image if needed
            self._pull_image_if_needed(image)
            
            # Create container
            self._logger.info(f"Creating container for platform {platform}")
            container = self.client.containers.run(
                image=image,
                command="sleep infinity",
                detach=True,
                privileged=True,
                tty=True,
                remove=False,  # We'll remove manually for better error handling
                name=f"saitest-{platform.replace(':', '-')}-{id(self)}"
            )
            
            # Track active container
            self.active_containers[platform] = container
            self._logger.info(f"Container {container.short_id} created for {platform}")
            
            # Yield wrapper
            yield ContainerWrapper(container, platform)
            
        except APIError as e:
            self._logger.error(f"Docker API error creating container: {e}")
            raise RuntimeError(f"Failed to create container for {platform}: {e}") from e
        
        except Exception as e:
            self._logger.error(f"Unexpected error creating container: {e}")
            raise RuntimeError(f"Failed to create container for {platform}: {e}") from e
        
        finally:
            # Cleanup container
            if container:
                try:
                    self._logger.info(f"Stopping container {container.short_id}")
                    container.stop(timeout=10)
                    self._logger.info(f"Removing container {container.short_id}")
                    container.remove(force=True)
                    self._logger.info(f"Container {container.short_id} cleaned up")
                except Exception as e:
                    self._logger.error(f"Error cleaning up container: {e}")
                finally:
                    # Remove from active containers
                    if platform in self.active_containers:
                        del self.active_containers[platform]
    
    def cleanup_all(self) -> None:
        """Clean up all active containers.
        
        This method should be called on shutdown to ensure no containers
        are left running.
        """
        self._logger.info("Cleaning up all active containers")
        
        for platform, container in list(self.active_containers.items()):
            try:
                self._logger.info(f"Stopping container for {platform}")
                container.stop(timeout=10)
                container.remove(force=True)
                self._logger.info(f"Container for {platform} cleaned up")
            except Exception as e:
                self._logger.error(f"Error cleaning up container for {platform}: {e}")
            finally:
                del self.active_containers[platform]
        
        self._logger.info("All containers cleaned up")
    
    def __del__(self):
        """Cleanup on deletion."""
        if hasattr(self, 'active_containers') and self.active_containers:
            self.cleanup_all()
