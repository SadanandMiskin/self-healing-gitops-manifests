from __future__ import annotations

import os
import json
import re
from dataclasses import dataclass

from .config import AgentConfig
from .detector import DetectedIssue
from .fixer import required_env_present


@dataclass(frozen=True)
class Diagnosis:
    issue_type: str
    confidence: float
    explanation: str
    recommended_fix: str


def diagnose(config: AgentConfig, issue: DetectedIssue, provider: str | None = None) -> Diagnosis:
    llm_provider = provider or config.llm_provider
    if llm_provider == "mistral":
        return _diagnose_with_mistral(config, issue)
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

    if _gitops_manifest_evidence(config, issue):
        return Diagnosis(
            issue_type="missing_env_var",
            confidence=0.95,
            explanation=(
                f"GitOps manifest is missing {config.required_env_name} and the pod has "
                f"restarted {issue.restart_count} time(s). This matches the supported demo failure."
            ),
            recommended_fix=f"Add {config.required_env_name} to the Deployment env list.",
        )

    return Diagnosis(
        issue_type="unknown",
        confidence=0.2,
        explanation="The logs do not match the supported missing environment variable pattern.",
        recommended_fix="No automated fix recommended.",
    )


def _diagnose_with_mistral(config: AgentConfig, issue: DetectedIssue) -> Diagnosis:
    if not os.getenv("MISTRAL_API_KEY"):
        raise RuntimeError("MISTRAL_API_KEY is required when llm_provider is mistral")

    from mistralai import Mistral

    client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
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
Return only JSON with keys: category, confidence, explanation, recommended_fix.
"""
    response = client.chat.complete(
        model=config.llm_model,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        temperature=0,
    )
    text = (response.choices[0].message.content or "").strip()
    issue_type, confidence, recommended_fix = _parse_llm_response(text)

    log_evidence_has_missing_env = (
        config.required_env_name in issue.logs and "missing" in issue.logs.lower()
    )
    if log_evidence_has_missing_env and issue_type == "unknown":
        issue_type = "missing_env_var"
        confidence = max(confidence, 0.95)
        recommended_fix = f"Add {config.required_env_name} to the Deployment env list."

    if _gitops_manifest_evidence(config, issue):
        issue_type = "missing_env_var"
        confidence = max(confidence, 0.95)
        recommended_fix = f"Add {config.required_env_name} to the Deployment env list."
        text = (
            f"{text}\n\nGitOps evidence: deployment.yaml is missing "
            f"{config.required_env_name}, and the pod has restarted {issue.restart_count} time(s)."
        )

    return Diagnosis(
        issue_type=issue_type,
        confidence=confidence,
        explanation=text,
        recommended_fix=recommended_fix,
    )


def _parse_llm_response(text: str) -> tuple[str, float, str]:
    payload = _extract_json(text)
    if payload:
        category = str(payload.get("category", payload.get("issue_type", "unknown"))).strip()
        confidence = _safe_float(payload.get("confidence"), default=0.3)
        recommended_fix = str(
            payload.get("recommended_fix", payload.get("fix", "No automated fix recommended."))
        )
    else:
        lowered = text.lower()
        category = "missing_env_var" if re.search(r"\bmissing_env_var\b", lowered) else "unknown"
        confidence = _extract_confidence(lowered)
        recommended_fix = "No automated fix recommended."

    issue_type = "missing_env_var" if category == "missing_env_var" else "unknown"
    return issue_type, confidence, recommended_fix


def _extract_json(text: str) -> dict | None:
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    candidate = match.group(1) if match else text
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


def _extract_confidence(text: str) -> float:
    match = re.search(r"confidence\s*[:=]\s*([01](?:\.\d+)?)", text)
    if not match:
        return 0.3
    return _safe_float(match.group(1), default=0.3)


def _safe_float(value, default: float) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, confidence))


def _gitops_manifest_evidence(config: AgentConfig, issue: DetectedIssue) -> bool:
    try:
        manifest_missing_env = not required_env_present(config)
    except (FileNotFoundError, RuntimeError, KeyError, TypeError):
        return False
    return manifest_missing_env and issue.restart_count > 0
