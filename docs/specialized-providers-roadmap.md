# Specialized CLI Tool Providers for Universal Software Actions

This document outlines command-line tools that can perform actions on ANY software, following the pattern of existing specialized providers like `gdb`, `strace`, `trivy`, etc.

## Current Specialized Providers (10)
- **gdb** - GNU Debugger (debug any binary)
- **perf** - Performance profiling (profile any process)  
- **strace** - System call tracing (trace any process)
- **grype** - Vulnerability scanning (scan any software)
- **trivy** - Security scanning (scan any container/filesystem)
- **syft** - SBOM generation (generate SBOM for any software)
- **lsof** - List open files (inspect any process)
- **netstat** - Network statistics (monitor any network activity)
- **lynis** - Security auditing (audit any system)
- **restic** - Backup (backup any software data)

## Proposed New Specialized Providers

### Process & System Analysis

| Provider | Type | Description | Platforms | Key Actions |
|----------|------|-------------|-----------|-------------|
| **ps** | process | Process status and management | linux, macos, windows | list, tree, filter, sort, kill, signal |
| **top** | monitor | Real-time process monitoring | linux, macos, windows | monitor, sort, filter, kill, batch |
| **htop** | monitor | Interactive process viewer | linux, macos | monitor, kill, nice, search, tree, filter |
| **pgrep** | process | Process grep and management | linux, macos | find, count, kill, signal, parent, session |
| **pkill** | process | Kill processes by name/criteria | linux, macos | kill, signal, term, user, group, parent |
| **killall** | process | Kill processes by name | linux, macos, windows | kill, signal, interactive, verbose, wait |

### Memory & Resource Analysis

| Provider | Type | Description | Platforms | Key Actions |
|----------|------|-------------|-----------|-------------|
| **valgrind** | memory | Memory debugging and profiling | linux, macos | memcheck, callgrind, helgrind, massif, cachegrind |
| **pmap** | memory | Process memory mapping | linux, macos | map, extended, device, quiet, range |
| **vmstat** | system | Virtual memory statistics | linux, macos | report, interval, count, disk, partition |
| **iostat** | io | I/O statistics | linux, macos | report, interval, cpu, device, extended |
| **iotop** | io | I/O monitoring by process | linux | monitor, accumulated, only, processes, quiet |
| **free** | memory | Memory usage display | linux | total, human, seconds, wide, available |

### Network Analysis & Monitoring

| Provider | Type | Description | Platforms | Key Actions |
|----------|------|-------------|-----------|-------------|
| **ss** | network | Socket statistics | linux | tcp, udp, listening, processes, summary, numeric |
| **tcpdump** | network | Network packet analyzer | linux, macos | capture, filter, interface, count, verbose, write |
| **wireshark** | network | Network protocol analyzer | linux, macos, windows | capture, analyze, filter, decode, export |
| **ngrep** | network | Network grep | linux, macos | search, interface, pattern, hex, quiet |
| **iftop** | network | Network bandwidth by connection | linux, macos | monitor, interface, port, host, filter |
| **nethogs** | network | Network usage by process | linux | monitor, device, delay, trace, version |
| **nmap** | network | Network discovery and security | linux, macos, windows | scan, discover, script, timing, output |

### File & Filesystem Analysis

| Provider | Type | Description | Platforms | Key Actions |
|----------|------|-------------|-----------|-------------|
| **find** | filesystem | Find files and directories | linux, macos, windows | search, exec, delete, type, size, time |
| **locate** | filesystem | Find files by name | linux, macos | search, database, update, statistics, regex |
| **du** | filesystem | Disk usage analyzer | linux, macos, windows | size, summarize, human, depth, exclude |
| **df** | filesystem | Filesystem disk space usage | linux, macos, windows | space, human, type, inodes, total |
| **ncdu** | filesystem | Interactive disk usage analyzer | linux, macos, windows | analyze, interactive, exclude, export, import |
| **tree** | filesystem | Directory tree display | linux, macos, windows | tree, depth, size, permissions, pattern |
| **stat** | filesystem | File/filesystem status | linux, macos | info, format, filesystem, dereference, terse |

### Text Processing & Analysis

| Provider | Type | Description | Platforms | Key Actions |
|----------|------|-------------|-----------|-------------|
| **grep** | text | Text pattern searching | linux, macos, windows | search, recursive, ignore_case, count, files |
| **awk** | text | Text processing and analysis | linux, macos, windows | process, field, pattern, script, variable |
| **sed** | text | Stream editor | linux, macos, windows | substitute, delete, insert, script, in_place |
| **sort** | text | Sort lines of text | linux, macos, windows | sort, numeric, reverse, unique, field |
| **uniq** | text | Report or omit repeated lines | linux, macos, windows | unique, count, duplicate, ignore_case, skip |
| **wc** | text | Word, line, character, byte count | linux, macos, windows | lines, words, chars, bytes, max_line |

### Security & Forensics

| Provider | Type | Description | Platforms | Key Actions |
|----------|------|-------------|-----------|-------------|
| **checksec** | security | Binary security feature checker | linux, macos | check, file, process, kernel, fortify |
| **strings** | forensics | Extract printable strings | linux, macos, windows | extract, encoding, length, offset, radix |
| **hexdump** | forensics | Hex and ASCII dump | linux, macos | dump, canonical, decimal, octal, skip |
| **objdump** | forensics | Object file analyzer | linux, macos | disassemble, headers, symbols, sections, reloc |
| **nm** | forensics | Symbol table analyzer | linux, macos | symbols, undefined, external, debug, demangle |
| **readelf** | forensics | ELF file analyzer | linux | headers, sections, symbols, relocs, dynamic |
| **file** | forensics | File type identification | linux, macos, windows | type, mime, brief, dereference, compress |

