param(
    [string]$Config = "..\agents\config.local.yaml",
    [switch]$DryRun
)

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

Push-Location "$PSScriptRoot\..\agents"
try {
    if (!(Test-Path ".venv")) {
        & $Python -m venv .venv
    }

    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt

    $argsList = @("-m", "agent.main", "--config", $Config, "--mock-alert")
    if ($DryRun) {
        $argsList += "--dry-run"
    }

    python @argsList
}
finally {
    Pop-Location
}
