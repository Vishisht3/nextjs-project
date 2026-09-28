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
$failures = [System.Collections.Generic.List[string]]::new()

function Add-Failure([string]$message) {
    $failures.Add($message)
    Write-Host "FAIL $message" -ForegroundColor Red
}

Write-Host "Dependency/API audit"

$deprecatedPatterns = @(
    "@nextui-org/react",
    "framer-motion",
    "<Textarea\b",
    "<CardBody\b",
    "<AccordionItem\b",
    "isLoading="
)
$frontendFiles = Get-ChildItem $frontend -Recurse -File -Include *.ts,*.tsx,*.css |
    Where-Object { $_.FullName -notmatch "\\(node_modules|\.next)\\" }
foreach ($pattern in $deprecatedPatterns) {
    $matches = $frontendFiles | Select-String -Pattern $pattern -SimpleMatch:$false -CaseSensitive
    if ($matches) {
        Add-Failure "Deprecated frontend pattern '$pattern' found in $($matches[0].Path)"
    }
}

Push-Location $frontend
try {
    $outdatedOutput = npm outdated --include=dev --json 2>$null | Out-String
    if ($LASTEXITCODE -eq 0) {
        Write-Host "OK frontend dependencies are current"
    } elseif ($outdatedOutput.Trim()) {
        Write-Host "INFO frontend dependency updates are available; review before upgrading" -ForegroundColor Yellow
    } else {
        Write-Host "INFO npm outdated could not reach the registry" -ForegroundColor Yellow
    }

    npm run build *> $null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "OK frontend production build"
    } else {
        Add-Failure "frontend production build failed"
    }
} finally {
    Pop-Location
}

Push-Location $backend
try {
    & $pythonCommand -m compileall -q .
    if ($LASTEXITCODE -eq 0) {
        Write-Host "OK backend Python compilation"
    } else {
        Add-Failure "backend Python compilation failed"
    }

    & $pythonCommand -m pip check *> $null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "OK Python dependency consistency"
    } else {
        Add-Failure "Python dependency consistency check failed"
    }

    & $pythonCommand (Join-Path $PSScriptRoot "audit-backend-imports.py")
    if ($LASTEXITCODE -eq 0) {
        Write-Host "OK backend module imports"
    } else {
        Add-Failure "backend module import check failed"
    }

    $outdatedPython = & $pythonCommand -m pip list --outdated --format=json 2>$null | Out-String
    if ($LASTEXITCODE -eq 0 -and $outdatedPython.Trim() -and $outdatedPython.Trim() -ne "[]") {
        Write-Host "INFO Python dependency updates are available; review before upgrading" -ForegroundColor Yellow
    } elseif ($LASTEXITCODE -eq 0) {
        Write-Host "OK Python dependencies are current"
    } else {
        Write-Host "INFO pip outdated check could not reach the registry" -ForegroundColor Yellow
    }
} finally {
    Pop-Location
}

if ($failures.Count -gt 0) {
    Write-Host "Audit failed: $($failures.Count) issue(s)" -ForegroundColor Red
    exit 1
}

Write-Host "Audit passed" -ForegroundColor Green
