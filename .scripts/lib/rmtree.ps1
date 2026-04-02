# Recursively delete a directory.
# Usage: rmtree.ps1 -Path <absolute-dir-path>
param(
    [Parameter(Mandatory)][string]$Path
)

if (-not (Test-Path $Path)) {
    exit 0
}

Remove-Item -Path $Path -Recurse -Force
