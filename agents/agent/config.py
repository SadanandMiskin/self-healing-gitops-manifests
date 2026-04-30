from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class AgentConfig:
    app_name: str
    namespace: str
    container_name: str
    required_env_name: str
    required_env_value: str
    prometheus_url: str
    llm_provider: str
    gemini_model: str
    poll_interval_seconds: int
    state_file: Path
    manifests_repo_path: Path
    deployment_path: Path
    github_repo: str
    base_branch: str
    branch_prefix: str

    @property
    def deployment_file(self) -> Path:
        return self.manifests_repo_path / self.deployment_path


def load_config(path: str | Path) -> AgentConfig:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)

    return AgentConfig(
        app_name=raw["app_name"],
        namespace=raw["namespace"],
        container_name=raw["container_name"],
        required_env_name=raw["required_env_name"],
        required_env_value=raw["required_env_value"],
        prometheus_url=raw.get("prometheus_url", "http://localhost:9090"),
        llm_provider=raw.get("llm_provider", "gemini"),
        gemini_model=raw.get("gemini_model", "gemini-2.5-flash-lite"),
        poll_interval_seconds=int(raw.get("poll_interval_seconds", 30)),
        state_file=Path(raw.get("state_file", ".agent-state.yaml")),
        manifests_repo_path=Path(raw["manifests_repo_path"]),
        deployment_path=Path(raw["deployment_path"]),
        github_repo=raw["github_repo"],
        base_branch=raw.get("base_branch", "main"),
        branch_prefix=raw.get("branch_prefix", "self-heal"),
    )
