from darkflash_pc_monitor.telemetry import discover_gpus, read_telemetry


def _make_xe_hwmon(root, index: int, bdf: str, temperature_mc: int) -> None:
    hwmon = root / f"hwmon{index}"
    hwmon.mkdir()
    (hwmon / "name").write_text("xe\n")
    device = root / bdf
    device.mkdir()
    (hwmon / "device").symlink_to(device)
    (hwmon / "temp2_label").write_text("pkg\n")
    (hwmon / "temp2_input").write_text(f"{temperature_mc}\n")


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
