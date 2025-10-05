# SAI Output Formatting Improvements

## Overview

The SAI CLI tool now features consistent, beautiful output formatting across all commands. This enhancement provides clear visual separation between providers, highlighted commands, and color-coded output for better user experience.

## Key Features

### 1. Provider Separation
- **Clear Headers**: Each provider's output is separated with styled headers
- **Success/Failure Indication**: Headers show provider status with color coding
- **Multiple Provider Support**: Clean separation when multiple providers execute the same action

```
── apt ──
Executing: sudo apt install nginx
[output here]

── brew (failed) ──
Executing: brew install nginx
[error output here]
```

### 2. Command Highlighting
- **Bold Commands**: Commands are displayed in bold for easy identification
- **Provider Context**: Optional provider name shown in brackets for context
- **Sensitive Data Protection**: Automatic redaction of passwords, tokens, and other sensitive information

```
Executing: [apt] sudo apt install nginx
Executing: mysql -u root -p [REDACTED]
```

### 3. Color-Coded Output
- **Standard Output**: White/default color for normal command output
- **Error Output**: Red color for stderr, slightly dimmed for readability
- **Success Messages**: Green color with checkmark (✓)
- **Error Messages**: Red color with X mark (✗)
- **Warning Messages**: Yellow color with warning symbol (⚠)
- **Info Messages**: Blue color with info symbol (ℹ)

### 4. Mode-Responsive Formatting

#### Normal Mode
- Shows provider headers for multiple providers
- Displays commands when verbose or on failure
- Shows all output with appropriate formatting

#### Verbose Mode
- Always shows commands being executed
- Displays execution statistics (time, success rate)
- Shows detailed command lists for multi-step operations
- Includes additional context and debugging information

#### Quiet Mode
- Suppresses headers and command display for successful operations
- Only shows essential output (stdout from successful commands)
- Still shows errors and warnings
- Minimal visual noise

## Implementation

### Core Components

#### OutputFormatter Class
Located in `sai/utils/output_formatter.py`, this class provides:

- **Consistent Styling**: Centralized color and formatting rules
- **Mode Awareness**: Respects quiet/verbose/json output modes
- **Provider Sections**: Methods for formatting complete provider output blocks
- **Message Types**: Standardized success/error/warning/info message formatting
- **Command Sanitization**: Automatic detection and redaction of sensitive information

#### Integration Points
The formatter is integrated into:

- **Single Actions**: `sai install nginx`, `sai status nginx`, etc.
- **Multi-Provider Actions**: `sai info nginx` (shows info from all supporting providers)
- **Batch Operations**: `sai apply actions.yaml`
- **Cache Management**: `sai cache clear`, `sai cache cleanup`

### Usage Examples

#### Single Provider Action
```bash
$ sai install nginx
Executing: sudo apt install nginx
Reading package lists... Done
Building dependency tree... Done
The following NEW packages will be installed:
  nginx
[... installation output ...]
```

#### Multiple Provider Information
```bash
$ sai info nginx

── apt ──
Executing: apt show nginx
Package: nginx
Version: 1.18.0-6ubuntu14.3
[... package info ...]

── snap ──
Executing: snap info nginx
name:      nginx
summary:   Nginx HTTP server
[... snap info ...]

── brew (failed) ──
Executing: brew info nginx
Error: No available formula with name "nginx"
```

#### Verbose Mode
```bash
$ sai install nginx --verbose
ℹ Using provider: apt
ℹ Commands to be executed:
  sudo apt update
  sudo apt install -y nginx
  sudo systemctl enable nginx

── apt ──
Executing: sudo apt install -y nginx
[... output ...]
✓ Installation completed successfully
ℹ Execution time: 2.34s
```

#### Quiet Mode
```bash
$ sai list --quiet
nginx/jammy,now 1.18.0-6ubuntu14.3 all [installed]
docker/jammy,now 20.10.21-0ubuntu1~22.04.3 amd64 [installed]
```

## Benefits

### For Users
- **Clarity**: Easy to distinguish between different providers and their outputs
- **Consistency**: Same visual language across all SAI commands
- **Efficiency**: Quiet mode for scripting, verbose mode for debugging
- **Safety**: Automatic redaction of sensitive information in command display

### For Developers
- **Maintainability**: Centralized formatting logic
- **Extensibility**: Easy to add new message types or formatting rules
- **Testing**: Consistent output makes automated testing more reliable
- **Documentation**: Clear examples for users and contributors

## Migration Notes

### Backward Compatibility
- JSON output mode (`--json`) remains unchanged
- All existing command-line options work as before
- Output content is preserved, only formatting is enhanced

### Configuration
- No additional configuration required
- Respects existing `--quiet`, `--verbose`, and `--json` flags
- Works with all existing SAI commands

## Future Enhancements

### Planned Improvements
- **Progress Indicators**: For long-running operations
- **Interactive Mode**: Better prompts and confirmations
- **Customizable Themes**: User-configurable color schemes
- **Rich Text Support**: Enhanced formatting for supported terminals

### Extensibility
The OutputFormatter class is designed to be easily extended:
- New message types can be added
- Custom formatting rules for specific providers
- Integration with external logging systems
- Support for different output formats (HTML, Markdown, etc.)