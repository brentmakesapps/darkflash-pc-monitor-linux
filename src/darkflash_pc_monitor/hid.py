"""Narrow, stdlib-only hidraw access for the display controller."""

from __future__ import annotations

import errno
import os
from dataclasses import dataclass
from pathlib import Path

VENDOR_ID = 0x5131
PRODUCT_ID = 0x2007
REPORT_SIZE = 65


class HidError(RuntimeError):
    """The configured display cannot be found or opened."""


@dataclass(frozen=True)
class HidNode:
    path: Path
    vendor_id: int
    product_id: int


def find_display(
    vendor_id: int = VENDOR_ID,
    product_id: int = PRODUCT_ID,
    *,
    sysfs: Path = Path("/sys/bus/hid/devices"),
) -> HidNode:
    """Find the display's hidraw node without relying on its dynamic number."""
    for device in sorted(sysfs.iterdir(), key=lambda entry: entry.name):
        try:
            uevent = (device / "uevent").read_text()
            hid_id = next(
                line.removeprefix("HID_ID=")
                for line in uevent.splitlines()
                if line.startswith("HID_ID=")
            )
            _, vendor, product = hid_id.split(":")
            if (int(vendor, 16), int(product, 16)) != (vendor_id, product_id):
                continue
            hidraw = next((device / "hidraw").iterdir())
        except (FileNotFoundError, StopIteration, ValueError):
            continue
        return HidNode(Path("/dev") / hidraw.name, vendor_id, product_id)
    raise HidError(
        f"display {vendor_id:#06x}:{product_id:#06x} was not found on hidraw"
    )


class HidDisplay:
    """A display endpoint that accepts complete, unnumbered-or-numbered reports."""

    def __init__(self, node: HidNode) -> None:
        self._node = node
        try:
            self._fd = os.open(node.path, os.O_RDWR)
        except OSError as exc:
            if exc.errno in (errno.EACCES, errno.EPERM):
                raise HidError(
                    f"permission denied opening {node.path}; install a narrow "
                    "udev rule for USB ID 5131:2007"
                ) from exc
            raise HidError(f"cannot open {node.path}: {exc.strerror}") from exc

    def write(self, report: bytes) -> None:
        """Write one vendor report and reject truncated writes."""
        if len(report) != REPORT_SIZE:
            raise ValueError(f"expected {REPORT_SIZE}-byte report, got {len(report)}")
        written = os.write(self._fd, report)
        if written != len(report):
            raise HidError(f"short write to {self._node.path}: {written} bytes")

    def close(self) -> None:
        os.close(self._fd)

    def __enter__(self) -> "HidDisplay":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
