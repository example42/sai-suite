# SAI Stats Command

The `sai stats` command provides comprehensive statistics about providers and actions in the SAI ecosystem.

## Usage

```bash
sai stats [OPTIONS]
```

## Options

- `--detailed, -d`: Show detailed statistics with action coverage breakdown
- `--by-type, -t`: Group statistics by provider type
- `--by-platform, -p`: Group statistics by platform support
- `--actions-only, -a`: Show only action statistics (no provider info)

## Examples

### Basic Statistics
```bash
sai stats
```
Shows overview with total providers, actions, and coverage percentages.

### Detailed Action Coverage
```bash
sai stats --detailed
```
Shows which providers implement each action, grouped by provider type.

### Provider Type Breakdown
```bash
sai stats --by-type
```
Shows provider distribution by type (package_manager, network, security, etc.).

### Platform Support Analysis
```bash
sai stats --by-platform
```
Shows how many providers support each platform (linux, macos, windows, etc.).

### Actions Only
```bash
sai stats --actions-only
```
Shows only action statistics without provider type or platform information.

## Sample Output

```
🔧 SAI Provider & Action Statistics
========================================

📊 Overview:
  Total Providers: 50
  Unique Actions: 67
  Total Action Implementations: 490

⚡ Action Statistics:
Action          Providers  Coverage  
-----------------------------------
list            41          82.0%
info            40          80.0%
search          38          76.0%
status          37          74.0%
upgrade         36          72.0%
install         33          66.0%
uninstall       33          66.0%
start           33          66.0%
stop            33          66.0%
restart         32          64.0%
logs            28          56.0%
enable          19          38.0%
disable         19          38.0%

🏆 Most Common Actions:
  list          41 providers ( 82.0%)
  info          40 providers ( 80.0%)
  search        38 providers ( 76.0%)
  status        37 providers ( 74.0%)
  upgrade       36 providers ( 72.0%)

🔍 Least Common Actions:
  repository     1 providers (  2.0%)
  config         1 providers (  2.0%)
  secret         1 providers (  2.0%)
  license        1 providers (  2.0%)
  sbom           1 providers (  2.0%)

🏷️  Provider Types:
  package_manager  32 ( 64.0%)
  network           8 ( 16.0%)
  security          2 (  4.0%)
  container         1 (  2.0%)
  debug             1 (  2.0%)
  troubleshoot      1 (  2.0%)
  audit             1 (  2.0%)
  profile           1 (  2.0%)
  backup            1 (  2.0%)
  trace             1 (  2.0%)
  sbom              1 (  2.0%)
```

## Key Insights

### Action Coverage Analysis
- **Universal Actions**: `list`, `info`, `search`, `status` are supported by 70%+ of providers
- **Core Management**: `install`, `uninstall`, `start`, `stop` are supported by 60%+ of providers
- **Service Management**: `enable`, `disable` are supported by package managers (38% coverage)
- **Specialized Actions**: Debug, security, and monitoring actions have lower coverage (2-6%)

### Provider Distribution
- **Package Managers**: Dominate the ecosystem (64% of providers)
- **Network Tools**: Second largest category (16% of providers)
- **Specialized Tools**: Security, debugging, monitoring tools fill specific niches

### Platform Support
- **Linux**: Best supported platform (66% of providers)
- **macOS**: Good cross-platform support (56% of providers)  
- **Windows**: Growing support (42% of providers)
- **Specialized Distros**: Targeted support for specific Linux distributions

## Use Cases

### Development Planning
- Identify gaps in action coverage
- Plan new provider development priorities
- Understand ecosystem maturity

### Operations Analysis
- Assess platform compatibility
- Evaluate action availability for workflows
- Compare provider capabilities

### Documentation
- Generate provider capability matrices
- Create action reference guides
- Track ecosystem growth over time

## Implementation Details

The stats command:
1. Loads all available providers using `ProviderLoader`
2. Analyzes provider metadata and capabilities
3. Calculates coverage percentages and distributions
4. Formats output with emojis and tables for readability
5. Handles validation errors gracefully (continues with valid providers)

The command provides both high-level overview and detailed breakdowns to support different analysis needs.