# Self-Healing Agent

The agent observes Prometheus alerts, reads Kubernetes logs, asks an LLM or mock LLM for diagnosis, checks a narrow safety policy, modifies the manifests Git repository, and opens a pull request.

It does not modify the cluster.

## Modules

- `observer.py`: reads Prometheus alerts or emits a mock alert for demos
- `detector.py`: maps alerts to the affected Kubernetes workload and gathers logs
- `diagnoser.py`: uses OpenAI or mock LLM to diagnose the logs
- `decision.py`: allows only the missing `REQUIRED_GREETING` env-var fix
- `fixer.py`: edits `deployment.yaml` in the manifests repository
- `executor.py`: creates a Git branch, commit, push, and GitHub PR
- `main.py`: orchestrates one healing cycle

## Quick Run

```powershell
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
Copy-Item config.example.yaml config.local.yaml
python -m agent.main --config config.local.yaml --mock-alert --dry-run
```

Remove `--dry-run` when you want the agent to create a branch, commit, push, and PR.
