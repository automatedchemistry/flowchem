# Ocean Optics Spectrometer
```{admonition} Additional software needed!
:class: attention

To control an Ocean Optics / Ocean Insight spectrometer, the `seabreeze` package (`python-seabreeze` on PyPI) must
be installed separately, as it is not a `flowchem` dependency.
A libusb driver must also be available for the spectrometer's USB device: on Windows this typically means
installing a WinUSB/libusb-win32 driver for the device (e.g. via [Zadig](https://zadig.akeo.ie/)).
Additionally, the manufacturer software (OceanView) locks the device while running, so it must be closed before
`flowchem` attempts to open the spectrometer, otherwise an access-denied error is raised.
```

## Introduction
The `FlameOptical` class controls Ocean Optics / Ocean Insight USB spectrometers (e.g. Flame) via the
`python-seabreeze` library, which can use either the `cseabreeze` or `pyseabreeze` backend.
`flowchem` automatically selects a working backend, preferring `pyseabreeze` on Windows.
The device exposes a `PhotoSensor` component that can acquire spectra/intensities, read the wavelength axis,
and configure integration time, scan averaging, and trigger mode.

## Configuration
Configuration sample showing all possible parameters:

```toml
[device.my-spectrometer]  # This is the device identifier
type = "FlameOptical"
serial_number = "FLMS12345"  # Optional; if omitted, the first available spectrometer is used
backend = "auto"             # Optional: "auto" (default), "cseabreeze", or "pyseabreeze"
```

```{note} Backend selection
The backend can also be forced globally via the `FLOWCHEM_OCEANOPTICS_BACKEND` environment variable, which is
used whenever the `backend` parameter is omitted (i.e. left at its `"auto"` default).
```
