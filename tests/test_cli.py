import sys

from darkflash_pc_monitor import cli
from darkflash_pc_monitor.protocol import blank_frame, utilization_frame
from darkflash_pc_monitor.telemetry import GpuDevice, TelemetryError


def test_render_writes_utilization_frame_when_utilization_mode_is_selected(monkeypatch) -> None:
    reports = []

    class FakeDisplay:
        def __init__(self, _node) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            pass

        def write(self, report: bytes) -> None:
            reports.append(report)

    monkeypatch.setattr(cli, "HidDisplay", FakeDisplay)
    monkeypatch.setattr(cli, "find_display", lambda: object())
    monkeypatch.setattr(cli, "selected_gpu", lambda: "xe-pci-0400")
    monkeypatch.setattr(cli, "selected_mode", lambda: "utilization")
    monkeypatch.setattr(cli, "read_utilization_snapshot", lambda _gpu: object())
    monkeypatch.setattr(sys, "argv", ["darkflash-pc-monitor", "render", "--once"])

    cli.main()

    assert reports == [utilization_frame(0, 0, 0, 0)]


def test_render_uses_the_latest_configured_gpu(monkeypatch) -> None:
    reports = []
    configured_gpus = iter(("dual", "xe-pci-0400"))

    class FakeDisplay:
        def __init__(self, _node) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            pass

        def write(self, report: bytes) -> None:
            reports.append(report)

    monkeypatch.setattr(cli, "HidDisplay", FakeDisplay)
    monkeypatch.setattr(cli, "find_display", lambda: object())
    monkeypatch.setattr(cli, "selected_gpu", lambda: next(configured_gpus))
    monkeypatch.setattr(cli, "selected_mode", lambda: "utilization")
    monkeypatch.setattr(cli, "read_utilization_snapshot", lambda _gpu: object())
    monkeypatch.setattr(sys, "argv", ["darkflash-pc-monitor", "render", "--once"])

    cli.main()

    assert reports == [utilization_frame(0, 0, 0, 0)]


def test_blank_writes_a_cleared_frame(monkeypatch) -> None:
    reports = []

    class FakeDisplay:
        def __init__(self, _node) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            pass

        def write(self, report: bytes) -> None:
            reports.append(report)

    monkeypatch.setattr(cli, "HidDisplay", FakeDisplay)
    monkeypatch.setattr(cli, "find_display", lambda: object())
    monkeypatch.setattr(sys, "argv", ["darkflash-pc-monitor", "blank"])

    cli.main()

    assert reports == [blank_frame(0)]


def test_dual_gpu_devices_uses_the_first_two_discovered_cards(monkeypatch) -> None:
    devices = [
        GpuDevice("amdgpu-pci-0a00", 60, "AMD"),
        GpuDevice("nvidia-pci-0b00", 61, "NVIDIA"),
        GpuDevice("xe-pci-0c00", 62, "Intel"),
    ]
    monkeypatch.setattr(cli, "discover_gpus", lambda: devices)

    assert cli._dual_gpu_devices() == (devices[0], devices[1])


def test_dual_gpu_devices_requires_two_cards(monkeypatch) -> None:
    monkeypatch.setattr(cli, "discover_gpus", lambda: [])

    try:
        cli._dual_gpu_devices()
    except TelemetryError as error:
        assert str(error) == "Dual GPU mode requires at least two discovered GPUs"
    else:
        raise AssertionError("expected Dual GPU mode to reject a single-GPU system")
