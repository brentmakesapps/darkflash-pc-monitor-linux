"""Read CPU and Intel Xe GPU package temperatures through lm-sensors."""

from __future__ import annotations

import json
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


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


@dataclass(frozen=True)
class UtilizationSnapshot:
    """Cumulative CPU ticks and selected-GPU engine nanoseconds."""

    timestamp_ns: int
    cpu_total_ticks: int
    cpu_idle_ticks: int
    gpu_engine_ns: int


@dataclass(frozen=True)
class Utilization:
    cpu_percent: float
    gpu_percent: float


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


def _cpu_ticks(proc_stat: Path) -> tuple[int, int]:
    try:
        fields = proc_stat.read_text().splitlines()[0].split()
        if fields[0] != "cpu":
            raise ValueError("missing aggregate CPU row")
        values = [int(value) for value in fields[1:]]
    except (OSError, IndexError, ValueError) as exc:
        raise TelemetryError(f"unable to read aggregate CPU utilization: {exc}") from exc
    if len(values) < 5:
        raise TelemetryError("aggregate CPU utilization row is incomplete")
    return sum(values), values[3] + values[4]


def _gpu_bdf(gpu_chip: str) -> str:
    match = re.fullmatch(r"xe-pci-([0-9a-f]{4})", gpu_chip)
    if match is None:
        raise TelemetryError(f"invalid Intel Xe GPU identifier: {gpu_chip!r}")
    compact = match.group(1)
    return f"0000:{compact[:2]}:{compact[2:]}.0"


def _gpu_engine_time_ns(fdinfo_root: Path, bdf: str) -> int:
    clients: dict[str, int] = {}
    for path in fdinfo_root.glob("*/fdinfo/*"):
        try:
            entries = dict(
                line.split(":", 1)
                for line in path.read_text().splitlines()
                if ":" in line
            )
        except OSError:
            continue
        if entries.get("drm-driver", "").strip() != "xe":
            continue
        if entries.get("drm-pdev", "").strip() != bdf:
            continue
        client_id = entries.get("drm-client-id", "").strip()
        if not client_id:
            continue
        engine_time = sum(
            int(value.strip().removesuffix(" ns"))
            for key, value in entries.items()
            if key.startswith("drm-engine-") and not key.startswith("drm-engine-capacity-")
        )
        clients[client_id] = max(clients.get(client_id, 0), engine_time)
    return sum(clients.values())


def read_utilization_snapshot(
    gpu_chip: str,
    *,
    proc_stat: Path = Path("/proc/stat"),
    fdinfo_root: Path = Path("/proc"),
    clock_ns: Callable[[], int] = time.monotonic_ns,
) -> UtilizationSnapshot:
    """Read cumulative CPU and Xe engine counters for an interval sample."""
    total, idle = _cpu_ticks(proc_stat)
    return UtilizationSnapshot(
        timestamp_ns=clock_ns(),
        cpu_total_ticks=total,
        cpu_idle_ticks=idle,
        gpu_engine_ns=_gpu_engine_time_ns(fdinfo_root, _gpu_bdf(gpu_chip)),
    )


def utilization_between(
    previous: UtilizationSnapshot, current: UtilizationSnapshot
) -> Utilization:
    """Calculate busy percentages between two cumulative counter snapshots."""
    cpu_delta = current.cpu_total_ticks - previous.cpu_total_ticks
    idle_delta = current.cpu_idle_ticks - previous.cpu_idle_ticks
    wall_delta = current.timestamp_ns - previous.timestamp_ns
    if cpu_delta <= 0 or wall_delta <= 0:
        raise TelemetryError("utilization counters did not advance")
    cpu_percent = 100 * (cpu_delta - idle_delta) / cpu_delta
    gpu_percent = 100 * (current.gpu_engine_ns - previous.gpu_engine_ns) / wall_delta
    return Utilization(
        cpu_percent=max(0, min(100, cpu_percent)),
        gpu_percent=max(0, min(100, gpu_percent)),
    )
