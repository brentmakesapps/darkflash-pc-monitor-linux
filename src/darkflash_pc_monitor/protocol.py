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



def _vendor_utilization_bank(
    cpu_percent: int, cpu_bar_percent: int, gpu_digit_percent: int, gpu_bar_percent: int
) -> bytes:
    """Reproduce PC Monitor's final TM1721_show4 utilization renderer."""
    bank = bytearray(16)
    cpu_value = max(0, min(100, cpu_percent))
    gpu_digit_value = max(0, min(100, gpu_digit_percent))
    gpu_bar_value = max(0, min(100, gpu_bar_percent))
    _draw_temperature(bank, cpu_value, (_CPU_DIGITS, _CPU_TENS, _CPU_ONES))
    gpu_hundreds = tuple(tuple((word, 0x08) for word, _ in digit) for digit in _GPU_DIGITS)
    _draw_temperature(bank, gpu_digit_value, (gpu_hundreds, _GPU_TENS, _GPU_ONES))
    for word in (1, 3, 5, 7, 9, 11):
        bank[word] |= 0x04
    bank[1] |= 0x02
    bank[11] |= 0x02
    cpu_bar = ((6, 0x40), (8, 0x40), (10, 0x40), (12, 0x40), (1, 0x01),
               (5, 0x01), (3, 0x01), (2, 0x40), (4, 0x40), (0, 0x40))
    gpu_bar = ((9, 0x01), (11, 0x01), (0, 0x80), (2, 0x80), (4, 0x80),
               (7, 0x01), (12, 0x80), (10, 0x80), (8, 0x80), (6, 0x80))
    for word, mask in cpu_bar[: max(0, min(100, cpu_bar_percent)) // 10]:
        bank[word] |= mask
    for word, mask in gpu_bar[: gpu_bar_value // 10]:
        bank[word] |= mask
    return bytes(bank)


def utilization_frame(
    cpu_percent: int,
    gpu_digit_percent: int,
    gpu_bar_percent: int,
    sequence: int,
) -> bytes:
    """Build the vendor-derived CPU telemetry and utilization page report."""
    bank = _vendor_utilization_bank(cpu_percent, cpu_percent, gpu_digit_percent, gpu_bar_percent)

    frame = bytearray(REPORT_SIZE)
    frame[0] = REPORT_ID
    frame[1] = sequence & 0xFF
    frame[3] = CONTROLLER_TYPE
    frame[25 : 25 + len(SETUP_BANK)] = SETUP_BANK
    frame[41 : 41 + len(bank)] = bank
    return bytes(frame)


def temperature_frame(cpu_temperature: int, gpu_temperature: int, sequence: int, unit: str = "celsius") -> bytes:
    """Build the CPU/GPU temperature page report in the requested unit."""
    bank = bytearray(16)
    bank[1] |= 0x04
    bank[11] |= 0x04
    if unit == "fahrenheit":
        bank[3] |= 0x02
        bank[9] |= 0x02
    else:
        bank[5] |= 0x02
        bank[7] |= 0x02
    _draw_temperature(bank, cpu_temperature, (_CPU_DIGITS, _CPU_TENS, _CPU_ONES))
    _draw_temperature(bank, gpu_temperature, (_GPU_DIGITS, _GPU_TENS, _GPU_ONES))

    frame = bytearray(REPORT_SIZE)
    frame[0] = REPORT_ID
    frame[1] = sequence & 0xFF
    frame[3] = CONTROLLER_TYPE
    frame[25 : 25 + len(SETUP_BANK)] = SETUP_BANK
    frame[41 : 41 + len(bank)] = bank
    return bytes(frame)


def dual_gpu_temperature_frame(left_temperature: int, right_temperature: int, sequence: int, unit: str = "celsius") -> bytes:
    """Build a dual-GPU temperature report with the CPU label segments cleared."""
    bank = bytearray(16)
    bank[11] |= 0x04
    if unit == "fahrenheit":
        bank[9] |= 0x02
    else:
        bank[7] |= 0x02
    _draw_temperature(bank, left_temperature, (_CPU_DIGITS, _CPU_TENS, _CPU_ONES))
    _draw_temperature(bank, right_temperature, (_GPU_DIGITS, _GPU_TENS, _GPU_ONES))
    frame = bytearray(REPORT_SIZE)
    frame[0] = REPORT_ID
    frame[1] = sequence & 0xFF
    frame[3] = CONTROLLER_TYPE
    frame[25 : 25 + len(SETUP_BANK)] = SETUP_BANK
    frame[41 : 41 + len(bank)] = bank
    return bytes(frame)


def dual_gpu_utilization_frame(
    left_digit_percent: int, left_bar_percent: int, right_digit_percent: int, right_bar_percent: int, sequence: int
) -> bytes:
    """Build a dual-GPU utilization report with CPU text segments cleared."""
    bank = bytearray(
        _vendor_utilization_bank(left_digit_percent, left_bar_percent, right_digit_percent, right_bar_percent)
    )
    for word in (1, 3, 5):
        bank[word] &= ~0x04
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


def blank_frame(sequence: int) -> bytes:
    """Build a complete report with every TM1721 display segment cleared."""
    frame = bytearray(REPORT_SIZE)
    frame[0] = REPORT_ID
    frame[1] = sequence & 0xFF
    frame[3] = CONTROLLER_TYPE
    frame[25 : 25 + len(SETUP_BANK)] = SETUP_BANK
    return bytes(frame)
