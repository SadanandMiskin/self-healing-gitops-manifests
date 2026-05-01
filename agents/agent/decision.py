from __future__ import annotations

from dataclasses import dataclass

from .config import AgentConfig
from .detector import DetectedIssue
from .diagnoser import Diagnosis
from .fixer import required_env_present


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

    if config.deployment_file.name != "deployment.yaml":
        return Decision(False, "Configured fix target is not deployment.yaml.")

    if required_env_present(config):
        return Decision(False, f"Manifest already contains {config.required_env_name}; no GitOps fix needed.")

    log_evidence = config.required_env_name in issue.logs and "missing" in issue.logs.lower()
    llm_evidence = diagnosis.issue_type == "missing_env_var" and diagnosis.confidence >= 0.8
    gitops_evidence = issue.restart_count > 0

    if log_evidence or llm_evidence:
        return Decision(True, f"Approved manifest-only fix for missing {config.required_env_name}.")

    if gitops_evidence:
        return Decision(
            True,
            (
                f"Approved safe GitOps fallback: alert is firing, pod restarted {issue.restart_count} "
                f"time(s), and manifest is missing {config.required_env_name}."
            ),
        )

    return Decision(False, "No log, LLM, or restart evidence supports the missing env-var fix.")
