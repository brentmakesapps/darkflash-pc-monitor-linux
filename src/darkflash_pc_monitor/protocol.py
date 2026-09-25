"""Observed DarkFlash PC Monitor HID framing.

This module intentionally contains only behavior established by local capture:
the 65-byte report shape, report ID, rolling sequence byte, controller setup,
and the vendor's zero-temperature screen. Dynamic TM1721 digit rendering is
implemented separately once its original encoder has matching test vectors.
"""

from __future__ import annotations

from .hid import REPORT_SIZE

REPORT_ID = 0x00
CONTROLLER_TYPE = 0x02
SETUP_BANK = bytes(
    [0xFD, 0x08, 0x08, 0x08, 0xFD, 0x08, 0xDD, 0x0F, 0xD0, 0xDF, 0x8F]
)
ZERO_TEMPERATURE_BANK = bytes(
    [0x24, 0x04, 0x24, 0x00, 0x24, 0x02, 0x00, 0x02, 0x24, 0x00, 0x24, 0x04, 0x24]
)


def zero_temperature_frame(sequence: int) -> bytes:
    """Build the captured CPU/GPU 0°C vendor screen as a complete HID report."""
    frame = bytearray(REPORT_SIZE)
    frame[0] = REPORT_ID
    frame[1] = sequence & 0xFF
    frame[3] = CONTROLLER_TYPE
    frame[25 : 25 + len(SETUP_BANK)] = SETUP_BANK
    frame[41 : 41 + len(ZERO_TEMPERATURE_BANK)] = ZERO_TEMPERATURE_BANK
    return bytes(frame)
