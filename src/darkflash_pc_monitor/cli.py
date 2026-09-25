"""Command-line interface for discovery and safe protocol probes."""

from __future__ import annotations

import argparse
import json
import time

from .config import (
    save_selected_gpu,
    save_selected_gpu_display,
    save_selected_auto_display,
    save_selected_temperature_unit,
    save_selected_mode,
    selected_gpu,
    selected_gpu_display,
    selected_auto_display,
    selected_temperature_unit,
    selected_mode,
)
from .hid import HidDisplay, find_display
from .protocol import (
    blank_frame,
    dual_gpu_temperature_frame,
    dual_gpu_utilization_frame,
    temperature_frame,
    utilization_frame,
    zero_temperature_frame,
)
from .telemetry import (
    GpuDevice,
    TelemetryError,
    discover_gpus,
    read_combined_telemetry,
    read_gpu_metrics,
    read_telemetry,
    read_utilization_snapshot,
    sensors_snapshot,
    utilization_between,
)


def _dual_gpu_devices() -> tuple[GpuDevice, GpuDevice]:
    """Return the first two discovered GPUs in stable PCI order."""
    devices = discover_gpus()
    if len(devices) < 2:
        raise TelemetryError("Dual GPU mode requires at least two discovered GPUs")
    return devices[0], devices[1]


