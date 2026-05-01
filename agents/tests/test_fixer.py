from pathlib import Path

import yaml

from agent.config import AgentConfig
from agent.fixer import add_required_env


def test_add_required_env(tmp_path: Path) -> None:
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

    assert add_required_env(config) is True
    document = yaml.safe_load(deployment.read_text(encoding="utf-8"))
    env = document["spec"]["template"]["spec"]["containers"][0]["env"]
    assert {"name": "REQUIRED_GREETING", "value": "hello-from-gitops"} in env


def test_add_required_env_is_idempotent(tmp_path: Path) -> None:
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
            - name: REQUIRED_GREETING
              value: hello-from-gitops
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

    assert add_required_env(config) is False
