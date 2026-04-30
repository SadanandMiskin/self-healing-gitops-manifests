from __future__ import annotations

from dataclasses import dataclass

import requests

from .config import AgentConfig


@dataclass(frozen=True)
class Alert:
    name: str
    app: str
    namespace: str
    severity: str
    summary: str
    state: str


def mock_crashloop_alert(config: AgentConfig) -> Alert:
    return Alert(
        name="SelfHealingApiCrashLoopBackOff",
        app=config.app_name,
        namespace=config.namespace,
        severity="warning",
        summary=f"{config.app_name} is in CrashLoopBackOff",
        state="firing",
    )


def get_firing_alert(config: AgentConfig, prometheus_url: str | None = None) -> Alert | None:
    base_url = prometheus_url or config.prometheus_url
    response = requests.get(f"{base_url.rstrip('/')}/api/v1/alerts", timeout=10)
    response.raise_for_status()

    payload = response.json()
    for alert in payload.get("data", {}).get("alerts", []):
        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})
        if (
            labels.get("alertname") == "SelfHealingApiCrashLoopBackOff"
            and labels.get("app") == config.app_name
            and labels.get("self_healing") == "enabled"
            and alert.get("state") == "firing"
        ):
            return Alert(
                name=labels["alertname"],
                app=labels["app"],
                namespace=labels.get("namespace", config.namespace),
                severity=labels.get("severity", "warning"),
                summary=annotations.get("summary", ""),
                state=alert["state"],
            )

    return None
