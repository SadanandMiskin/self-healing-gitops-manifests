from pathlib import Path

from agent.config import AgentConfig
from agent.decision import decide
from agent.detector import DetectedIssue
from agent.diagnoser import Diagnosis
from agent.observer import Alert


def config(tmp_path: Path) -> AgentConfig:
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


def issue(restart_count: int, logs: str = "") -> DetectedIssue:
    return DetectedIssue(
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
        restart_count=restart_count,
        logs=logs,
    )


def test_decision_approves_from_missing_manifest_and_restarts(tmp_path: Path) -> None:
    decision = decide(
        config(tmp_path),
        issue(restart_count=3),
        Diagnosis(
            issue_type="unknown",
            confidence=0.3,
            explanation="No old logs available.",
            recommended_fix="No automated fix.",
        ),
    )

    assert decision.approved is True
    assert "safe GitOps fallback" in decision.reason


def test_decision_blocks_when_manifest_already_has_env(tmp_path: Path) -> None:
    cfg = config(tmp_path)
    cfg.deployment_file.write_text(
        """
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
        - name: api
          env:
            - name: REQUIRED_GREETING
              value: hello-from-gitops
""".lstrip(),
        encoding="utf-8",
    )

    decision = decide(
        cfg,
        issue(restart_count=3, logs="REQUIRED_GREETING environment variable is missing"),
        Diagnosis(
            issue_type="missing_env_var",
            confidence=0.99,
            explanation="missing",
            recommended_fix="add env",
        ),
    )

    assert decision.approved is False
    assert "already contains" in decision.reason
