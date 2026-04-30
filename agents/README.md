# Self-Healing Agent

The agent continuously observes Prometheus alerts, reads Kubernetes logs, asks Gemini or the mock LLM for diagnosis, checks a narrow safety policy, modifies the manifests Git repository, and opens a pull request.

It does not modify the cluster.

## Modules

- `observer.py`: reads Prometheus alerts or emits a mock alert for demos
- `detector.py`: maps alerts to the affected Kubernetes workload and gathers logs
- `diagnoser.py`: uses Gemini or mock LLM to diagnose the logs
- `decision.py`: allows only the missing `REQUIRED_GREETING` env-var fix
- `fixer.py`: edits `deployment.yaml` in the manifests repository
- `executor.py`: creates a Git branch, commit, push, and GitHub PR
- `state.py`: remembers handled alert instances to avoid duplicate PRs
- `main.py`: runs the continuous healing loop

## Quick Run

```powershell
$env:GEMINI_API_KEY="<YOUR_GEMINI_API_KEY>"
python ..\run_agent.py --github-repo OWNER/self-healing-gitops-manifests --manifests-repo-path C:\absolute\path\to\manifests-repo
```

For one-cycle debugging without Gemini:

```powershell
python ..\run_agent.py --mock-alert --llm mock --once --dry-run
```
