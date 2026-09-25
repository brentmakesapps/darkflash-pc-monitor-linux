"""Command-line interface for discovery and safe protocol probes."""

from __future__ import annotations

import argparse
import json
import time

from .config import (
    save_selected_gpu,
    save_selected_mode,
    selected_gpu,
    selected_mode,
)
from .hid import HidDisplay, find_display
from .protocol import temperature_frame, zero_temperature_frame
from .telemetry import (
    TelemetryError,
    discover_gpus,
    read_telemetry,
    read_utilization_snapshot,
    sensors_snapshot,
    utilization_between,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("list-gpus", help="list Intel Xe GPU temperature sources")
    telemetry = subcommands.add_parser("telemetry", help="read selected live telemetry")
    telemetry.add_argument("--gpu", required=True, help="lm-sensors Xe chip name")
    probe = subcommands.add_parser("probe", help="write the captured 0°C vendor frame once")
    probe.add_argument("--confirm", action="store_true", help="permit a HID write")
    render = subcommands.add_parser("render", help="continuously render live CPU and GPU temperatures")
    render.add_argument("--gpu", help="Intel Xe GPU temperature source")
    render.add_argument("--interval", type=float, default=1.0, help="refresh interval in seconds")
    render.add_argument("--once", action="store_true", help="write one live frame, then exit")
    set_gpu = subcommands.add_parser("set-gpu", help="select the GPU used by the native service")
    set_gpu.add_argument("--gpu", required=True, help="Intel Xe GPU temperature source")
    subcommands.add_parser("selected-gpu", help="print the persisted GPU selection")
    set_mode = subcommands.add_parser("set-mode", help="select the display page")
    set_mode.add_argument("--mode", choices=("temperature", "utilization"), required=True)
    subcommands.add_parser("selected-mode", help="print the persisted display page")
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
        if args.command == "selected-gpu":
            gpu = selected_gpu()
            if gpu is None:
                raise SystemExit("no GPU is selected; run set-gpu --gpu <chip>")
            print(gpu)
            return
        if args.command == "set-gpu":
            available = {device.chip for device in discover_gpus(sensors_snapshot())}
            if args.gpu not in available:
                choices = ", ".join(sorted(available)) or "none"
                raise SystemExit(f"GPU {args.gpu!r} was not found; available: {choices}")
            save_selected_gpu(args.gpu)
            return
        if args.command == "selected-mode":
            print(selected_mode())
            return
        if args.command == "set-mode":
            save_selected_mode(args.mode)
            return
        if args.command == "probe":
            if not args.confirm:
                raise SystemExit("probe writes to the display; re-run with --confirm")
            with HidDisplay(find_display()) as display:
                display.write(zero_temperature_frame(0))
            return
        if args.interval <= 0:
            raise SystemExit("--interval must be greater than zero")
        gpu = args.gpu or selected_gpu()
        if gpu is None:
            raise SystemExit("no GPU is selected; pass --gpu or run set-gpu --gpu <chip>")
        with HidDisplay(find_display()) as display:
            sequence = 0
            utilization_snapshot = None
            while True:
                if selected_mode() == "utilization":
                    next_snapshot = read_utilization_snapshot(gpu)
                    if utilization_snapshot is None:
                        cpu_value = gpu_value = 0
                    else:
                        utilization = utilization_between(utilization_snapshot, next_snapshot)
                        cpu_value = round(utilization.cpu_percent)
                        gpu_value = round(utilization.gpu_percent)
                    utilization_snapshot = next_snapshot
                else:
                    telemetry = read_telemetry(gpu)
                    cpu_value = round(telemetry.cpu_temperature_c)
                    gpu_value = round(telemetry.gpu.temperature_c)
                display.write(
                    temperature_frame(
                        cpu_value,
                        gpu_value,
                        sequence,
                    )
                )
                if args.once:
                    return
                sequence = (sequence + 1) & 0xFF
                time.sleep(args.interval)
    except TelemetryError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
