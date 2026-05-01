from pathlib import Path

from agent.config import AgentConfig
from agent.detector import DetectedIssue
from agent.diagnoser import diagnose
from agent.observer import Alert


def test_mock_diagnosis_uses_gitops_manifest_evidence(tmp_path: Path) -> None:
    deployment = tmp_path / "deployment.yaml"
    deployment.write_text(
        """
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
        - name: api
          env:
            - name: LOG_LEVEL
              value: info
""".lstrip(),
        encoding="utf-8",
    )
    config = AgentConfig(
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
    issue = DetectedIssue(
        alert=Alert(
            name="SelfHealingApiCrashLoopBackOff",
            app="self-healing-api",
            namespace="self-healing",
            severity="warning",
            summary="crash",
            state="firing",
        ),
        pod_name="self-healing-api-123",
        phase="Running",
        waiting_reason="",
        restart_count=3,
        logs="GET /healthz 200 OK",
    )

    diagnosis = diagnose(config, issue, provider="mock")

    assert diagnosis.issue_type == "missing_env_var"
    assert diagnosis.confidence == 0.95
