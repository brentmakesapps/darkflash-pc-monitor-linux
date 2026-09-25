from darkflash_pc_monitor.telemetry import (
    GpuDevice,
    UtilizationSnapshot,
    _nvtop_device_for_gpu,
    discover_gpus,
    read_telemetry,
    read_utilization_snapshot,
    utilization_between,
)


def _make_xe_hwmon(root, index: int, bdf: str, temperature_mc: int) -> None:
    hwmon = root / f"hwmon{index}"
    hwmon.mkdir()
    (hwmon / "name").write_text("xe\n")
    device = root / bdf
    device.mkdir()
    (hwmon / "device").symlink_to(device)
    (hwmon / "temp2_label").write_text("pkg\n")
    (hwmon / "temp2_input").write_text(f"{temperature_mc}\n")


def _make_gpu_hwmon(root, index: int, driver: str, bdf: str, temperature_mc: int) -> None:
    hwmon = root / f"hwmon{index}"
    hwmon.mkdir()
    (hwmon / "name").write_text(f"{driver}\n")
    device = root / bdf
    device.mkdir()
    (hwmon / "device").symlink_to(device)
    (hwmon / "temp1_label").write_text("edge\n")
    (hwmon / "temp1_input").write_text(f"{temperature_mc}\n")


def test_discovers_and_selects_intel_xe_package_temperature(tmp_path) -> None:
    hwmon_root = tmp_path / "hwmon"
    hwmon_root.mkdir()
    _make_xe_hwmon(hwmon_root, 2, "0000:04:00.0", 43_000)
    _make_xe_hwmon(hwmon_root, 5, "0000:85:00.0", 52_000)
    snapshot = {
        "coretemp-isa-0000": {"Package id 0": {"temp1_input": 41.5}},
    }

    assert [device.chip for device in discover_gpus(hwmon_root=hwmon_root)] == [
        "xe-pci-0400",
        "xe-pci-8500",
    ]
    telemetry = read_telemetry("xe-pci-0400", snapshot, hwmon_root=hwmon_root)
    assert telemetry.cpu_temperature_c == 41.5
    assert telemetry.gpu.temperature_c == 43.0


def test_discovers_other_supported_gpu_hwmon_drivers(tmp_path, monkeypatch) -> None:
    hwmon_root = tmp_path / "hwmon"
    hwmon_root.mkdir()
    _make_gpu_hwmon(hwmon_root, 0, "amdgpu", "0000:0a:00.0", 60_000)
    _make_gpu_hwmon(hwmon_root, 1, "nvidia", "0000:0b:00.0", 61_000)
    monkeypatch.setattr("darkflash_pc_monitor.telemetry._pci_name", lambda bdf: bdf)

    devices = discover_gpus(hwmon_root=hwmon_root)

    assert [(device.chip, device.temperature_c) for device in devices] == [
        ("amdgpu-pci-0a00", 60.0),
        ("nvidia-pci-0b00", 61.0),
    ]


def test_discovers_generic_display_driver_with_hwmon_temperature(tmp_path, monkeypatch) -> None:
    hwmon_root = tmp_path / "hwmon"
    hwmon_root.mkdir()
    _make_gpu_hwmon(hwmon_root, 0, "customgpu", "0000:0c:00.0", 62_000)
    monkeypatch.setattr("darkflash_pc_monitor.telemetry._is_display_pci_device", lambda _bdf: True)
    monkeypatch.setattr("darkflash_pc_monitor.telemetry._pci_name", lambda bdf: bdf)

    devices = discover_gpus(hwmon_root=hwmon_root)

    assert [(device.chip, device.temperature_c) for device in devices] == [
        ("customgpu-pci-0c00", 62.0),
    ]


def test_matches_discovered_gpu_to_nvtop_name() -> None:
    gpu = GpuDevice("nvidia-pci-0b00", 61.0, "GeForce RTX 5090")
    snapshot = [{"device_name": "NVIDIA GeForce RTX 5090", "gpu_util": "75%"}]

    assert _nvtop_device_for_gpu(gpu, snapshot) == snapshot[0]


def test_prefers_the_most_specific_nvtop_name_match() -> None:
    gpu = GpuDevice("xe-pci-0400", 52.0, "Arc Pro B70")
    snapshot = [
        {"device_name": "Battlemage G31 (Arc Pro B70)"},
        {"device_name": "Battlemage G21 (Arc Pro B50)"},
    ]

    assert _nvtop_device_for_gpu(gpu, snapshot) == snapshot[0]


def test_reads_cpu_and_xe_client_utilization(tmp_path) -> None:
    proc_stat = tmp_path / "stat"
    proc_stat.write_text("cpu  100 0 50 800 50 0 0 0 0 0\n")
    fdinfo = tmp_path / "proc" / "123" / "fdinfo"
    fdinfo.mkdir(parents=True)
    (fdinfo / "5").write_text(
        "drm-driver:\txe\n"
        "drm-client-id:\t7\n"
        "drm-pdev:\t0000:04:00.0\n"
        "drm-engine-render:\t100000000 ns\n"
        "drm-engine-capacity-vcs:\t2\n"
    )
    (fdinfo / "6").write_text(
        "drm-driver:\txe\n"
        "drm-client-id:\t7\n"
        "drm-pdev:\t0000:04:00.0\n"
        "drm-engine-render:\t100000000 ns\n"
    )

    snapshot = read_utilization_snapshot(
        "xe-pci-0400",
        proc_stat=proc_stat,
        fdinfo_root=tmp_path / "proc",
        clock_ns=lambda: 1_000_000_000,
        gpu_utilization_reader=lambda _gpu: None,
        gpu_combined_reader=lambda: None,
    )

    assert snapshot.gpu_engine_ns == 100_000_000
    result = utilization_between(
        UtilizationSnapshot(0, 500, 425, 0),
        UtilizationSnapshot(1_000_000_000, 600, 475, 250_000_000),
    )
    assert result.cpu_percent == 50
    assert result.gpu_percent == 25
