from darkflash_pc_monitor.config import save_selected_gpu, selected_gpu


def test_save_and_read_selected_gpu(tmp_path) -> None:
    path = tmp_path / "config.json"

    assert selected_gpu(path) is None
    save_selected_gpu("xe-pci-0400", path)

    assert selected_gpu(path) == "xe-pci-0400"
