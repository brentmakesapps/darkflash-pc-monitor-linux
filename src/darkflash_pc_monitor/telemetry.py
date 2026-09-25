"""Read CPU and Intel Xe GPU package temperatures through lm-sensors."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


class TelemetryError(RuntimeError):
    """lm-sensors did not provide the requested telemetry source."""


@dataclass(frozen=True)
class GpuDevice:
    chip: str
    temperature_c: float


@dataclass(frozen=True)
class Telemetry:
    cpu_temperature_c: float
    gpu: GpuDevice


def sensors_snapshot() -> dict:
    """Return a single lm-sensors JSON snapshot."""
    try:
        result = subprocess.run(
            ["sensors", "-j"],
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout)
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        raise TelemetryError(f"unable to read sensors -j: {exc}") from exc


def _temperature(entries: dict, label: str) -> float | None:
    values = entries.get(label)
    if not isinstance(values, dict):
        return None
    for key, value in values.items():
        if key.endswith("_input") and "temp" in key and isinstance(value, (int, float)):
            return float(value)
    return None


def read_cpu_temperature(snapshot: dict) -> float:
    """Read the Intel coretemp package sensor."""
    for chip, entries in snapshot.items():
        if not chip.startswith("coretemp") or not isinstance(entries, dict):
            continue
        temperature = _temperature(entries, "Package id 0")
        if temperature is not None:
            return temperature
    raise TelemetryError("Intel coretemp package sensor was not found")


def discover_gpus(
    snapshot: dict | None = None,
    *,
    hwmon_root: Path = Path("/sys/class/hwmon"),
) -> list[GpuDevice]:
    """List Intel Xe cards with a package-temperature hwmon label.

    `sensors -j` cannot represent Xe's duplicate ``pkg`` JSON key: its
    temperature object is overwritten by the energy object. hwmon exposes the
    package label and temperature as distinct files, so it is the authoritative
    source for GPU selection.
    """
    devices: list[GpuDevice] = []
    for hwmon in sorted(hwmon_root.glob("hwmon*")):
        try:
            if (hwmon / "name").read_text().strip() != "xe":
                continue
            pci_name = Path((hwmon / "device").resolve()).name
            match = re.fullmatch(r"(?:[0-9a-f]{4}:)?([0-9a-f]{2}:[0-9a-f]{2})\.[0-7]", pci_name)
            if match is None:
                continue
            chip = f"xe-pci-{match.group(1).replace(':', '')}"
        except OSError:
            continue
        for label_path in hwmon.glob("temp*_label"):
            try:
                if label_path.read_text().strip() != "pkg":
                    continue
                input_path = label_path.with_name(
                    label_path.name.removesuffix("_label") + "_input"
                )
                temperature = int(input_path.read_text().strip()) / 1000
            except (OSError, ValueError):
                continue
            devices.append(GpuDevice(chip=chip, temperature_c=temperature))
            break
    return sorted(devices, key=lambda device: device.chip)


def read_telemetry(
    gpu_chip: str,
    snapshot: dict | None = None,
    *,
    hwmon_root: Path = Path("/sys/class/hwmon"),
) -> Telemetry:
    """Read the CPU package and the user-selected Intel Xe GPU package."""
    data = snapshot if snapshot is not None else sensors_snapshot()
    gpus = discover_gpus(hwmon_root=hwmon_root)
    gpu = next((device for device in gpus if device.chip == gpu_chip), None)
    if gpu is None:
        choices = ", ".join(device.chip for device in gpus) or "none"
        raise TelemetryError(f"GPU {gpu_chip!r} was not found; available: {choices}")
    return Telemetry(cpu_temperature_c=read_cpu_temperature(data), gpu=gpu)
