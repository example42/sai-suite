# SAI Installation Script for Windows PowerShell
# This script installs the SAI Software Management Suite on Windows

param(
    [switch]$Help,
    [switch]$Uninstall
)

# Configuration
$PythonMinVersion = [Version]"3.8"
$PackageName = "sai"
$VenvDir = "$env:USERPROFILE\.sai\venv"
$ConfigDir = "$env:USERPROFILE\.sai"
$LocalBinDir = "$env:USERPROFILE\.local\bin"

# Functions
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Test-PythonVersion {
    Write-Info "Checking Python version..."
    
    try {
        $pythonVersion = & python --version 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "Python not found"
        }
        
        $versionMatch = $pythonVersion -match "Python (\d+\.\d+\.\d+)"
        if (-not $versionMatch) {
            throw "Could not parse Python version"
        }
        
        $currentVersion = [Version]$matches[1]
        if ($currentVersion -lt $PythonMinVersion) {
            throw "Python $PythonMinVersion or higher is required. Found: $currentVersion"
        }
        
        Write-Success "Python $currentVersion found"
        return $true
    }
    catch {
        Write-Error "Python 3.8 or higher is required. Please install Python from https://python.org"
        return $false
    }
}

function Test-Pip {
    Write-Info "Checking pip..."
    
    try {
        & python -m pip --version | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "pip not available"
        }
        Write-Success "pip is available"
        return $true
    }
    catch {
        Write-Error "pip is not available. Please install pip."
        return $false
    }
}

function New-VirtualEnvironment {
    Write-Info "Creating virtual environment at $VenvDir..."
    
    # Create config directory
    if (-not (Test-Path $ConfigDir)) {
        New-Item -ItemType Directory -Path $ConfigDir -Force | Out-Null
    }
    
    # Remove existing venv if it exists
    if (Test-Path $VenvDir) {
        Write-Warning "Removing existing virtual environment..."
        Remove-Item -Path $VenvDir -Recurse -Force
    }
    
    # Create new virtual environment
    & python -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to create virtual environment"
        return $false
    }
    
    # Activate virtual environment and upgrade pip
    $activateScript = Join-Path $VenvDir "Scripts\Activate.ps1"
    & $activateScript
    & python -m pip install --upgrade pip
    
    Write-Success "Virtual environment created"
    return $true
}

function Install-SAI {
    Write-Info "Installing SAI Software Management Suite..."
    
    # Activate virtual environment
    $activateScript = Join-Path $VenvDir "Scripts\Activate.ps1"
    & $activateScript
    
    # Install SAI with all optional dependencies
    & python -m pip install "$PackageName[all]"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to install SAI"
        return $false
    }
    
    Write-Success "SAI installed successfully"
    return $true
}

function New-CommandWrappers {
    Write-Info "Creating command wrappers..."
    
    # Create local bin directory
    if (-not (Test-Path $LocalBinDir)) {
        New-Item -ItemType Directory -Path $LocalBinDir -Force | Out-Null
    }
    
    # Create batch files for commands
    $saiBat = Join-Path $LocalBinDir "sai.bat"
    $saigenBat = Join-Path $LocalBinDir "saigen.bat"
    
    @"
@echo off
"$VenvDir\Scripts\python.exe" -m sai.cli.main %*
"@ | Out-File -FilePath $saiBat -Encoding ASCII
    
    @"
@echo off
"$VenvDir\Scripts\python.exe" -m saigen.cli.main %*
"@ | Out-File -FilePath $saigenBat -Encoding ASCII
    
    Write-Success "Command wrappers created in $LocalBinDir"
    return $true
}

function New-DefaultConfig {
    Write-Info "Creating default configuration..."
    
    $configFile = Join-Path $ConfigDir "config.yaml"
    
    if (-not (Test-Path $configFile)) {
        $configContent = @'
config_version: "0.1.0"
log_level: info

# Saidata search paths (repository cache has highest priority)
saidata_paths:
  - "~/.sai/cache/repositories/saidata-main"
  - "~/.sai/saidata"
  - "/usr/local/share/sai/saidata"

provider_paths:
  - "providers"
  - "~/.sai/providers"
  - "/usr/local/share/sai/providers"

# Provider priorities (lower number = higher priority)
provider_priorities:
  winget: 1
  choco: 2
  scoop: 3

# Execution settings
max_concurrent_actions: 3
action_timeout: 300
require_confirmation: true
dry_run_default: false
'@
        $configContent | Out-File -FilePath $configFile -Encoding UTF8
        Write-Success "Default configuration created at $configFile"
    }
    else {
        Write-Info "Configuration file already exists at $configFile"
    }
}

function Show-Usage {
    Write-Success "SAI Software Management Suite installed successfully!"
    Write-Host ""
    Write-Host "To use SAI commands, make sure $LocalBinDir is in your PATH:"
    Write-Host "  `$env:PATH = `"$LocalBinDir;`$env:PATH`""
    Write-Host ""
    Write-Host "To make this permanent, add $LocalBinDir to your system PATH environment variable."
    Write-Host ""
    Write-Host "Available commands:"
    Write-Host "  sai --help      # Show SAI CLI help"
    Write-Host "  saigen --help   # Show SAIGEN CLI help"
    Write-Host ""
    Write-Host "Example usage:"
    Write-Host "  sai install nginx"
    Write-Host "  sai providers list"
    Write-Host "  saigen generate nginx"
    Write-Host ""
    Write-Host "Configuration file: $configFile"
    Write-Host "Virtual environment: $VenvDir"
}

function Uninstall-SAI {
    Write-Info "Uninstalling SAI..."
    
    if (Test-Path $VenvDir) {
        Remove-Item -Path $VenvDir -Recurse -Force
    }
    
    $saiBat = Join-Path $LocalBinDir "sai.bat"
    $saigenBat = Join-Path $LocalBinDir "saigen.bat"
    
    if (Test-Path $saiBat) {
        Remove-Item -Path $saiBat -Force
    }
    
    if (Test-Path $saigenBat) {
        Remove-Item -Path $saigenBat -Force
    }
    
    Write-Success "SAI uninstalled successfully"
}

# Main installation process
function Install-Main {
    Write-Host "SAI Software Management Suite Installer" -ForegroundColor Cyan
    Write-Host "=======================================" -ForegroundColor Cyan
    Write-Host ""
    
    if (-not (Test-PythonVersion)) { exit 1 }
    if (-not (Test-Pip)) { exit 1 }
    if (-not (New-VirtualEnvironment)) { exit 1 }
    if (-not (Install-SAI)) { exit 1 }
    if (-not (New-CommandWrappers)) { exit 1 }
    New-DefaultConfig
    Show-Usage
}

# Handle command line arguments
if ($Help) {
    Write-Host "SAI Installation Script for Windows"
    Write-Host ""
    Write-Host "Usage: .\install.ps1 [OPTIONS]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Help          Show this help message"
    Write-Host "  -Uninstall     Uninstall SAI"
    Write-Host ""
    exit 0
}

if ($Uninstall) {
    Uninstall-SAI
    exit 0
}

# Run main installation
Install-Main