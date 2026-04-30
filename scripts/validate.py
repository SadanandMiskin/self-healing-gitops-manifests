from __future__ import annotations

import compileall
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    print("Validating Python syntax...")
    ok = compileall.compile_dir(ROOT / "agents" / "agent", quiet=1)
    ok = compileall.compile_dir(ROOT / "agents" / "tests", quiet=1) and ok
    ok = compileall.compile_dir(ROOT / "app", quiet=1) and ok
    ok = compileall.compile_file(ROOT / "run_agent.py", quiet=1) and ok

    print("Checking required project files...")
    required = [
        ".github/workflows/ci.yml",
        "app/app.py",
        "app/Dockerfile",
        "manifests/apps/self-healing-api/deployment.yaml",
        "manifests/apps/self-healing-api/service.yaml",
        "manifests/argocd/application.yaml",
        "manifests/monitoring/prometheus-alert-rule.yaml",
        "agents/agent/main.py",
        "run_agent.py",
    ]

    missing = [path for path in required if not (ROOT / path).exists()]
    if missing:
        for path in missing:
            print(f"Missing required file: {path}")
        return 1

    if not ok:
        return 1

    print("Project scaffold validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
