from __future__ import annotations

from pathlib import Path

import yaml

from .config import AgentConfig
from .detector import DetectedIssue


class AgentState:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._data = self._load()

    def already_handled(self, issue: DetectedIssue) -> bool:
        return self._key(issue) in self._data.get("handled", [])

    def mark_handled(self, issue: DetectedIssue, pr_url: str) -> None:
        handled = self._data.setdefault("handled", [])
        key = self._key(issue)
        if key not in handled:
            handled.append(key)
        prs = self._data.setdefault("pull_requests", {})
        prs[key] = pr_url
        self._save()

    def _load(self) -> dict:
        if not self.path.exists():
            return {"handled": [], "pull_requests": {}}
        with self.path.open("r", encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {"handled": [], "pull_requests": {}}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as fh:
            yaml.safe_dump(self._data, fh, sort_keys=False)

    @staticmethod
    def _key(issue: DetectedIssue) -> str:
        return (
            f"{issue.alert.name}:"
            f"{issue.alert.namespace}:"
            f"{issue.alert.app}:"
            f"{issue.pod_name}:"
            f"{issue.restart_count}"
        )


def load_state(config: AgentConfig) -> AgentState:
    return AgentState(config.manifests_repo_path / config.state_file)
