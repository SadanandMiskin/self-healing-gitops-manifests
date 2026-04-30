from __future__ import annotations

import argparse
import sys

from .config import load_config
from .decision import decide
from .detector import detect_issue
from .diagnoser import diagnose
from .executor import create_fix_pr
from .fixer import add_required_env
from .observer import get_firing_alert, mock_crashloop_alert


def main() -> int:
    parser = argparse.ArgumentParser(description="Self-healing GitOps agent")
    parser.add_argument("--config", required=True, help="Path to agent config YAML")
    parser.add_argument("--prometheus-url", help="Prometheus URL, for example http://localhost:9090")
    parser.add_argument("--mock-alert", action="store_true", help="Use a built-in CrashLoopBackOff alert")
    parser.add_argument("--llm", choices=["mock", "openai"], help="Override configured LLM provider")
    parser.add_argument("--dry-run", action="store_true", help="Modify manifest but skip git commit/push/PR")
    args = parser.parse_args()

    config = load_config(args.config)
    alert = mock_crashloop_alert(config) if args.mock_alert else get_firing_alert(config, args.prometheus_url)
    if not alert:
        print("No matching firing alert found.")
        return 0

    print(f"Observed alert: {alert.name} for app={alert.app} namespace={alert.namespace}")
    issue = detect_issue(config, alert)
    print(
        f"Detected pod={issue.pod_name} phase={issue.phase} "
        f"waiting_reason={issue.waiting_reason or 'unknown'} restarts={issue.restart_count}"
    )

    diagnosis = diagnose(config, issue, args.llm)
    print(f"Diagnosis: {diagnosis.issue_type} confidence={diagnosis.confidence:.2f}")
    print(diagnosis.explanation)

    decision = decide(config, issue, diagnosis)
    print(f"Decision: {'approved' if decision.approved else 'blocked'} - {decision.reason}")
    if not decision.approved:
        return 2

    changed = add_required_env(config)
    if not changed:
        print("Manifest already contains the required env var. No PR needed.")
        return 0

    result = create_fix_pr(config, dry_run=args.dry_run)
    print(f"Branch: {result.branch}")
    print(f"Pull request: {result.pr_url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
