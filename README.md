# DarkFlash PC Monitor for Linux

Native Linux telemetry support for the DarkFlash PC Monitor segmented USB display.

## Current status

The display's Linux HID node, report size, report sequence counter, controller
setup bytes, and temperature-screen frame banks have been captured from the
vendor application. The project currently provides:

- safe discovery of the `5131:2007` display HID node;
- live CPU package and selectable Intel Xe GPU temperature discovery;
- a CLI suitable for a bar-widget dropdown or user service;
- a native TM1721 CPU/GPU temperature-page renderer;
- protocol fixtures and tests derived from locally observed HID traffic.

The native renderer currently supports the observed CPU-left/GPU-right
temperature and utilization pages. Do not run PC Monitor at the same time:
two programs must not write to the same HID node.

## Install for development

```bash
python -m venv .venv
.venv/bin/pip install -e '.[dev]'
```

## Discover telemetry sources

```bash
darkflash-pc-monitor list-gpus
darkflash-pc-monitor telemetry --gpu xe-pci-0400
```

`xe-pci-0400` is the Intel Arc B70 on the development system. The CLI lists
all supported Intel Xe devices so a future dropdown can select either card.

## Protocol probe

The probe writes the captured `CPU 0°C / GPU 0°C` screen frame, cycling the
vendor sequence byte. It is a hardware-connection test, not a telemetry
renderer:

```bash
darkflash-pc-monitor probe --confirm
```

Close PC Monitor first. The display permits only one writer at a time.

## Render live temperatures

Render the CPU package temperature and a selected Intel Xe GPU continuously:

```bash
darkflash-pc-monitor render --gpu xe-pci-0400
```

Use `--once` to test one live frame and `--interval <seconds>` to change the
default one-second refresh cadence.

## Utilization page

Switch to the CPU/GPU utilization page with:

```bash
darkflash-pc-monitor set-mode --mode utilization
```

The left value is aggregate CPU busy time from `/proc/stat`. The right value
is the selected Intel Xe GPU's aggregate engine busy time from its DRM
per-client counters. Both values are percentages sampled over the renderer's
refresh interval. Use `set-mode --mode temperature` to return to temperatures.

## Persist a GPU selection and run at login

Select any GPU listed by `list-gpus`; the renderer and user service use this
persisted selection when no `--gpu` flag is provided:

```bash
darkflash-pc-monitor set-gpu --gpu xe-pci-0400
```

The included `systemd/darkflash-pc-monitor.service` is configured for this
repository's development virtual environment. Copy it into the user service
directory and enable it:

```bash
mkdir -p ~/.config/systemd/user
cp systemd/darkflash-pc-monitor.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now darkflash-pc-monitor.service
```

If the repository is checked out somewhere other than `~/Work`, change the
`ExecStart` path before enabling the service.

## Hardware access

The display is a HID controller with USB vendor/product ID `5131:2007`.
Configure a narrow udev rule granting the active desktop user access to that
device only; do not use a broad world-writable hidraw rule.
