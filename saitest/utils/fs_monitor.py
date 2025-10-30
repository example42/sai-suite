"""Filesystem monitoring for tracking installation changes.

This module provides filesystem monitoring capabilities to detect changes
during software installation, including new files, services, and binaries.
"""

import logging
from dataclasses import dataclass
from typing import List, Set, Optional
from datetime import datetime, timezone


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
    """
    
    def __init__(self, container):
        """Initialize filesystem monitor.
        
        Args:
            container: ContainerWrapper instance
        """
        self.container = container
        self.baseline_files: Optional[Set[str]] = None
        self._logger = logging.getLogger(f"{__name__}.{container.platform}")
    
    def capture_baseline(self) -> None:
        """Capture filesystem baseline before installation.
        
        This method scans key directories and stores the current state
        of the filesystem for later comparison.
        """
        self._logger.info("Capturing filesystem baseline")
        
        # Directories to monitor for changes
        monitored_paths = [
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
        
        baseline_files = set()
        
        for path in monitored_paths:
            # Use find to list all files in the directory
            # Ignore errors for paths that don't exist
            command = f"find {path} -type f 2>/dev/null || true"
            result = self.container.exec(command)
            
            if result["success"] and result["output"]:
                files = [
                    line.strip() 
                    for line in result["output"].split('\n') 
                    if line.strip()
                ]
                baseline_files.update(files)
                self._logger.debug(f"Found {len(files)} files in {path}")
        
        self.baseline_files = baseline_files
        self._logger.info(f"Baseline captured: {len(baseline_files)} files")
    
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
        
        # Same directories as baseline
        monitored_paths = [
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
        
        current_files = set()
        
        for path in monitored_paths:
            command = f"find {path} -type f 2>/dev/null || true"
            result = self.container.exec(command)
            
            if result["success"] and result["output"]:
                files = [
                    line.strip() 
                    for line in result["output"].split('\n') 
                    if line.strip()
                ]
                current_files.update(files)
        
        # Find new files
        new_files = current_files - self.baseline_files
        self._logger.info(f"Detected {len(new_files)} new files")
        
        # Get details for new files
        changes = []
        timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        
        for file_path in new_files:
            # Get file details using stat
            stat_command = f"stat -c '%s %a' {file_path} 2>/dev/null || echo '0 000'"
            result = self.container.exec(stat_command)
            
            if result["success"] and result["output"]:
                parts = result["output"].strip().split()
                size = int(parts[0]) if len(parts) > 0 else 0
                permissions = parts[1] if len(parts) > 1 else "000"
                
                change = FileChange(
                    path=file_path,
                    change_type="new",
                    timestamp=timestamp,
                    size=size,
                    permissions=permissions
                )
                changes.append(change)
        
        self._logger.info(f"Captured {len(changes)} file changes")
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
        
        service_files = set()
        
        for path in service_paths:
            # Find .service files
            command = f"find {path} -name '*.service' -type f 2>/dev/null || true"
            result = self.container.exec(command)
            
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
        
        binaries = set()
        
        for path in binary_paths:
            # Find executable files
            command = f"find {path} -type f -executable 2>/dev/null || true"
            result = self.container.exec(command)
            
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
