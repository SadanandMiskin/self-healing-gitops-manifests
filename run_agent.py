from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
AGENTS_DIR = ROOT / "agents"
CONFIG_FILE = AGENTS_DIR / "config.local.yaml"
EXAMPLE_CONFIG = AGENTS_DIR / "config.example.yaml"
REQUIREMENTS = AGENTS_DIR / "requirements.txt"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bootstrap dependencies and run the continuous self-healing agent."
    )
    parser.add_argument("--config", default=str(CONFIG_FILE), help="Agent config YAML path")
    parser.add_argument("--prometheus-url", default="http://localhost:9090", help="Prometheus URL")
    parser.add_argument("--github-repo", default=os.getenv("GITHUB_REPO"), help="OWNER/manifests-repo")
    parser.add_argument(
        "--manifests-repo-path",
        default=os.getenv("MANIFESTS_REPO_PATH"),
        help="Local path to the manifests Git repository",
    )
    parser.add_argument(
        "--required-env-value",
        default=os.getenv("REQUIRED_GREETING_VALUE"),
        help="Value inserted for REQUIRED_GREETING",
    )
    parser.add_argument("--llm", choices=["gemini", "mock"], help="Override configured LLM provider")
    parser.add_argument("--mock-alert", action="store_true", help="Use built-in demo alert")
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit")
    parser.add_argument("--dry-run", action="store_true", help="Skip git commit, push, and PR creation")
    parser.add_argument("--skip-install", action="store_true", help="Do not install/update Python dependencies")
    args = parser.parse_args()

    config_path = Path(args.config)
    ensure_config(config_path)
    apply_config_overrides(config_path, args)
    ensure_dependencies(skip_install=args.skip_install)

    command = [
        sys.executable,
        "-m",
        "agent.main",
        "--config",
        str(config_path.resolve()),
        "--prometheus-url",
        args.prometheus_url,
    ]
    if args.llm:
        command.extend(["--llm", args.llm])
    if args.mock_alert:
        command.append("--mock-alert")
    if args.once:
        command.append("--once")
    if args.dry_run:
        command.append("--dry-run")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(AGENTS_DIR)

    return subprocess.call(command, cwd=AGENTS_DIR, env=env)


def ensure_config(config_path: Path) -> None:
    if config_path.exists():
        return

    if config_path.resolve() != CONFIG_FILE.resolve():
        raise FileNotFoundError(f"Config file does not exist: {config_path}")

    shutil.copyfile(EXAMPLE_CONFIG, CONFIG_FILE)
    print(f"Created default config: {CONFIG_FILE}")
    print("Using default config. Pass --github-repo and --manifests-repo-path to override it.")


def apply_config_overrides(config_path: Path, args: argparse.Namespace) -> None:
    updates = {}
    if args.github_repo:
        updates["github_repo"] = args.github_repo
    if args.manifests_repo_path:
        updates["manifests_repo_path"] = str(Path(args.manifests_repo_path).resolve())
    if args.required_env_value:
        updates["required_env_value"] = args.required_env_value
    if args.prometheus_url:
        updates["prometheus_url"] = args.prometheus_url
    if args.llm:
        updates["llm_provider"] = args.llm

    if not updates:
        return

    lines = config_path.read_text(encoding="utf-8").splitlines()
    seen = set()
    next_lines = []
    for line in lines:
        key = line.split(":", 1)[0].strip() if ":" in line else ""
        if key in updates and not line.lstrip().startswith("#"):
            next_lines.append(f"{key}: {updates[key]}")
            seen.add(key)
        else:
            next_lines.append(line)

    for key, value in updates.items():
        if key not in seen:
            next_lines.append(f"{key}: {value}")

    config_path.write_text("\n".join(next_lines) + "\n", encoding="utf-8")


def ensure_dependencies(skip_install: bool) -> None:
    if not skip_install:
        print("Installing agent dependencies...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS)])


if __name__ == "__main__":
    sys.exit(main())
