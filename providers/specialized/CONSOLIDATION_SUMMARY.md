# Provider Consolidation Summary

This document summarizes the consolidation of overlapping providers in the SAI specialized providers directory.

## Consolidated Providers

### 1. Process Management (`process.yaml`)
**Replaces:** `ps.yaml`, `pkill.yaml`, `pgrep.yaml`, `killall.yaml`

**Functionality:**
- Process listing and searching
- Process information and status checking
- Process termination (graceful and forced)
- Process restart capabilities
- Real-time process monitoring
- Cross-platform support (Linux, macOS, Windows)

**Key Features:**
- Intelligent kill method selection (pkill vs killall)
- Graceful termination with fallback to force kill
- Platform-specific command adaptations
- Unified interface for all process operations

### 2. Network Monitoring (`network-monitor.yaml`)
**Replaces:** `netstat.yaml`, `ss.yaml`

**Functionality:**
- Network connection monitoring
- Listening port analysis
- Network statistics and summaries
- Process-to-network mapping
- Socket state monitoring
- Routing table information

**Key Features:**
- Automatic tool selection (prefers `ss` on Linux, `netstat` elsewhere)
- Fallback mechanisms for tool availability
- Platform-specific optimizations
- Unified command interface

### 3. Disk Usage Analysis (`disk-usage.yaml`)
**Replaces:** `df.yaml`, `du.yaml`, `ncdu.yaml`

**Functionality:**
- Filesystem space usage reporting
- Directory usage breakdown
- Interactive disk usage exploration
- Usage analysis with exclusions
- Export capabilities for analysis data

**Key Features:**
- Progressive detail levels (summary to detailed)
- Interactive mode with ncdu when available
- Configurable exclusion patterns
- Export functionality for reporting

### 4. System Performance Monitor (`system-monitor.yaml`)
**Replaces:** `iostat.yaml`, `iotop.yaml`, `vmstat.yaml`

**Functionality:**
- CPU usage monitoring
- Memory and virtual memory statistics
- I/O performance analysis
- Process-specific I/O monitoring
- Continuous system monitoring

**Key Features:**
- Unified interface for system metrics
- Process-specific monitoring capabilities
- Configurable monitoring intervals
- Fallback options for missing tools

### 5. Security Scanner (`security-scanner.yaml`)
**Replaces:** `grype.yaml`, `syft.yaml`, `trivy.yaml`

**Functionality:**
- Vulnerability scanning for containers and filesystems
- Software Bill of Materials (SBOM) generation
- Secret and credential detection
- Configuration security analysis
- License compliance scanning
- Comprehensive compliance reporting

**Key Features:**
- Multi-tool support with intelligent selection
- Unified scanning interface across security domains
- Multiple output formats (JSON, SARIF, table)
- Comprehensive compliance workflows
- Tool fallback and preference management

## Benefits of Consolidation

1. **Reduced Complexity:** Fewer provider files to maintain
2. **Unified Interface:** Consistent action names across related functionality
3. **Better Fallbacks:** Intelligent tool selection and fallback mechanisms
4. **Platform Optimization:** Platform-specific configurations in single files
5. **Reduced Duplication:** Eliminated redundant functionality across providers

## Backup Location

Original providers have been backed up to `providers/specialized/backup/` for reference.

## Migration Notes

- Existing saidata files using the old provider names will need to be updated
- The new consolidated providers offer more comprehensive functionality
- Action names have been standardized across providers
- Platform-specific behaviors are now handled within single provider files