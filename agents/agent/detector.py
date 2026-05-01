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

    pod = _select_relevant_pod(items, config)
    pod_name = pod["metadata"]["name"]
    phase = pod.get("status", {}).get("phase", "Unknown")
    statuses = pod.get("status", {}).get("containerStatuses", [])
    target = next((s for s in statuses if s.get("name") == config.container_name), statuses[0])
    state = target.get("state", {})
    waiting_reason = state.get("waiting", {}).get("reason", "")
    restart_count = int(target.get("restartCount", 0))
    return pod_name, phase, waiting_reason, restart_count


def _select_relevant_pod(items: list[dict], config: AgentConfig) -> dict:
    def pod_score(pod: dict) -> tuple[int, int]:
        statuses = pod.get("status", {}).get("containerStatuses", [])
        target = next((s for s in statuses if s.get("name") == config.container_name), statuses[0] if statuses else {})
        waiting_reason = target.get("state", {}).get("waiting", {}).get("reason", "")
        restart_count = int(target.get("restartCount", 0))
        is_crashloop = 1 if waiting_reason == "CrashLoopBackOff" else 0
        return is_crashloop, restart_count

    return max(items, key=pod_score)


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
    previous_args = args + ["--previous"]
    previous = subprocess.run(previous_args, capture_output=True, text=True)
    sections = []

    if previous.returncode == 0 and previous.stdout.strip():
        sections.append("=== previous container logs ===")
        sections.append(previous.stdout.strip())
    elif previous.stderr.strip():
        sections.append("=== previous container logs unavailable ===")
        sections.append(previous.stderr.strip())

    if completed.returncode == 0 and completed.stdout.strip():
        sections.append("=== current container logs ===")
        sections.append(completed.stdout.strip())
    elif completed.stderr.strip():
        sections.append("=== current container logs unavailable ===")
        sections.append(completed.stderr.strip())

    return "\n".join(sections)


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
