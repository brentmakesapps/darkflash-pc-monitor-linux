from darkflash_pc_monitor.protocol import (
    CONTROLLER_TYPE,
    REPORT_ID,
    SETUP_BANK,
    ZERO_TEMPERATURE_BANK,
    blank_frame,
    temperature_frame,
    utilization_frame,
    zero_temperature_frame,
)


def test_zero_temperature_frame_matches_observed_report_shape() -> None:
    frame = zero_temperature_frame(0xA6)

    assert len(frame) == 65
    assert frame[0] == REPORT_ID
    assert frame[1] == 0xA6
    assert frame[3] == CONTROLLER_TYPE
    assert frame[25 : 25 + len(SETUP_BANK)] == SETUP_BANK
    assert frame[41 : 41 + len(ZERO_TEMPERATURE_BANK)] == ZERO_TEMPERATURE_BANK
    assert frame[54:57] == b"\0\0\0"


def test_temperature_frame_renders_cpu_left_and_gpu_right() -> None:
    frame = temperature_frame(42, 57, 0xA6)

    assert frame[41:54] == bytes(
        [0x10, 0x04, 0x26, 0x00, 0x12, 0x02, 0x14, 0x02, 0x36, 0x00, 0x26, 0x04, 0x14]
    )


def test_blank_frame_clears_the_complete_display_bank() -> None:
    frame = blank_frame(0xA6)

    assert frame[1] == 0xA6
    assert frame[25 : 25 + len(SETUP_BANK)] == SETUP_BANK
    assert frame[41:57] == b"\0" * 16


def test_utilization_frame_matches_recovered_vendor_renderer() -> None:
    frame = utilization_frame(51, 19, 19, 0xA6)

    assert frame[0] == REPORT_ID
    assert frame[1] == 0xA6
    assert frame[3] == CONTROLLER_TYPE
    assert frame[25 : 25 + len(SETUP_BANK)] == SETUP_BANK
    assert frame[41:57] == bytes.fromhex("00073204240462046205660672000000")
