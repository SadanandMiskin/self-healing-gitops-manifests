from __future__ import annotations

from dataclasses import dataclass

from .config import AgentConfig
from .detector import DetectedIssue
from .diagnoser import Diagnosis


@dataclass(frozen=True)
class Decision:
    approved: bool
    reason: str


def decide(config: AgentConfig, issue: DetectedIssue, diagnosis: Diagnosis) -> Decision:
    if issue.alert.name != "SelfHealingApiCrashLoopBackOff":
        return Decision(False, "Alert is outside the supported self-healing policy.")

    if issue.alert.app != config.app_name:
        return Decision(False, "Alert targets a different app.")

    if issue.waiting_reason and issue.waiting_reason != "CrashLoopBackOff":
        return Decision(False, f"Pod waiting reason is {issue.waiting_reason}, not CrashLoopBackOff.")

    if diagnosis.issue_type != "missing_env_var":
        return Decision(False, "Diagnosis is not the supported missing_env_var type.")

    if diagnosis.confidence < 0.8:
        return Decision(False, f"Diagnosis confidence {diagnosis.confidence:.2f} is below threshold.")

    if config.required_env_name not in issue.logs:
        return Decision(False, f"Logs do not mention {config.required_env_name}.")

    if config.deployment_file.name != "deployment.yaml":
        return Decision(False, "Configured fix target is not deployment.yaml.")

    return Decision(True, f"Approved manifest-only fix for missing {config.required_env_name}.")
