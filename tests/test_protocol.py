from darkflash_pc_monitor.protocol import (
    CONTROLLER_TYPE,
    REPORT_ID,
    SETUP_BANK,
    ZERO_TEMPERATURE_BANK,
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
