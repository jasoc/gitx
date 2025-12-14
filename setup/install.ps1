# gitx Windows installer (PowerShell)
#
# This script aims to do the same high‑level work as install.sh on Linux/macOS:
#   - Check that Python 3 is available
#   - Ensure pipx is installed
#   - Install or upgrade gitx-cli via pipx
#   - Make sure the user PATH contains the pipx binaries directory

param(
    [ValidateSet('install', 'ensure-pipx', 'validate-python', 'help')]
    [string] $Command = 'install'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Info($Message) {
    Write-Host "[gitx] $Message"
}

function Write-ErrorAndExit($Message) {
    Write-Error "[gitx] $Message"
    exit 1
}

# -----------------------------------------------------------------------------
# Python validation
# -----------------------------------------------------------------------------

function Test-Python {
    Write-Info 'Checking for python3...'

    $python = Get-Command python3 -ErrorAction SilentlyContinue
    if (-not $python) {
        # Fallback to `python` if python3 is not found
        $python = Get-Command python -ErrorAction SilentlyContinue
    }

    if (-not $python) {
        Write-ErrorAndExit 'python3 (or python) is required but was not found in PATH.'
    }

    return $python.Source
}

# -----------------------------------------------------------------------------
# pipx installation & validation
# -----------------------------------------------------------------------------

function Install-PipxWithPip {
    param(
        [Parameter(Mandatory = $true)]
        [string] $PythonExe
    )

    Write-Info 'Installing pipx via pip...'

    & $PythonExe -m pip install --user --upgrade pip pipx
    if ($LASTEXITCODE -ne 0) {
        Write-ErrorAndExit 'Failed to install pipx with pip.'
    }
}

function Ensure-PipxPath {
    Write-Info 'Ensuring pipx directory is on PATH...'

    # Typical pipx binary locations on Windows
    $candidateDirs = @(
        "$env:USERPROFILE\.local\bin",
        "$env:APPDATA\Python\Scripts",
        "$env:LOCALAPPDATA\Programs\Python\PythonScripts"
    )

    $currentUserPath = [Environment]::GetEnvironmentVariable('PATH', 'User')
    if (-not $currentUserPath) {
        $currentUserPath = ''
    }

    $newPath = $currentUserPath
    foreach ($dir in $candidateDirs) {
        if (Test-Path $dir -PathType Container) {
            if ($newPath -notlike "*${dir}*") {
                if ([string]::IsNullOrWhiteSpace($newPath)) {
                    $newPath = $dir
                } else {
                    $newPath = "$newPath;$dir"
                }
            }
        }
    }

    if ($newPath -ne $currentUserPath) {
        [Environment]::SetEnvironmentVariable('PATH', $newPath, 'User')
        Write-Info 'Updated User PATH to include pipx binaries directory. You may need to restart your shell.'
    } else {
        Write-Info 'User PATH already includes a pipx binaries directory.'
    }
}

function Ensure-Pipx {
    $pipxCmd = Get-Command pipx -ErrorAction SilentlyContinue
    if ($pipxCmd) {
        Write-Info 'pipx is already installed.'
        return $true
    }

    $pythonExe = Test-Python

    Write-Info 'pipx was not found, attempting installation with pip...'
    Install-PipxWithPip -PythonExe $pythonExe

    # Refresh PATH for the current session
    $env:PATH = [Environment]::GetEnvironmentVariable('PATH', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('PATH', 'User')

    $pipxCmd = Get-Command pipx -ErrorAction SilentlyContinue
    if (-not $pipxCmd) {
        Write-ErrorAndExit 'pipx installation appears to have failed. Please install pipx manually and re-run this script.'
    }

    Ensure-PipxPath
    return $true
}

# -----------------------------------------------------------------------------
# Main installation
# -----------------------------------------------------------------------------

function Install-Gitx {
    Write-Info 'Starting gitx installation...'

    $null = Test-Python

    if (-not (Ensure-Pipx)) {
        Write-ErrorAndExit 'pipx is required for installation.'
    }

    Write-Info 'Installing (or upgrading) gitx-cli via pipx...'
    pipx install gitx-cli 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Info 'gitx-cli may already be installed, trying upgrade...'
        pipx upgrade gitx-cli
        if ($LASTEXITCODE -ne 0) {
            Write-ErrorAndExit 'Failed to install or upgrade gitx-cli using pipx.'
        }
    }

    Ensure-PipxPath

    Write-Host ''
    Write-Host '✔ gitx installed successfully via pipx.'
    Write-Host '→ You may need to restart your terminal session so that the updated PATH is picked up.'
    Write-Host ''
    Write-Host 'Try:'
    Write-Host '  gitx --help'
}

# -----------------------------------------------------------------------------
# Help
# -----------------------------------------------------------------------------

function Show-Help {
    Write-Host 'Usage: install.ps1 [-Command <install|ensure-pipx|validate-python|help>]' -ForegroundColor Cyan
    Write-Host ''
    Write-Host 'Commands:'
    Write-Host '  install        Install gitx (default)'
    Write-Host '  ensure-pipx    Ensure pipx is installed and on PATH'
    Write-Host '  validate-python Check that python3/python is available'
    Write-Host '  help           Show this help message'
}

switch ($Command) {
    'install' {
        Install-Gitx
    }
    'ensure-pipx' {
        Ensure-Pipx | Out-Null
    }
    'validate-python' {
        Test-Python | Out-Null
        Write-Info 'Python is available.'
    }
    'help' {
        Show-Help
    }
    default {
        Install-Gitx
    }
}