"""Persistent user preferences for the native display service."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "darkflash-pc-monitor" / "config.json"


def selected_gpu(path: Path = CONFIG_PATH) -> str | None:
    """Return the configured GPU identifier, if one has been selected."""
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    gpu = data.get("gpu")
    return gpu if isinstance(gpu, str) and gpu else None


def selected_mode(path: Path = CONFIG_PATH) -> str:
    """Return the configured display mode."""
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return "temperature"
    mode = data.get("mode")
    return mode if mode in {"temperature", "utilization"} else "temperature"


def _save(data: dict[str, str], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", dir=path.parent, prefix=".config-", delete=False
    ) as temporary:
        json.dump(data, temporary, indent=2)
        temporary.write("\n")
        temporary_path = Path(temporary.name)
    os.replace(temporary_path, path)


def save_selected_gpu(gpu: str, path: Path = CONFIG_PATH) -> None:
    """Atomically persist a validated GPU identifier."""
    _save({"gpu": gpu, "mode": selected_mode(path)}, path)


def save_selected_mode(mode: str, path: Path = CONFIG_PATH) -> None:
    """Atomically persist a display mode."""
    if mode not in {"temperature", "utilization"}:
        raise ValueError(f"unsupported display mode: {mode}")
    data = {"mode": mode}
    gpu = selected_gpu(path)
    if gpu is not None:
        data["gpu"] = gpu
    _save(data, path)
