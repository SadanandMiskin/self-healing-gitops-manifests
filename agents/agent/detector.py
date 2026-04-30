from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass

from .config import AgentConfig
from .observer import Alert


@dataclass(frozen=True)
class DetectedIssue:
    alert: Alert
    pod_name: str
    phase: str
    waiting_reason: str
    restart_count: int
    logs: str


def _run(args: list[str]) -> str:
    completed = subprocess.run(args, check=True, capture_output=True, text=True)
    return completed.stdout.strip()


def _find_pod(config: AgentConfig) -> tuple[str, str, str, int]:
    raw = _run(
        [
            "kubectl",
            "get",
            "pods",
            "-n",
            config.namespace,
            "-l",
            f"app={config.app_name}",
            "-o",
            "json",
        ]
    )
    payload = json.loads(raw)
    items = payload.get("items", [])
    if not items:
        raise RuntimeError(f"No pod found for app={config.app_name} in namespace={config.namespace}")

    pod = items[0]
    pod_name = pod["metadata"]["name"]
    phase = pod.get("status", {}).get("phase", "Unknown")
    statuses = pod.get("status", {}).get("containerStatuses", [])
    target = next((s for s in statuses if s.get("name") == config.container_name), statuses[0])
    state = target.get("state", {})
    waiting_reason = state.get("waiting", {}).get("reason", "")
    restart_count = int(target.get("restartCount", 0))
    return pod_name, phase, waiting_reason, restart_count


def _logs(config: AgentConfig, pod_name: str) -> str:
    args = [
        "kubectl",
        "logs",
        "-n",
        config.namespace,
        pod_name,
        "-c",
        config.container_name,
        "--tail=200",
    ]
    completed = subprocess.run(args, capture_output=True, text=True)
    if completed.returncode == 0 and completed.stdout.strip():
        return completed.stdout

    previous_args = args + ["--previous"]
    previous = subprocess.run(previous_args, capture_output=True, text=True)
    if previous.returncode == 0 and previous.stdout.strip():
        return previous.stdout

    return completed.stderr or previous.stderr or ""


def detect_issue(config: AgentConfig, alert: Alert) -> DetectedIssue:
    if alert.name != "SelfHealingApiCrashLoopBackOff":
        raise RuntimeError(f"Unsupported alert: {alert.name}")
    if alert.app != config.app_name:
        raise RuntimeError(f"Alert app {alert.app} does not match configured app {config.app_name}")

    pod_name, phase, waiting_reason, restart_count = _find_pod(config)
    logs = _logs(config, pod_name)

    return DetectedIssue(
        alert=alert,
        pod_name=pod_name,
        phase=phase,
        waiting_reason=waiting_reason,
        restart_count=restart_count,
        logs=logs,
    )
