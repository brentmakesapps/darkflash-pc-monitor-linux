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


def save_selected_gpu(gpu: str, path: Path = CONFIG_PATH) -> None:
    """Atomically persist a validated GPU identifier."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", dir=path.parent, prefix=".config-", delete=False
    ) as temporary:
        json.dump({"gpu": gpu}, temporary, indent=2)
        temporary.write("\n")
        temporary_path = Path(temporary.name)
    os.replace(temporary_path, path)
