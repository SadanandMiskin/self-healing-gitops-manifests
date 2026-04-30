$ErrorActionPreference = "Stop"

function Resolve-Python {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        return $python.Source
    }

    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        return $py.Source
    }

    $bundled = "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
    if (Test-Path $bundled) {
        return $bundled
    }

    throw "Python was not found. Install Python 3.11+ or add it to PATH."
}

$Python = Resolve-Python

Write-Host "Validating Python syntax..."
& $Python -m compileall agents app

Write-Host "Checking required project files..."
$required = @(
    ".github/workflows/ci.yml",
    "app/app.py",
    "app/Dockerfile",
    "manifests/apps/self-healing-api/deployment.yaml",
    "manifests/apps/self-healing-api/service.yaml",
    "manifests/argocd/application.yaml",
    "manifests/monitoring/prometheus-alert-rule.yaml",
    "agents/agent/main.py"
)

foreach ($path in $required) {
    if (!(Test-Path $path)) {
        throw "Missing required file: $path"
    }
}

Write-Host "Project scaffold validation passed."
