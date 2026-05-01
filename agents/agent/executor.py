from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone

from .config import AgentConfig


@dataclass(frozen=True)
class PullRequestResult:
    branch: str
    pr_url: str
    dry_run: bool


def create_fix_pr(config: AgentConfig, dry_run: bool = False) -> PullRequestResult:
    branch = _branch_name(config)
    title = f"Fix {config.app_name} missing {config.required_env_name}"
    body = (
        "Automated GitOps self-healing PR.\n\n"
        f"- App: `{config.app_name}`\n"
        f"- Fix: add `{config.required_env_name}` to the Deployment env list\n"
        "- Safety: manifest-only change, no direct cluster mutation\n"
    )

    if dry_run:
        return PullRequestResult(branch=branch, pr_url="dry-run: no PR created", dry_run=True)

    _run(["git", "checkout", "-b", branch], cwd=config.manifests_repo_path)
    _run(["git", "add", str(config.deployment_path)], cwd=config.manifests_repo_path)
    _run(
        ["git", "commit", "-m", f"Fix missing {config.required_env_name} for {config.app_name}"],
        cwd=config.manifests_repo_path,
    )
    _run(["git", "push", "-u", "origin", branch], cwd=config.manifests_repo_path)
    pr_url = _run(
        [
            "gh",
            "pr",
            "create",
            "--repo",
            config.github_repo,
            "--base",
            config.base_branch,
            "--head",
            branch,
            "--title",
            title,
            "--body",
            body,
        ],
        cwd=config.manifests_repo_path,
    )
    return PullRequestResult(branch=branch, pr_url=pr_url, dry_run=False)


def _branch_name(config: AgentConfig) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{config.branch_prefix}/{config.app_name}-missing-env-{stamp}"


def _run(args: list[str], cwd) -> str:
    completed = subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)
    return completed.stdout.strip()
