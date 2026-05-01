import subprocess
from pathlib import Path

from agent.config import AgentConfig
from agent.detector import _logs, _select_relevant_pod


def config(tmp_path: Path) -> AgentConfig:
    return AgentConfig(
        app_name="self-healing-api",
        namespace="self-healing",
        container_name="api",
        required_env_name="REQUIRED_GREETING",
        required_env_value="hello-from-gitops",
        prometheus_url="http://localhost:9090",
        llm_provider="mock",
        llm_model="mistral-small-latest",
        poll_interval_seconds=30,
        state_file=Path(".agent-state.yaml"),
        manifests_repo_path=tmp_path,
        deployment_path=Path("deployment.yaml"),
        github_repo="example/manifests",
        base_branch="main",
        branch_prefix="self-heal",
    )


def test_select_relevant_pod_prefers_crashloop(tmp_path: Path) -> None:
    pods = [
        {
            "metadata": {"name": "healthy"},
            "status": {
                "containerStatuses": [
                    {"name": "api", "restartCount": 5, "state": {"running": {}}}
                ]
            },
        },
        {
            "metadata": {"name": "crashing"},
            "status": {
                "containerStatuses": [
                    {
                        "name": "api",
                        "restartCount": 1,
                        "state": {"waiting": {"reason": "CrashLoopBackOff"}},
                    }
                ]
            },
        },
    ]

    assert _select_relevant_pod(pods, config(tmp_path))["metadata"]["name"] == "crashing"


def test_logs_include_previous_before_current(monkeypatch, tmp_path: Path) -> None:
    calls = []

    def fake_run(args, capture_output, text):
        calls.append(args)
        if "--previous" in args:
            return subprocess.CompletedProcess(
                args,
                0,
                stdout="RuntimeError: REQUIRED_GREETING environment variable is missing\n",
                stderr="",
            )
        return subprocess.CompletedProcess(args, 0, stdout="Application startup complete\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    logs = _logs(config(tmp_path), "self-healing-api-123")

    assert "=== previous container logs ===" in logs
    assert "REQUIRED_GREETING environment variable is missing" in logs
    assert logs.index("previous container logs") < logs.index("current container logs")
    assert len(calls) == 2
