"""System inspection tools for saitest.

This module provides LangGraph tools for inspecting system state,
including services, ports, and configuration files.
"""

import logging
from typing import Dict, Any, List, Optional

from langchain_core.tools import tool

from saitest.utils.docker_manager import ContainerManager


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
def inspect_service(platform: str, service_name: str) -> Dict[str, Any]:
    """Inspect systemd service configuration and status.
    
    This tool checks the status of a systemd service, retrieves its
    configuration, and determines if it's enabled to start on boot.
    
    Args:
        platform: Platform identifier (e.g., "ubuntu:22.04", "debian:12")
        service_name: Name of the service to inspect (e.g., "nginx", "apache2")
    
    Returns:
        Dictionary with:
            - service_name: Name of the service
            - status: Service status output from systemctl status
            - active: Whether service is currently active (running)
            - enabled: Whether service is enabled to start on boot
            - config: Service unit file contents
            - unit_file_path: Path to the service unit file
            - success: Whether inspection succeeded
            - errors: List of error messages
    
    Example:
        >>> result = inspect_service(
        ...     platform="ubuntu:22.04",
        ...     service_name="nginx"
        ... )
        >>> print(result["active"])
        True
        >>> print(result["enabled"])
        True
    """
    tool_logger = logging.getLogger(f"{__name__}.{platform}")
    tool_logger.info(f"Inspecting service {service_name} on {platform}")
    
    result = {
        "service_name": service_name,
        "status": "",
        "active": False,
        "enabled": False,
        "config": "",
        "unit_file_path": "",
        "success": False,
        "errors": []
    }
    
    try:
        container_manager = get_container_manager()
        
        with container_manager.spawn_container(platform) as container:
            # Get service status
            tool_logger.debug(f"Getting status for {service_name}")
            status_result = container.exec(
                f"systemctl status {service_name} 2>&1 || true"
            )
            result["status"] = status_result["output"]
            
            # Check if service is active
            active_result = container.exec(
                f"systemctl is-active {service_name} 2>&1"
            )
            result["active"] = active_result["output"].strip() == "active"
            tool_logger.debug(f"Service active: {result['active']}")
            
            # Check if service is enabled
            enabled_result = container.exec(
                f"systemctl is-enabled {service_name} 2>&1"
            )
            enabled_output = enabled_result["output"].strip()
            result["enabled"] = enabled_output in ["enabled", "static"]
            tool_logger.debug(f"Service enabled: {result['enabled']}")
            
            # Get service configuration
            tool_logger.debug(f"Getting configuration for {service_name}")
            config_result = container.exec(
                f"systemctl cat {service_name} 2>&1 || true"
            )
            result["config"] = config_result["output"]
            
            # Try to find unit file path
            unit_path_result = container.exec(
                f"systemctl show -p FragmentPath {service_name} 2>&1 || true"
            )
            if unit_path_result["success"]:
                # Parse FragmentPath=<path> output
                for line in unit_path_result["output"].split('\n'):
                    if line.startswith("FragmentPath="):
                        result["unit_file_path"] = line.split('=', 1)[1].strip()
                        break
            
            result["success"] = True
            tool_logger.info(
                f"Successfully inspected service {service_name} "
                f"(active={result['active']}, enabled={result['enabled']})"
            )
    
    except Exception as e:
        error_msg = f"Error inspecting service {service_name}: {e}"
        tool_logger.error(error_msg, exc_info=True)
        result["errors"].append(error_msg)
        result["success"] = False
    
    return result


@tool
def check_listening_ports(platform: str) -> Dict[str, Any]:
    """Check which network ports are listening on the system.
    
    This tool uses the 'ss' command to identify all listening TCP and UDP ports,
    including the process that's listening on each port.
    
    Args:
        platform: Platform identifier (e.g., "ubuntu:22.04", "debian:12")
    
    Returns:
        Dictionary with:
            - ports: List of port dictionaries, each containing:
                - port: Port number
                - protocol: Protocol (tcp/udp)
                - address: Listening address (e.g., "0.0.0.0", "127.0.0.1")
                - process: Process name (if available)
            - success: Whether check succeeded
            - errors: List of error messages
    
    Example:
        >>> result = check_listening_ports(platform="ubuntu:22.04")
        >>> print(len(result["ports"]))
        5
        >>> print(result["ports"][0])
        {'port': 80, 'protocol': 'tcp', 'address': '0.0.0.0', 'process': 'nginx'}
    """
    tool_logger = logging.getLogger(f"{__name__}.{platform}")
    tool_logger.info(f"Checking listening ports on {platform}")
    
    result = {
        "ports": [],
        "success": False,
        "errors": []
    }
    
    try:
        container_manager = get_container_manager()
        
        with container_manager.spawn_container(platform) as container:
            # Use ss command to list listening ports
            # -t: TCP, -u: UDP, -l: listening, -n: numeric, -p: show process
            tool_logger.debug("Executing ss command to list listening ports")
            ss_result = container.exec(
                "ss -tulnp 2>&1 || netstat -tulnp 2>&1 || true"
            )
            
            if not ss_result["output"]:
                tool_logger.warning("No output from ss/netstat command")
                result["success"] = True
                return result
            
            # Parse ss output
            ports = []
            for line in ss_result["output"].split('\n'):
                line = line.strip()
                
                # Skip header lines and empty lines
                if not line or line.startswith('Netid') or line.startswith('Proto'):
                    continue
                
                # Parse line (format varies between ss and netstat)
                parts = line.split()
                if len(parts) < 5:
                    continue
                
                try:
                    # Determine protocol
                    protocol = parts[0].lower()
                    if protocol not in ['tcp', 'udp']:
                        continue
                    
                    # Parse local address (format: address:port or [address]:port)
                    local_addr = parts[4] if len(parts) > 4 else parts[3]
                    
                    # Extract address and port
                    if ':' in local_addr:
                        # Handle IPv6 addresses in brackets
                        if local_addr.startswith('['):
                            # Format: [address]:port
                            addr_end = local_addr.index(']')
                            address = local_addr[1:addr_end]
                            port_str = local_addr[addr_end+2:]  # Skip ']:' 
                        else:
                            # Format: address:port
                            addr_parts = local_addr.rsplit(':', 1)
                            address = addr_parts[0]
                            port_str = addr_parts[1]
                        
                        # Convert port to integer
                        try:
                            port = int(port_str)
                        except ValueError:
                            # Port might be '*' or service name
                            continue
                        
                        # Extract process name if available
                        process = ""
                        if len(parts) > 6:
                            # Process info is usually in the last column
                            process_info = parts[-1]
                            # Format: users:(("process",pid=123,fd=4))
                            if '((' in process_info:
                                start = process_info.index('((') + 3
                                end = process_info.index('"', start)
                                process = process_info[start:end]
                        
                        ports.append({
                            "port": port,
                            "protocol": protocol,
                            "address": address,
                            "process": process
                        })
                        
                except (ValueError, IndexError) as e:
                    tool_logger.debug(f"Failed to parse line: {line} - {e}")
                    continue
            
            result["ports"] = ports
            result["success"] = True
            tool_logger.info(f"Found {len(ports)} listening ports")
    
    except Exception as e:
        error_msg = f"Error checking listening ports: {e}"
        tool_logger.error(error_msg, exc_info=True)
        result["errors"].append(error_msg)
        result["success"] = False
    
    return result