### Performance & Benchmarking

| Provider | Type | Description | Platforms | Key Actions |
|----------|------|-------------|-----------|-------------|
| **time** | benchmark | Command execution timing | linux, macos, windows | time, verbose, output, append, format |
| **timeout** | control | Run command with time limit | linux, macos, windows | timeout, kill_after, signal, preserve |
| **nice** | priority | Run with modified priority | linux, macos, windows | priority, adjustment, increment |
| **nohup** | control | Run immune to hangups | linux, macos, windows | detach, output, append |
| **watch** | monitor | Execute program periodically | linux, macos | interval, differences, precise, exec |
| **uptime** | system | System uptime and load | linux, macos | uptime, pretty, since, version |

### Log Analysis & Monitoring

| Provider | Type | Description | Platforms | Key Actions |
|----------|------|-------------|-----------|-------------|
| **tail** | log | Output last part of files | linux, macos, windows | follow, lines, bytes, quiet, verbose |
| **head** | log | Output first part of files | linux, macos, windows | lines, bytes, quiet, verbose, zero |
| **less** | log | File pager | linux, macos, windows | view, search, follow, quit, help |
| **journalctl** | log | systemd journal viewer | linux | unit, follow, since, until, priority |
| **dmesg** | log | Kernel ring buffer | linux | kernel, facility, level, follow, human |
| **logrotate** | log | Log file rotation | linux, macos | rotate, force, debug, state, verbose |

### Archive & Compression

| Provider | Type | Description | Platforms | Key Actions |
|----------|------|-------------|-----------|-------------|
| **tar** | archive | Archive files | linux, macos, windows | create, extract, list, append, update |
| **zip** | compress | Create ZIP archives | linux, macos, windows | create, extract, list, test, update |
| **unzip** | compress | Extract ZIP archives | linux, macos, windows | extract, list, test, overwrite, quiet |
| **gzip** | compress | Compress/decompress files | linux, macos, windows | compress, decompress, test, list, force |
| **xz** | compress | High-ratio compression | linux, macos, windows | compress, decompress, test, list, keep |

### Environment & Configuration

| Provider | Type | Description | Platforms | Key Actions |
|----------|------|-------------|-----------|-------------|
| **env** | environment | Environment variable management | linux, macos, windows | set, unset, list, ignore, null |
| **which** | path | Locate command | linux, macos, windows | locate, all, skip_dot, skip_tilde, show_dot |
| **whereis** | path | Locate binary, source, manual | linux, macos | binary, manual, source, unusual, list |
| **type** | shell | Command type identification | linux, macos, windows | type, all, path, force_path |
| **alias** | shell | Command aliases | linux, macos, windows | list, create, remove |
| **history** | shell | Command history | linux, macos, windows | list, clear, delete, append, read |

## Usage Examples

### Universal Process Analysis
```bash
# Any software process analysis
sai analyze redis --provider ps --action list
sai monitor redis --provider htop --action monitor  
sai trace redis --provider strace --action trace
sai profile redis --provider perf --action record
sai debug redis --provider gdb --action attach
```

### Universal Security Analysis  
```bash
# Any software security analysis
sai scan redis --provider grype --action scan
sai audit redis --provider lynis --action audit
sai check redis --provider checksec --action check
sai analyze redis --provider strings --action extract
```

### Universal Network Analysis
```bash
# Any software network analysis
sai network redis --provider ss --action tcp
sai capture redis --provider tcpdump --action capture
sai monitor redis --provider iftop --action monitor
sai scan redis --provider nmap --action scan
```

### Universal File Analysis
```bash
# Any software file analysis
sai files redis --provider lsof --action files
sai search redis --provider find --action search
sai analyze redis --provider du --action size
sai tree redis --provider tree --action tree
```

## Key Benefits

### 1. **Universal Applicability** ✅
- Works with ANY software, not just specific applications
- Same interface for all analysis tasks
- Consistent variable resolution across tools

### 2. **Operational Coverage** ✅
- Complete software lifecycle analysis
- From installation to debugging to security
- Comprehensive troubleshooting capabilities

### 3. **Platform Native** ✅
- Uses standard Unix/Linux/Windows tools
- Leverages existing system utilities
- No additional software installation required

### 4. **Integration Ready** ✅
- Works with existing saidata files
- Compatible with current provider ecosystem
- Enables cross-tool workflows

## Implementation Priority

### Tier 1 (Essential System Tools)
1. **ps** - Process management (universal)
2. **find** - File searching (universal) 
3. **grep** - Text searching (universal)
4. **tail** - Log monitoring (universal)
5. **ss** - Network analysis (modern netstat)

### Tier 2 (Advanced Analysis)
1. **valgrind** - Memory debugging
2. **tcpdump** - Network capture
3. **tar** - Archive management
4. **time** - Performance timing
5. **watch** - Periodic monitoring

### Tier 3 (Specialized Tools)
1. **objdump** - Binary analysis
2. **checksec** - Security checking
3. **ncdu** - Interactive disk usage
4. **ngrep** - Network grep
5. **hexdump** - Binary inspection

These providers focus on generic CLI tools that can analyze, monitor, debug, and manage ANY software, making them truly universal and fitting the specialized provider pattern.