def _reference_gpu_chip() -> str:
    """Return a discovered GPU for CPU/utilization interval bookkeeping."""
    devices = discover_gpus()
    if not devices:
        raise TelemetryError("no GPU temperature sources were found")
    return devices[0].chip


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("list-gpus", help="list Intel Xe GPU temperature sources")
    telemetry = subcommands.add_parser("telemetry", help="read selected live telemetry")
    telemetry.add_argument("--gpu", required=True, help="lm-sensors Xe chip name")
    probe = subcommands.add_parser("probe", help="write the captured 0°C vendor frame once")
    probe.add_argument("--confirm", action="store_true", help="permit a HID write")
    subcommands.add_parser("blank", help="clear every display segment once")
    render = subcommands.add_parser("render", help="continuously render the selected live CPU/GPU display page")
    render.add_argument("--gpu", help="Intel Xe GPU temperature source")
    render.add_argument("--interval", type=float, default=1.0, help="refresh interval in seconds")
    render.add_argument("--once", action="store_true", help="write one live frame, then exit")
    set_gpu = subcommands.add_parser("set-gpu", help="select the GPU used by the native service")
    set_gpu.add_argument("--gpu", required=True, help="Intel Xe GPU temperature source")
    subcommands.add_parser("selected-gpu", help="print the persisted GPU selection")
    set_mode = subcommands.add_parser("set-mode", help="select the display page")
    set_mode.add_argument("--mode", choices=("temperature", "utilization", "auto", "disabled"), required=True)
    auto = subcommands.add_parser("set-auto-display", help="configure and activate automatic page rotation")
    auto.add_argument("--interval", type=int, required=True, help="seconds per page")
    auto.add_argument("--start", choices=("temperature", "utilization"), required=True)
    subcommands.add_parser("selected-mode", help="print the persisted display page")
    subcommands.add_parser("selected-gpu-display", help="print persisted GPU digit and bar metrics")
    subcommands.add_parser("selected-temperature-unit", help="print persisted temperature unit")
    temperature_unit = subcommands.add_parser("set-temperature-unit", help="select display temperature unit")
    temperature_unit.add_argument("--unit", choices=("celsius", "fahrenheit"), required=True)
    gpu_display = subcommands.add_parser("set-gpu-display", help="select GPU digit and bar metrics")
    gpu_display.add_argument("--digits", choices=("utilization", "memory"), required=True)
    gpu_display.add_argument("--bar", choices=("utilization", "memory"), required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    try:
        if args.command == "list-gpus":
            print(json.dumps([device.__dict__ for device in discover_gpus(sensors_snapshot())]))
            return
        if args.command == "telemetry":
            telemetry = read_combined_telemetry() if args.gpu == "combined" else read_telemetry(args.gpu)
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
            available = {device.chip for device in discover_gpus(sensors_snapshot())} | {"combined", "dual"}
            if args.gpu not in available:
                choices = ", ".join(sorted(available)) or "none"
                raise SystemExit(f"GPU {args.gpu!r} was not found; available: {choices}")
            save_selected_gpu(args.gpu)
            return
        if args.command == "selected-mode":
            print(selected_mode())
            return
        if args.command == "selected-gpu-display":
            digits, bar = selected_gpu_display()
            print(json.dumps({"digits": digits, "bar": bar}))
            return
        if args.command == "selected-temperature-unit":
            print(selected_temperature_unit())
            return
        if args.command == "set-temperature-unit":
            save_selected_temperature_unit(args.unit)
            return
        if args.command == "set-mode":
            save_selected_mode(args.mode)
            return
        if args.command == "set-auto-display":
            save_selected_auto_display(args.interval, args.start)
            return
        if args.command == "set-gpu-display":
            save_selected_gpu_display(args.digits, args.bar)
            return
        if args.command == "probe":
            if not args.confirm:
                raise SystemExit("probe writes to the display; re-run with --confirm")
            with HidDisplay(find_display()) as display:
                display.write(zero_temperature_frame(0))
            return
        if args.command == "blank":
            with HidDisplay(find_display()) as display:
                display.write(blank_frame(0))
            return
        if args.interval <= 0:
            raise SystemExit("--interval must be greater than zero")
        configured_gpu = args.gpu
        if configured_gpu is None and selected_gpu() is None:
            raise SystemExit("no GPU is selected; pass --gpu or run set-gpu --gpu <chip>")
        with HidDisplay(find_display()) as display:
            sequence = 0
            utilization_snapshot = None
            auto_started = time.monotonic()
            previous_mode = None
            previous_gpu = None
            while True:
                # The GUI updates this setting while the persistent renderer runs.
                gpu = configured_gpu or selected_gpu()
                if gpu is None:
                    raise SystemExit("no GPU is selected; pass --gpu or run set-gpu --gpu <chip>")
                if gpu != previous_gpu:
                    utilization_snapshot = None
                    previous_gpu = gpu
                mode = selected_mode()
                if mode == "auto":
                    interval, first_page = selected_auto_display()
                    pages = (first_page, "temperature" if first_page == "utilization" else "utilization")
                    mode = pages[int((time.monotonic() - auto_started) / interval) % 2]
                if mode == "disabled":
                    if previous_mode != "disabled":
                        display.write(blank_frame(sequence))
                    previous_mode = "disabled"
                    time.sleep(args.interval)
                    continue
                if gpu == "dual":
                    left_gpu, right_gpu = _dual_gpu_devices()
                    if mode == "utilization":
                        left_util, left_memory = read_gpu_metrics(left_gpu.chip)
                        right_util, right_memory = read_gpu_metrics(right_gpu.chip)
                        digits, bar = selected_gpu_display()
                        left_digit = left_memory if digits == "memory" else left_util
                        left_bar = left_memory if bar == "memory" else left_util
                        right_digit = right_memory if digits == "memory" else right_util
                        right_bar = right_memory if bar == "memory" else right_util
                        frame = dual_gpu_utilization_frame(
                            round(left_digit or 0), round(left_bar or 0),
                            round(right_digit or 0), round(right_bar or 0), sequence
                        )
                    else:
                        left = left_gpu.temperature_c
                        right = right_gpu.temperature_c
                        unit = selected_temperature_unit()
                        if unit == "fahrenheit":
                            left, right = left * 9 / 5 + 32, right * 9 / 5 + 32
                        frame = dual_gpu_temperature_frame(round(left), round(right), sequence, unit)
                    display.write(frame)
                    previous_mode = mode
                    if args.once:
                        return
                    sequence = (sequence + 1) & 0xFF
                    time.sleep(args.interval)
                    continue
                if mode == "utilization":
                    telemetry_gpu = _reference_gpu_chip() if gpu == "combined" else gpu
                    next_snapshot = read_utilization_snapshot(telemetry_gpu)
                    if utilization_snapshot is None:
                        cpu_value = gpu_value = gpu_bar_value = 0
                    else:
                        utilization = utilization_between(utilization_snapshot, next_snapshot)
                        cpu_value = round(utilization.cpu_percent)
                        digits, bar = selected_gpu_display()
                        def gpu_metric(source):
                            if source == "memory":
                                return next_snapshot.gpu_memory_percent
                            return utilization.gpu_percent
                        if gpu == "combined":
                            gpu_value = gpu_bar_value = round(
                                next_snapshot.gpu_combined_percent
                                if next_snapshot.gpu_combined_percent is not None
                                else utilization.gpu_percent
                            )
                        else:
                            gpu_value = round(
                                gpu_metric(digits)
                                if gpu_metric(digits) is not None
                                else utilization.gpu_percent
                            )
                            gpu_bar_value = round(
                                gpu_metric(bar)
                                if gpu_metric(bar) is not None
                                else utilization.gpu_percent
                            )
                    utilization_snapshot = next_snapshot
                else:
                    telemetry = read_combined_telemetry() if gpu == "combined" else read_telemetry(gpu)
                    cpu_value = round(telemetry.cpu_temperature_c)
                    gpu_value = round(telemetry.gpu.temperature_c)
                    unit = selected_temperature_unit()
                    if unit == "fahrenheit":
                        cpu_value = round(cpu_value * 9 / 5 + 32)
                        gpu_value = round(gpu_value * 9 / 5 + 32)
                frame = (
                    utilization_frame(cpu_value, gpu_value, gpu_bar_value, sequence)
                    if mode == "utilization"
                    else temperature_frame(cpu_value, gpu_value, sequence, unit)
                )
                display.write(frame)
                previous_mode = mode
                if args.once:
                    return
                sequence = (sequence + 1) & 0xFF
                time.sleep(args.interval)
    except TelemetryError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
