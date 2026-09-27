# DarkFlash L280 PC Monitor for Linux

A native Linux replacement for the Windows **PC Monitor** application used by
the small segmented display integrated into the
[DarkFlash L280](https://www.darkflash.com/product/l280) PC case.

The case display is a USB HID device, not a conventional monitor. This project
reads local CPU and Intel Xe GPU telemetry and writes the display directly,
without Wine or the vendor application. It is intended for the L280 hardware
observed during development; it is not an official DarkFlash project.

> **One writer only:** never run this renderer and the vendor PC Monitor
> application at the same time. Both write to the same HID device.

## Features

- CPU package and GPU temperatures from `lm-sensors` and sysfs.
- CPU utilization from `/proc/stat`.
- GPU utilization and memory use from `nvtop`'s JSON snapshot output.
- Temperature, utilization, automatic page rotation, and blank display modes.
- Celsius or Fahrenheit temperature display.
- GPU selection by detected card name.
- Combined-GPU average mode.
- Dual-GPU mode, showing the first two discovered PCI GPUs from left to right;
  CPU label segments are intentionally cleared in this layout.
- A complete blank frame on service stop, including shutdown.

The renderer communicates with a device observed as USB `5131:2007`. Its
TM1721-compatible segment mapping was recovered from locally captured vendor
HID traffic. The report layout is therefore specific to this display.

## Requirements

- Python 3.11 or later
- `lm-sensors` (`sensors -j`)
- `nvtop` for current GPU utilization and memory percentages
- `pciutils` (`lspci`) for readable GPU names
- Access to the display's `/dev/hidraw*` device

Create a narrow udev rule for USB `5131:2007` that grants the desktop user
access to this device. Do not make all hidraw devices world-writable.

## Development setup

```bash
git clone <repository-url> dark-flash-pc-monitor-linux
cd dark-flash-pc-monitor-linux
python -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/pytest -q
```

All examples below assume the editable install is active. Substitute
`.venv/bin/darkflash-pc-monitor` when it is not on `PATH`.

## Discover and select a GPU

```bash
darkflash-pc-monitor list-gpus
darkflash-pc-monitor set-gpu --gpu xe-pci-0400
darkflash-pc-monitor selected-gpu
```

`list-gpus` returns stable `<driver>-pci-XXXX` identifiers along with card
names and temperatures. On the development system, `xe-pci-0400` is an Arc
Pro B70 and `xe-pci-8500` is an Arc Pro B50.

Intel Xe is the verified implementation. NVIDIA (`nvidia`/`nouveau`), AMD
(`amdgpu`), Intel i915, and comparable PCI GPU drivers are discovered when
they expose a hwmon temperature sensor, are identified by `lspci` as display
adapters, and can be matched to an `nvtop` device. These paths are
**unverified**: please treat their readings and segment output as experimental
until tested on the target hardware.

Two special selections are also available:

```bash
darkflash-pc-monitor set-gpu --gpu combined  # Average all discovered GPUs
darkflash-pc-monitor set-gpu --gpu dual      # B70 left, B50 right
```

Dual mode uses the first two detected GPUs in PCI order, with the first on the
left and second on the right. It requires at least two discovered cards.

## Display modes and options

The renderer reads preferences from
`~/.config/darkflash-pc-monitor/config.json` on every refresh, so changes take
effect without restarting the service.

```bash
# Static temperature or utilization page
darkflash-pc-monitor set-mode --mode temperature
darkflash-pc-monitor set-mode --mode utilization

# Alternate pages every five seconds, starting on utilization
darkflash-pc-monitor set-auto-display --interval 5 --start utilization

# Clear the display while leaving the renderer available for later changes
darkflash-pc-monitor set-mode --mode disabled

# Select Celsius or Fahrenheit
darkflash-pc-monitor set-temperature-unit --unit fahrenheit

# Choose independent GPU metrics for the utilization-page digits and bar
darkflash-pc-monitor set-gpu-display --digits memory --bar utilization
```

In ordinary utilization mode, the left side shows CPU load and the right side
shows the selected GPU. In Dual GPU mode, both sides follow the digits/bar
metric choice independently. Combined mode uses an average across all
discovered GPUs.

## Run it

For a foreground test:

```bash
darkflash-pc-monitor render --gpu xe-pci-0400
```

Omit `--gpu` to use the saved selection. `--once` emits one frame and exits;
`--interval <seconds>` changes the default one-second refresh interval.

`probe --confirm` writes a known `0°C / 0°C` temperature frame. Use it only as
a hardware connection test after closing the vendor application:

```bash
darkflash-pc-monitor probe --confirm
```

To blank the display manually:

```bash
darkflash-pc-monitor blank
```

## System service

`systemd/darkflash-pc-monitor@.service` is a system-wide, per-user service
template that starts before graphical login and blanks the display in
`ExecStopPost`. It contains no machine-specific path or username. Its
per-installation executable path is supplied through an environment file.

```bash
user="$(id -un)"
sudo install -Dm644 systemd/darkflash-pc-monitor@.service \
  /etc/systemd/system/darkflash-pc-monitor@.service
sudo install -Dm644 systemd/darkflash-pc-monitor.env.example \
  "/etc/darkflash-pc-monitor/${user}.conf"
sudoedit "/etc/darkflash-pc-monitor/${user}.conf"
sudo systemctl daemon-reload
sudo systemctl enable --now "darkflash-pc-monitor@${user}.service"
```

Set `DARKFLASH_PC_MONITOR` in the environment file to the absolute executable
path for this installation. After changing Python source, restart the matching
service instance:

```bash
sudo systemctl restart "darkflash-pc-monitor@$(id -un).service"
```

`systemd/darkflash-pc-monitor.service` is an optional per-user
graphical-session template. It reads the same variable from
`~/.config/darkflash-pc-monitor/service.env`. Do **not** enable it alongside
the system service: two concurrent renderers will conflict over the HID device.

## Project layout

| Path | Purpose |
| --- | --- |
| `src/darkflash_pc_monitor/protocol.py` | HID report and segment rendering |
| `src/darkflash_pc_monitor/telemetry.py` | CPU, GPU, nvtop, and sysfs telemetry |
| `src/darkflash_pc_monitor/cli.py` | CLI and persistent render loop |
| `src/darkflash_pc_monitor/config.py` | Atomic preference persistence |
| `systemd/` | User and system service templates |
| `tests/` | Protocol, telemetry, configuration, and CLI tests |
