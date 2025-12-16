"""Filesystem monitoring for tracking installation changes.

This module provides filesystem monitoring capabilities to detect changes
during software installation, including new files, services, and binaries.
"""

import logging
from dataclasses import dataclass
from typing import List, Set, Optional
from datetime import datetime, timezone

from saitest.utils.config_loader import get_config


logger = logging.getLogger(__name__)


@dataclass
class FileChange:
    """Represents a filesystem change detected during monitoring.
    
    Attributes:
        path: Absolute path to the file
        change_type: Type of change (new, modified, deleted)
        timestamp: When the change was detected
        size: File size in bytes
        permissions: File permissions (e.g., "755")
    """
    path: str
    change_type: str
    timestamp: str
    size: int
    permissions: str


class FilesystemMonitor:
    """Monitor filesystem changes during software installation.
    
    This class captures filesystem state before and after installation
    to identify new files, services, and binaries created by the installation.
    
    Attributes:
        container: ContainerWrapper instance for executing commands
        baseline_files: Set of file paths before installation
        scan_timeout: Timeout for filesystem scan operations in seconds
        max_depth: Maximum directory depth for scanning
    """
    
    # Default paths to monitor (can be customized)
    DEFAULT_MONITORED_PATHS = [
        "/usr/bin",
        "/usr/sbin",
        "/usr/local/bin",
        "/usr/local/sbin",
        "/bin",
        "/sbin",
        "/etc",
        "/lib/systemd/system",
        "/usr/lib/systemd/system",
        "/etc/systemd/system",
        "/opt",
        "/var/lib",
    ]
    
    def __init__(self, container, scan_timeout: Optional[int] = None, 
                 max_depth: Optional[int] = None, 
                 monitored_paths: Optional[List[str]] = None):
        """Initialize filesystem monitor.
        
        Args:
            container: ContainerWrapper instance
            scan_timeout: Timeout for filesystem scan operations in seconds (default: from config)
            max_depth: Maximum directory depth for scanning (default: from config)
            monitored_paths: Custom list of paths to monitor (default: from config or DEFAULT_MONITORED_PATHS)
        """
        self.container = container
        self.baseline_files: Optional[Set[str]] = None
        
        # Load configuration
        config = get_config()
        self.scan_timeout = scan_timeout or config.get("verification.filesystem.scan_timeout", 120)
        self.max_depth = max_depth or config.get("verification.filesystem.max_depth", 10)
        
        # Use provided paths, or from config, or defaults
        if monitored_paths:
            self.monitored_paths = monitored_paths
        else:
            config_paths = config.get("verification.filesystem.monitored_paths", [])
            self.monitored_paths = config_paths if config_paths else self.DEFAULT_MONITORED_PATHS
        
        self._logger = logging.getLogger(f"{__name__}.{container.platform}")
    
    def capture_baseline(self) -> None:
        """Capture filesystem baseline before installation.
        
        This method scans key directories and stores the current state
        of the filesystem for later comparison. Uses optimized scanning
        with depth limits and timeouts.
        """
        self._logger.info("Capturing filesystem baseline")
        
        baseline_files = set()
        
        # Build optimized find command that scans all paths in one go
        # This is much faster than scanning each path separately
        paths_str = " ".join(self.monitored_paths)
        
        # Use find with:
        # - maxdepth to limit recursion
        # - type f for files only
        # - parallel execution with xargs for better performance
        # - timeout to prevent hanging
        command = (
            f"timeout {self.scan_timeout} "
            f"find {paths_str} -maxdepth {self.max_depth} -type f "
            f"2>/dev/null || true"
        )
        
        result = self.container.exec(command, timeout=self.scan_timeout + 10)
        
        if result["success"] and result["output"]:
            files = [
                line.strip() 
                for line in result["output"].split('\n') 
                if line.strip()
            ]
            baseline_files.update(files)
            self._logger.debug(f"Scanned {len(self.monitored_paths)} paths, found {len(files)} files")
        elif not result["success"]:
            self._logger.warning(f"Baseline scan completed with warnings: {result['output'][:200]}")
        
        self.baseline_files = baseline_files
        self._logger.info(f"Baseline captured: {len(baseline_files)} files in {self.scan_timeout}s timeout")
    
    def capture_changes(self) -> List[FileChange]:
        """Detect filesystem changes since baseline.
        
        Returns:
            List of FileChange objects representing new or modified files
        
        Raises:
            RuntimeError: If baseline was not captured first
        """
        if self.baseline_files is None:
            raise RuntimeError("Baseline not captured. Call capture_baseline() first.")
        
        self._logger.info("Capturing filesystem changes")
        
        # Use optimized single-pass scanning
        paths_str = " ".join(self.monitored_paths)
        command = (
            f"timeout {self.scan_timeout} "
            f"find {paths_str} -maxdepth {self.max_depth} -type f "
            f"2>/dev/null || true"
        )
        
        result = self.container.exec(command, timeout=self.scan_timeout + 10)
        
        current_files = set()
        if result["success"] and result["output"]:
            files = [
                line.strip() 
                for line in result["output"].split('\n') 
                if line.strip()
            ]
            current_files.update(files)
        
        # Find new files (set difference is very fast)
        new_files = current_files - self.baseline_files
        self._logger.info(f"Detected {len(new_files)} new files")
        
        # Optimize: batch stat commands for better performance
        changes = []
        timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        
        if new_files:
            # Batch stat commands - much faster than individual calls
            # Create a single command that stats all files at once
            files_list = list(new_files)
            
            # Process in batches to avoid command line length limits
            batch_size = 100
            for i in range(0, len(files_list), batch_size):
                batch = files_list[i:i + batch_size]
                
                # Build stat command for batch
                # Format: path|size|permissions for each file
                stat_cmd = " && ".join([
                    f"stat -c '%n|%s|%a' {file_path} 2>/dev/null || echo '{file_path}|0|000'"
                    for file_path in batch
                ])
                
                result = self.container.exec(stat_cmd, timeout=30)
                
                if result["success"] and result["output"]:
                    for line in result["output"].strip().split('\n'):
                        if '|' in line:
                            parts = line.split('|')
                            if len(parts) >= 3:
                                file_path = parts[0]
                                size = int(parts[1]) if parts[1].isdigit() else 0
                                permissions = parts[2]
                                
                                change = FileChange(
                                    path=file_path,
                                    change_type="new",
                                    timestamp=timestamp,
                                    size=size,
                                    permissions=permissions
                                )
                                changes.append(change)
        
        self._logger.info(f"Captured {len(changes)} file changes with metadata")
        return changes
    
    def get_service_files(self) -> List[str]:
        """Find systemd service files created during installation.
        
        Returns:
            List of paths to systemd service files
        """
        self._logger.debug("Finding service files")
        
        service_paths = [
            "/lib/systemd/system",
            "/usr/lib/systemd/system",
            "/etc/systemd/system",
        ]
        
        # Optimized: scan all service paths in one command
        paths_str = " ".join(service_paths)
        command = (
            f"timeout 30 "
            f"find {paths_str} -maxdepth 3 -name '*.service' -type f "
            f"2>/dev/null || true"
        )
        
        result = self.container.exec(command, timeout=40)
        
        service_files = set()
        if result["success"] and result["output"]:
            files = [
                line.strip() 
                for line in result["output"].split('\n') 
                if line.strip()
            ]
            service_files.update(files)
        
        # Filter to only new service files if baseline exists
        if self.baseline_files is not None:
            service_files = service_files - self.baseline_files
        
        result_list = list(service_files)
        self._logger.info(f"Found {len(result_list)} service files")
        return result_list
    
    def get_binaries(self) -> List[str]:
        """Find executable binaries created during installation.
        
        Returns:
            List of paths to executable binaries
        """
        self._logger.debug("Finding binaries")
        
        binary_paths = [
            "/usr/bin",
            "/usr/sbin",
            "/usr/local/bin",
            "/usr/local/sbin",
            "/bin",
            "/sbin",
        ]
        
        # Optimized: scan all binary paths in one command
        paths_str = " ".join(binary_paths)
        command = (
            f"timeout 60 "
            f"find {paths_str} -maxdepth 3 -type f -executable "
            f"2>/dev/null || true"
        )
        
        result = self.container.exec(command, timeout=70)
        
        binaries = set()
        if result["success"] and result["output"]:
            files = [
                line.strip() 
                for line in result["output"].split('\n') 
                if line.strip()
            ]
            binaries.update(files)
        
        # Filter to only new binaries if baseline exists
        if self.baseline_files is not None:
            binaries = binaries - self.baseline_files
        
        result_list = list(binaries)
        self._logger.info(f"Found {len(result_list)} binaries")
        return result_list
