"""Command-line interface for discovery and safe protocol probes."""

from __future__ import annotations

import argparse
import json

from .hid import HidDisplay, find_display
from .protocol import zero_temperature_frame
from .telemetry import TelemetryError, discover_gpus, read_telemetry, sensors_snapshot


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("list-gpus", help="list Intel Xe GPU temperature sources")
    telemetry = subcommands.add_parser("telemetry", help="read selected live telemetry")
    telemetry.add_argument("--gpu", required=True, help="lm-sensors Xe chip name")
    probe = subcommands.add_parser("probe", help="write the captured 0°C vendor frame once")
    probe.add_argument("--confirm", action="store_true", help="permit a HID write")
    return parser


def main() -> None:
    args = _parser().parse_args()
    try:
        if args.command == "list-gpus":
            print(json.dumps([device.__dict__ for device in discover_gpus(sensors_snapshot())]))
            return
        if args.command == "telemetry":
            telemetry = read_telemetry(args.gpu)
            print(
                json.dumps(
                    {
                        "cpu_temperature_c": telemetry.cpu_temperature_c,
                        "gpu_chip": telemetry.gpu.chip,
                        "gpu_temperature_c": telemetry.gpu.temperature_c,
                    }
                )
            )
            return
        if not args.confirm:
            raise SystemExit("probe writes to the display; re-run with --confirm")
        with HidDisplay(find_display()) as display:
            display.write(zero_temperature_frame(0))
    except TelemetryError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
