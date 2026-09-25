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
    name: str
    bdf: str = ""
    driver: str = ""


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
    gpu_busy_percent: float | None = None
    gpu_memory_percent: float | None = None
    gpu_combined_percent: float | None = None


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


_GPU_HWMON_DRIVERS = frozenset({"xe", "i915", "amdgpu", "nvidia", "nouveau"})
_PREFERRED_TEMPERATURE_LABELS = ("pkg", "edge", "gpu", "junction")


def _gpu_bdf_from_path(path: Path) -> str | None:
    for part in reversed(path.parts):
        match = re.fullmatch(r"(?:[0-9a-f]{4}:)?([0-9a-f]{2}:[0-9a-f]{2}\.[0-7])", part)
        if match is not None:
            return f"0000:{match.group(1)}"
    return None


def _pci_name(bdf: str) -> str:
    """Return a concise PCI product name, retaining lspci's useful brackets."""
    try:
        output = subprocess.run(
            ["lspci", "-s", bdf],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return bdf
    names = re.findall(r"\[([^\]]+)\]", output)
    for name in reversed(names):
        if not re.fullmatch(r"(?:[0-9a-f]{4}:)?[0-9a-f]{4}", name, re.IGNORECASE):
            return name
    _, _, description = output.partition(": ")
    return re.sub(r" \(rev [^)]+\)$", "", description)


def _is_display_pci_device(bdf: str) -> bool:
    """Whether lspci identifies this PCI function as a display adapter."""
    try:
        output = subprocess.run(
            ["lspci", "-s", bdf],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return False
    return any(kind in output for kind in ("VGA compatible controller", "3D controller", "Display controller"))


def _read_hwmon_temperature(hwmon: Path) -> float | None:
    temperatures: list[tuple[int, str, float]] = []
    for input_path in hwmon.glob("temp*_input"):
        try:
            label_path = input_path.with_name(input_path.name.removesuffix("_input") + "_label")
            label = label_path.read_text().strip().lower() if label_path.exists() else ""
            temperature = int(input_path.read_text().strip()) / 1000
        except (OSError, ValueError):
            continue
        priority = (
            _PREFERRED_TEMPERATURE_LABELS.index(label)
            if label in _PREFERRED_TEMPERATURE_LABELS
            else len(_PREFERRED_TEMPERATURE_LABELS)
        )
        temperatures.append((priority, input_path.name, temperature))
    return min(temperatures, default=(0, "", None))[2]


def discover_gpus(
    snapshot: dict | None = None,
    *,
    hwmon_root: Path = Path("/sys/class/hwmon"),
) -> list[GpuDevice]:
    """List PCI GPUs with supported driver-backed hwmon temperature sensors.

    Xe is physically verified. i915, AMDGPU, NVIDIA, and Nouveau paths use the
    same PCI/hwmon mechanism but are intentionally unverified.
    """
    devices: list[GpuDevice] = []
    for hwmon in sorted(hwmon_root.glob("hwmon*")):
        try:
            driver = (hwmon / "name").read_text().strip()
            bdf = _gpu_bdf_from_path((hwmon / "device").resolve())
            if bdf is None:
                continue
        except OSError:
            continue
        if driver not in _GPU_HWMON_DRIVERS and not _is_display_pci_device(bdf):
            continue
        temperature = _read_hwmon_temperature(hwmon)
        if temperature is None:
            continue
        compact_bdf = bdf.removeprefix("0000:").replace(":", "").removesuffix(".0")
        identifier = driver if re.fullmatch(r"[a-z0-9]+", driver) else "generic"
        chip = f"{identifier}-pci-{compact_bdf}"
        devices.append(
            GpuDevice(
                chip=chip,
                temperature_c=temperature,
                name=_pci_name(bdf),
                bdf=bdf,
                driver=driver,
            )
        )
    return sorted(devices, key=lambda device: device.bdf or device.chip)


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


def read_combined_telemetry(
    snapshot: dict | None = None, *, hwmon_root: Path = Path("/sys/class/hwmon")
) -> Telemetry:
    """Read CPU temperature and the average temperature of all discovered GPUs."""
    data = snapshot if snapshot is not None else sensors_snapshot()
    gpus = discover_gpus(hwmon_root=hwmon_root)
    if not gpus:
        raise TelemetryError("no Intel Xe GPU temperature sources were found")
    return Telemetry(
        cpu_temperature_c=read_cpu_temperature(data),
        gpu=GpuDevice(
            chip="combined",
            temperature_c=sum(device.temperature_c for device in gpus) / len(gpus),
            name="Combined GPUs",
        ),
    )


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
    match = re.fullmatch(r"[a-z0-9]+-pci-([0-9a-f]{4})", gpu_chip)
    if match is None:
        raise TelemetryError(f"invalid GPU identifier: {gpu_chip!r}")
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


def _nvtop_snapshot() -> list[dict]:
    try:
        snapshot = json.loads(
            subprocess.run(
                ["nvtop", "--snapshot", "--no-color", "--no-plot", "--no-processes"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout
        )
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        raise TelemetryError(f"unable to read nvtop GPU utilization: {exc}") from exc
    if not isinstance(snapshot, list):
        raise TelemetryError("nvtop did not return a device list")
    return [device for device in snapshot if isinstance(device, dict)]


def _nvtop_device_for_gpu(gpu: GpuDevice, snapshot: list[dict]) -> dict | None:
    target_words = set(re.findall(r"[a-z0-9]+", gpu.name.lower())) - {
        "corporation",
        "controller",
        "graphics",
        "intel",
        "nvidia",
        "radeon",
    }
    if not target_words:
        return None
    scored_matches = [
        (
            len(target_words & set(re.findall(r"[a-z0-9]+", str(device.get("device_name")).lower()))),
            device,
        )
        for device in snapshot
    ]
    best_score = max((score for score, _device in scored_matches), default=0)
    matches = [device for score, device in scored_matches if score == best_score]
    return matches[0] if best_score >= 2 and len(matches) == 1 else None


def _percent(value: object) -> float | None:
    match = re.fullmatch(r"(\d+(?:\.\d+)?)%", str(value))
    return float(match.group(1)) if match is not None else None


def read_gpu_metrics(gpu_chip: str) -> tuple[float | None, float | None]:
    """Read a selected discovered GPU's current busy and memory use from nvtop."""
    gpu = next((device for device in discover_gpus() if device.chip == gpu_chip), None)
    if gpu is None:
        raise TelemetryError(f"GPU {gpu_chip!r} was not found")
    device = _nvtop_device_for_gpu(gpu, _nvtop_snapshot())
    if device is None:
        return None, None
    return _percent(device.get("gpu_util")), _percent(device.get("mem_util"))


def read_gpu_utilization_percent(gpu_chip: str) -> float | None:
    """Read the selected Xe device's current busy percentage from nvtop."""
    return read_gpu_metrics(gpu_chip)[0]


def read_combined_gpu_utilization_percent() -> float | None:
    """Read the average current utilization across discovered GPUs."""
    snapshot = _nvtop_snapshot()
    values: list[float] = []
    for gpu in discover_gpus():
        device = _nvtop_device_for_gpu(gpu, snapshot)
        value = _percent(device.get("gpu_util")) if device is not None else None
        if value is not None:
            values.append(value)
    return sum(values) / len(values) if values else None


def read_utilization_snapshot(
    gpu_chip: str,
    *,
    proc_stat: Path = Path("/proc/stat"),
    fdinfo_root: Path = Path("/proc"),
    clock_ns: Callable[[], int] = time.monotonic_ns,
    gpu_utilization_reader: Callable[[str], float | None] = read_gpu_utilization_percent,
    gpu_memory_reader: Callable[[str], float | None] = lambda gpu: read_gpu_metrics(gpu)[1],
    gpu_combined_reader: Callable[[], float | None] = read_combined_gpu_utilization_percent,
) -> UtilizationSnapshot:
    """Read cumulative CPU and Xe engine counters for an interval sample."""
    total, idle = _cpu_ticks(proc_stat)
    return UtilizationSnapshot(
        timestamp_ns=clock_ns(),
        cpu_total_ticks=total,
        cpu_idle_ticks=idle,
        gpu_engine_ns=(
            _gpu_engine_time_ns(fdinfo_root, _gpu_bdf(gpu_chip))
            if gpu_chip.startswith("xe-pci-")
            else 0
        ),
        gpu_busy_percent=gpu_utilization_reader(gpu_chip),
        gpu_memory_percent=gpu_memory_reader(gpu_chip),
        gpu_combined_percent=gpu_combined_reader(),
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
    gpu_percent = (
        current.gpu_busy_percent
        if current.gpu_busy_percent is not None
        else 100 * (current.gpu_engine_ns - previous.gpu_engine_ns) / wall_delta
    )
    return Utilization(
        cpu_percent=max(0, min(100, cpu_percent)),
        gpu_percent=max(0, min(100, gpu_percent)),
    )
