from darkflash_pc_monitor.config import (
    save_selected_gpu,
    save_selected_mode,
    selected_gpu,
    selected_mode,
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
