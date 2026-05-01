from __future__ import annotations

from pathlib import Path

import yaml

from .config import AgentConfig


def required_env_present(config: AgentConfig) -> bool:
    deployment_file = config.deployment_file
    if not deployment_file.exists():
        raise FileNotFoundError(f"Deployment manifest not found: {deployment_file}")

    document = _load_yaml(deployment_file)
    container = _find_container(document, config)
    env = container.get("env", [])
    return any(item.get("name") == config.required_env_name for item in env)


def add_required_env(config: AgentConfig) -> bool:
    deployment_file = config.deployment_file
    if not deployment_file.exists():
        raise FileNotFoundError(f"Deployment manifest not found: {deployment_file}")

    document = _load_yaml(deployment_file)
    container = _find_container(document, config)

    env = container.setdefault("env", [])
    existing = next((item for item in env if item.get("name") == config.required_env_name), None)
    if existing:
        if existing.get("value") == config.required_env_value:
            return False
        existing["value"] = config.required_env_value
    else:
        env.append({"name": config.required_env_name, "value": config.required_env_value})

    _write_yaml(deployment_file, document)
    return True


def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _find_container(document: dict, config: AgentConfig) -> dict:
    if document.get("kind") != "Deployment":
        raise RuntimeError(f"Expected Deployment manifest, found {document.get('kind')}")

    containers = document["spec"]["template"]["spec"]["containers"]
    container = next((item for item in containers if item["name"] == config.container_name), None)
    if not container:
        raise RuntimeError(f"Container {config.container_name} not found in deployment")
    return container


def _write_yaml(path: Path, document: dict) -> None:
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(document, fh, sort_keys=False)
