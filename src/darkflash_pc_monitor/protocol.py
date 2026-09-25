"""Observed DarkFlash PC Monitor HID framing and temperature-page rendering."""

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

# Each tuple identifies a TM1721 RAM word and its segment bit. The CPU digits
# occupy bits 0-2; GPU digits occupy bits 3-5.
_CPU_DIGITS = (
    ((0, 1), (2, 1), (12, 1), (10, 1), (8, 1), (4, 1)),
    ((2, 1), (12, 1)),
    ((0, 1), (2, 1), (6, 1), (8, 1), (10, 1)),
    ((0, 1), (2, 1), (6, 1), (12, 1), (10, 1)),
    ((2, 1), (12, 1), (4, 1), (6, 1)),
    ((0, 1), (12, 1), (10, 1), (4, 1), (6, 1)),
    ((0, 1), (12, 1), (10, 1), (8, 1), (4, 1), (6, 1)),
    ((0, 1), (2, 1), (12, 1)),
    ((0, 1), (2, 1), (12, 1), (10, 1), (8, 1), (4, 1), (6, 1)),
    ((0, 1), (2, 1), (12, 1), (10, 1), (4, 1), (6, 1)),
)
_CPU_TENS = (
    ((12, 2), (4, 2), (2, 2), (6, 2), (0, 2), (10, 2)),
    ((4, 2), (2, 2)),
    ((12, 2), (4, 2), (8, 2), (0, 2), (6, 2)),
    ((12, 2), (4, 2), (8, 2), (2, 2), (6, 2)),
    ((4, 2), (2, 2), (10, 2), (8, 2)),
    ((12, 2), (2, 2), (6, 2), (10, 2), (8, 2)),
    ((12, 2), (2, 2), (6, 2), (0, 2), (10, 2), (8, 2)),
    ((12, 2), (4, 2), (2, 2)),
    ((12, 2), (4, 2), (2, 2), (6, 2), (0, 2), (10, 2), (8, 2)),
    ((12, 2), (4, 2), (2, 2), (6, 2), (10, 2), (8, 2)),
)
_CPU_ONES = (
    ((2, 4), (10, 4), (4, 4), (12, 4), (8, 4), (0, 4)),
    ((10, 4), (4, 4)),
    ((2, 4), (10, 4), (6, 4), (8, 4), (12, 4)),
    ((2, 4), (10, 4), (6, 4), (4, 4), (12, 4)),
    ((10, 4), (4, 4), (0, 4), (6, 4)),
    ((2, 4), (4, 4), (12, 4), (0, 4), (6, 4)),
    ((2, 4), (4, 4), (12, 4), (8, 4), (0, 4), (6, 4)),
    ((2, 4), (10, 4), (4, 4)),
    ((2, 4), (10, 4), (4, 4), (12, 4), (8, 4), (0, 4), (6, 4)),
    ((2, 4), (10, 4), (4, 4), (12, 4), (0, 4), (6, 4)),
)

_GPU_DIGITS = (
    ((10, 1), (0, 1), (6, 1), (8, 1), (4, 1), (12, 1)),
    ((0, 1), (6, 1)),
    ((10, 1), (0, 1), (2, 1), (4, 1), (8, 1)),
    ((10, 1), (0, 1), (2, 1), (6, 1), (8, 1)),
    ((0, 1), (6, 1), (12, 1), (2, 1)),
    ((10, 1), (6, 1), (8, 1), (12, 1), (2, 1)),
    ((10, 1), (6, 1), (8, 1), (4, 1), (12, 1), (2, 1)),
    ((10, 1), (0, 1), (6, 1)),
    ((10, 1), (0, 1), (6, 1), (8, 1), (4, 1), (12, 1), (2, 1)),
    ((10, 1), (0, 1), (6, 1), (8, 1), (12, 1), (2, 1)),
)
_GPU_TENS = (
    ((4, 16), (2, 16), (12, 16), (8, 16), (10, 16), (0, 16)),
    ((2, 16), (12, 16)),
    ((4, 16), (2, 16), (6, 16), (10, 16), (8, 16)),
    ((4, 16), (2, 16), (6, 16), (12, 16), (8, 16)),
    ((2, 16), (12, 16), (0, 16), (6, 16)),
    ((4, 16), (12, 16), (8, 16), (0, 16), (6, 16)),
    ((4, 16), (12, 16), (8, 16), (10, 16), (0, 16), (6, 16)),
    ((4, 16), (2, 16), (12, 16)),
    ((4, 16), (2, 16), (12, 16), (8, 16), (10, 16), (0, 16), (6, 16)),
    ((4, 16), (2, 16), (12, 16), (8, 16), (0, 16), (6, 16)),
)
_GPU_ONES = (
    ((8, 32), (10, 32), (2, 32), (4, 32), (0, 32), (12, 32)),
    ((10, 32), (2, 32)),
    ((8, 32), (10, 32), (6, 32), (0, 32), (4, 32)),
    ((8, 32), (10, 32), (6, 32), (2, 32), (4, 32)),
    ((10, 32), (2, 32), (12, 32), (6, 32)),
    ((8, 32), (2, 32), (4, 32), (12, 32), (6, 32)),
    ((8, 32), (2, 32), (4, 32), (0, 32), (12, 32), (6, 32)),
    ((8, 32), (10, 32), (2, 32)),
    ((8, 32), (10, 32), (2, 32), (4, 32), (0, 32), (12, 32), (6, 32)),
    ((8, 32), (10, 32), (2, 32), (4, 32), (12, 32), (6, 32)),
)


def _draw_digit(bank: bytearray, digit: int, segments: tuple[tuple[tuple[int, int], ...], ...]) -> None:
    for word, mask in segments[digit]:
        bank[word] |= mask


def _draw_temperature(bank: bytearray, temperature_c: int, digits: tuple[tuple[tuple[tuple[int, int], ...], ...], ...]) -> None:
    value = max(0, min(999, temperature_c))
    hundreds, tens, ones = digits
    if value >= 100:
        _draw_digit(bank, value // 100, hundreds)
    if value >= 10:
        _draw_digit(bank, (value // 10) % 10, tens)
    _draw_digit(bank, value % 10, ones)


def temperature_frame(cpu_temperature_c: int, gpu_temperature_c: int, sequence: int) -> bytes:
    """Build the CPU/GPU temperature page report from whole-degree readings."""
    bank = bytearray(16)
    bank[1] |= 0x04
    bank[5] |= 0x02
    bank[11] |= 0x04
    bank[7] |= 0x02
    _draw_temperature(bank, cpu_temperature_c, (_CPU_DIGITS, _CPU_TENS, _CPU_ONES))
    _draw_temperature(bank, gpu_temperature_c, (_GPU_DIGITS, _GPU_TENS, _GPU_ONES))

    frame = bytearray(REPORT_SIZE)
    frame[0] = REPORT_ID
    frame[1] = sequence & 0xFF
    frame[3] = CONTROLLER_TYPE
    frame[25 : 25 + len(SETUP_BANK)] = SETUP_BANK
    frame[41 : 41 + len(bank)] = bank
    return bytes(frame)


def zero_temperature_frame(sequence: int) -> bytes:
    """Build the captured CPU/GPU 0°C vendor screen as a complete HID report."""
    return temperature_frame(0, 0, sequence)
