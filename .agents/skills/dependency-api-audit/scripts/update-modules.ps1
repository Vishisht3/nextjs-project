param(
    [switch]$AuditOnly
)

$ErrorActionPreference = "Stop"
$skillRoot = Split-Path -Parent $PSScriptRoot
$root = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $skillRoot))
$frontend = Join-Path $root "frontend"
$backend = Join-Path $root "backend"
$pythonCommand = "python"
$venvPython = Join-Path $root ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $pythonCommand = $venvPython
}

if (-not $AuditOnly) {
    Push-Location $frontend
    try {
        npm update
        if ($LASTEXITCODE -ne 0) {
            throw "npm update failed"
        }
    } finally {
        Pop-Location
    }

    Push-Location $backend
    try {
        & $pythonCommand -m pip install --upgrade -r requirements.txt
        if ($LASTEXITCODE -ne 0) {
            throw "Python dependency update failed"
        }
    } finally {
        Pop-Location
    }

    $frontendFiles = Get-ChildItem $frontend -Recurse -File -Include *.ts,*.tsx,*.css |
        Where-Object { $_.FullName -notmatch "\\(node_modules|\.next)\\" }
    foreach ($file in $frontendFiles) {
        $content = Get-Content $file.FullName -Raw
        $updated = $content.Replace("@nextui-org/react", "@heroui/react")
        if ($updated -cne $content) {
            Set-Content -Path $file.FullName -Value $updated -Encoding utf8
            Write-Host "Updated deprecated HeroUI import: $($file.FullName)"
        }
    }
}

& (Join-Path $PSScriptRoot "audit-project.ps1")
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
