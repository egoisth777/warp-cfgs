# Create symlink from warp-themes sub-repo to Warp's theme data directory.
# Usage: set_config.ps1 (no args — paths are relative to script location)

$ThemesSource = Join-Path "$PSScriptRoot" "..\..\warp-themes"
$WarpTarget = "$env:LOCALAPPDATA\warp\Warp\data\themes"

if (-not (Test-Path $ThemesSource)) {
    Write-Host "ERROR: warp-themes not found at $ThemesSource — run init.py first"
    exit 1
}

if (Test-Path $WarpTarget) {
    Write-Host "SKIP: $WarpTarget already exists"
    exit 0
}

# Ensure parent directory exists
$Parent = Split-Path $WarpTarget -Parent
if (-not (Test-Path $Parent)) {
    New-Item -ItemType Directory -Path $Parent -Force | Out-Null
}

New-Item -ItemType SymbolicLink -Path $WarpTarget -Target $ThemesSource | Out-Null
Write-Host "Created symlink: $WarpTarget -> $ThemesSource"
