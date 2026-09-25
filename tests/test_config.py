from darkflash_pc_monitor.config import (
    save_selected_auto_display,
    save_selected_gpu_display,
    save_selected_gpu,
    save_selected_mode,
    save_selected_temperature_unit,
    selected_gpu,
    selected_auto_display,
    selected_gpu_display,
    selected_mode,
    selected_temperature_unit,
)


def test_save_and_read_selected_gpu(tmp_path) -> None:
    path = tmp_path / "config.json"

    assert selected_gpu(path) is None
    save_selected_gpu("xe-pci-0400", path)

    assert selected_gpu(path) == "xe-pci-0400"
    assert selected_mode(path) == "temperature"
    save_selected_mode("utilization", path)
    assert selected_gpu(path) == "xe-pci-0400"
    assert selected_mode(path) == "utilization"
    save_selected_auto_display(5, "utilization", path)
    assert selected_mode(path) == "auto"
    assert selected_auto_display(path) == (5, "utilization")
    save_selected_gpu_display("utilization", "memory", path)
    save_selected_temperature_unit("fahrenheit", path)
    save_selected_mode("temperature", path)

    assert selected_auto_display(path) == (5, "utilization")
    assert selected_gpu_display(path) == ("utilization", "memory")
    assert selected_temperature_unit(path) == "fahrenheit"