@tool
def find_config_files(platform: str, software: str) -> Dict[str, Any]:
    """Find configuration files for specified software.
    
    This tool searches common configuration directories for files related
    to the specified software package.
    
    Args:
        platform: Platform identifier (e.g., "ubuntu:22.04", "debian:12")
        software: Software name to search for (e.g., "nginx", "apache")
    
    Returns:
        Dictionary with:
            - config_files: List of configuration file paths found
            - success: Whether search succeeded
            - errors: List of error messages
    
    Example:
        >>> result = find_config_files(
        ...     platform="ubuntu:22.04",
        ...     software="nginx"
        ... )
        >>> print(result["config_files"])
        ['/etc/nginx/nginx.conf', '/etc/nginx/sites-available/default']
    """
    tool_logger = logging.getLogger(f"{__name__}.{platform}")
    tool_logger.info(f"Finding config files for {software} on {platform}")
    
    result = {
        "config_files": [],
        "success": False,
        "errors": []
    }
    
    try:
        container_manager = get_container_manager()
        
        with container_manager.spawn_container(platform) as container:
            # Search common configuration directories
            search_paths = [
                f"/etc/{software}",
                f"/etc/{software}.conf",
                f"/etc/{software}.d",
                f"/usr/local/etc/{software}",
                f"/opt/{software}/etc",
                f"/opt/{software}/conf",
            ]
            
            config_files = []
            
            for search_path in search_paths:
                tool_logger.debug(f"Searching {search_path}")
                
                # Check if path exists
                check_result = container.exec(
                    f"test -e {search_path} && echo exists || echo notfound"
                )
                
                if "exists" not in check_result["output"]:
                    continue
                
                # Check if it's a file or directory
                type_result = container.exec(
                    f"test -f {search_path} && echo file || "
                    f"test -d {search_path} && echo dir || echo unknown"
                )
                
                path_type = type_result["output"].strip()
                
                if path_type == "file":
                    # It's a file, add it directly
                    config_files.append(search_path)
                    tool_logger.debug(f"Found config file: {search_path}")
                
                elif path_type == "dir":
                    # It's a directory, find all files in it
                    find_result = container.exec(
                        f"find {search_path} -type f 2>/dev/null || true"
                    )
                    
                    if find_result["success"] and find_result["output"]:
                        files = [
                            line.strip()
                            for line in find_result["output"].split('\n')
                            if line.strip()
                        ]
                        config_files.extend(files)
                        tool_logger.debug(
                            f"Found {len(files)} files in {search_path}"
                        )
            
            # Also search for common config file patterns
            pattern_searches = [
                f"/etc/*{software}*.conf",
                f"/etc/default/{software}",
                f"/etc/sysconfig/{software}",
            ]
            
            for pattern in pattern_searches:
                tool_logger.debug(f"Searching pattern {pattern}")
                find_result = container.exec(
                    f"find /etc -maxdepth 2 -name '*{software}*.conf' "
                    f"-type f 2>/dev/null || true"
                )
                
                if find_result["success"] and find_result["output"]:
                    files = [
                        line.strip()
                        for line in find_result["output"].split('\n')
                        if line.strip() and line.strip() not in config_files
                    ]
                    config_files.extend(files)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_files = []
            for f in config_files:
                if f not in seen:
                    seen.add(f)
                    unique_files.append(f)
            
            result["config_files"] = unique_files
            result["success"] = True
            tool_logger.info(
                f"Found {len(unique_files)} config files for {software}"
            )
    
    except Exception as e:
        error_msg = f"Error finding config files for {software}: {e}"
        tool_logger.error(error_msg, exc_info=True)
        result["errors"].append(error_msg)
        result["success"] = False
    
    return result
