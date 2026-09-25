"""Persistent user preferences for the native display service."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "darkflash-pc-monitor" / "config.json"
GPU_DISPLAY_METRICS = {"utilization", "memory"}


def _load(path: Path) -> dict[str, object]:
    """Return the saved configuration, or an empty mapping when unavailable."""
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def selected_gpu(path: Path = CONFIG_PATH) -> str | None:
    """Return the configured GPU identifier, if one has been selected."""
    data = _load(path)
    gpu = data.get("gpu")
    return gpu if isinstance(gpu, str) and gpu else None


def selected_mode(path: Path = CONFIG_PATH) -> str:
    """Return the configured display mode."""
    data = _load(path)
    mode = data.get("mode")
    return mode if mode in {"temperature", "utilization", "auto", "disabled"} else "temperature"


def selected_gpu_display(path: Path = CONFIG_PATH) -> tuple[str, str]:
    """Return the persisted GPU digit and bar metric sources."""
    data = _load(path)
    digits = data.get("gpu_digits")
    bar = data.get("gpu_bar")
    return (
        digits if digits in GPU_DISPLAY_METRICS else "memory",
        bar if bar in GPU_DISPLAY_METRICS else "utilization",
    )


def selected_auto_display(path: Path = CONFIG_PATH) -> tuple[int, str]:
    """Return the persisted auto-rotation interval and first page."""
    data = _load(path)
    interval = data.get("auto_interval_seconds")
    start = data.get("auto_start_page")
    return (
        interval if isinstance(interval, int) and interval > 0 else 5,
        start if start in {"temperature", "utilization"} else "utilization",
    )


def selected_temperature_unit(path: Path = CONFIG_PATH) -> str:
    """Return the persisted temperature unit."""
    data = _load(path)
    return data.get("temperature_unit") if data.get("temperature_unit") in {"celsius", "fahrenheit"} else "celsius"


def save_selected_temperature_unit(unit: str, path: Path = CONFIG_PATH) -> None:
    """Atomically persist the temperature unit."""
    if unit not in {"celsius", "fahrenheit"}:
        raise ValueError(f"unsupported temperature unit: {unit}")
    data = _load(path)
    data["temperature_unit"] = unit
    _save(data, path)


def _save(data: dict[str, object], path: Path) -> None:
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
    data = _load(path)
    data["gpu"] = gpu
    _save(data, path)


def save_selected_mode(mode: str, path: Path = CONFIG_PATH) -> None:
    """Atomically persist a display mode."""
    if mode not in {"temperature", "utilization", "auto", "disabled"}:
        raise ValueError(f"unsupported display mode: {mode}")
    data = _load(path)
    data["mode"] = mode
    _save(data, path)


def save_selected_auto_display(interval: int, start: str, path: Path = CONFIG_PATH) -> None:
    """Atomically persist auto-rotation settings and activate Auto mode."""
    if interval <= 0 or start not in {"temperature", "utilization"}:
        raise ValueError("invalid auto display settings")
    data = _load(path)
    data.update(
        {
            "mode": "auto",
            "auto_interval_seconds": interval,
            "auto_start_page": start,
        }
    )
    _save(data, path)


def save_selected_gpu_display(digits: str, bar: str, path: Path = CONFIG_PATH) -> None:
    """Atomically persist independent GPU digit and bar metric sources."""
    if digits not in GPU_DISPLAY_METRICS or bar not in GPU_DISPLAY_METRICS:
        raise ValueError("unsupported GPU display metric")
    data = _load(path)
    data["gpu_digits"] = digits
    data["gpu_bar"] = bar
    _save(data, path)
