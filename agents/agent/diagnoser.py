from __future__ import annotations

import os
from dataclasses import dataclass

from .config import AgentConfig
from .detector import DetectedIssue


@dataclass(frozen=True)
class Diagnosis:
    issue_type: str
    confidence: float
    explanation: str
    recommended_fix: str


def diagnose(config: AgentConfig, issue: DetectedIssue, provider: str | None = None) -> Diagnosis:
    llm_provider = provider or config.llm_provider
    if llm_provider == "openai":
        return _diagnose_with_openai(config, issue)
    return _diagnose_with_mock(config, issue)


def _diagnose_with_mock(config: AgentConfig, issue: DetectedIssue) -> Diagnosis:
    if config.required_env_name in issue.logs and "missing" in issue.logs.lower():
        return Diagnosis(
            issue_type="missing_env_var",
            confidence=0.99,
            explanation=(
                f"Container logs show {config.required_env_name} is missing at startup, "
                "which explains the CrashLoopBackOff."
            ),
            recommended_fix=f"Add {config.required_env_name} to the Deployment env list.",
        )

    return Diagnosis(
        issue_type="unknown",
        confidence=0.2,
        explanation="The logs do not match the supported missing environment variable pattern.",
        recommended_fix="No automated fix recommended.",
    )


def _diagnose_with_openai(config: AgentConfig, issue: DetectedIssue) -> Diagnosis:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required when llm_provider is openai")

    from openai import OpenAI

    client = OpenAI()
    prompt = f"""
You are diagnosing a Kubernetes CrashLoopBackOff for a demo service.

Allowed diagnosis categories:
- missing_env_var
- unknown

Only decide whether the logs indicate the required environment variable is missing.

Required env var: {config.required_env_name}
Pod: {issue.pod_name}
Waiting reason: {issue.waiting_reason}
Restart count: {issue.restart_count}

Logs:
{issue.logs}

Return concise text with category, confidence from 0 to 1, explanation, and recommended fix.
"""
    response = client.responses.create(
        model=config.openai_model,
        input=prompt,
    )
    text = response.output_text.strip()
    lowered = text.lower()
    issue_type = "missing_env_var" if "missing_env_var" in lowered else "unknown"
    confidence = 0.9 if issue_type == "missing_env_var" else 0.3

    return Diagnosis(
        issue_type=issue_type,
        confidence=confidence,
        explanation=text,
        recommended_fix=f"Add {config.required_env_name} to the Deployment env list."
        if issue_type == "missing_env_var"
        else "No automated fix recommended.",
    )
