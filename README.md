# DarkFlash PC Monitor for Linux

Native Linux telemetry support for the DarkFlash PC Monitor segmented USB display.

## Current status

The display's Linux HID node, report size, report sequence counter, controller
setup bytes, and temperature-screen frame banks have been captured from the
vendor application. The project currently provides:

- safe discovery of the `5131:2007` display HID node;
- live CPU package and selectable Intel Xe GPU temperature discovery;
- a CLI suitable for a bar-widget dropdown or user service;
- a replay probe for the observed CPU/GPU `0°C` screen frame;
- protocol fixtures and tests derived from locally observed HID traffic.

The remaining work is translating the vendor TM1721 digit renderer into an
original native encoder. Until that encoder is complete, leave PC Monitor as
the active writer; two programs must not write to the same HID node at once.

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

## Hardware access

The display is a HID controller with USB vendor/product ID `5131:2007`.
Configure a narrow udev rule granting the active desktop user access to that
device only; do not use a broad world-writable hidraw rule.
