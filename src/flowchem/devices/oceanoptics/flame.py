"""
Ocean Optics / Ocean Insight spectrometer support.

Windows note:
- pyseabreeze needs libusb available on the DLL search path
- OceanView often locks the device, causing an access denied error here
"""

import os
import platform
import sys
import sysconfig

import numpy as np
from loguru import logger

from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.oceanoptics.flame_spectrometer import GeneralSensor
from flowchem.utils.exceptions import InvalidConfigurationError
from flowchem.utils.people import wei_hsin

try:
    import seabreeze

    HAS_SEABREEZE = True
except ImportError:
    seabreeze = None  # type: ignore[assignment]
    HAS_SEABREEZE = False


def _configure_libusb_for_windows() -> None:
    """Expose the libusb wheel DLL to pyusb on Windows."""
    if sys.platform != "win32":
        return

    arch = "x86_64" if platform.machine().lower() in {"amd64", "x86_64"} else "x86"
    libusb_dir = (
        sysconfig.get_paths()["purelib"],
        "libusb",
        "_platform",
        "windows",
        arch,
    )
    libusb_path = os.path.join(*libusb_dir)
    if not os.path.isdir(libusb_path):
        return

    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(libusb_path)
    os.environ["PATH"] = f"{libusb_path}{os.pathsep}{os.environ.get('PATH', '')}"


def _candidate_backends(requested: str | None) -> list[str]:
    env_backend = os.getenv("FLOWCHEM_OCEANOPTICS_BACKEND", "").strip().lower()
    backend = (requested or env_backend or "auto").strip().lower()

    if backend in {"cseabreeze", "pyseabreeze"}:
        return [backend]

    if sys.platform == "win32":
        return ["pyseabreeze", "cseabreeze"]

    return ["cseabreeze", "pyseabreeze"]


def _select_backend(requested: str | None) -> str:
    last_error: Exception | None = None
    _configure_libusb_for_windows()

    for backend_name in _candidate_backends(requested):
        try:
            seabreeze.use(backend_name)
            logger.info(f"Ocean Optics seabreeze backend selected: {backend_name}")
            return backend_name
        except Exception as exc:  # pragma: no cover - environment-specific
            last_error = exc
            logger.warning(
                f"Failed to activate seabreeze backend '{backend_name}': {exc}"
            )

    raise RuntimeError(
        "No usable seabreeze backend found for Ocean Optics. "
        "Set FLOWCHEM_OCEANOPTICS_BACKEND to 'pyseabreeze' or 'cseabreeze'."
    ) from last_error


def _normalize_open_error(exc: Exception) -> Exception:
    message = str(exc).lower()
    if "access denied" in message or "insufficient permissions" in message:
        return RuntimeError(
            "Ocean Optics USB access denied. Close OceanView or any other software using the "
            "spectrometer, reconnect the device, and rerun from an Administrator terminal."
        )
    return exc


class FlameOptical(FlowchemDevice):
    def __init__(
        self,
        serial_number: str | None = None,
        backend: str | None = None,
        name: str = "",
    ) -> None:
        if not HAS_SEABREEZE:
            raise InvalidConfigurationError(
                "Ocean Optics unusable: seabreeze package not installed."
            )
        self.serial_n = serial_number
        self.backend = _select_backend(backend)
        self.scans_to_average = 1
        self.trigger_mode_value: int | None = None
        super().__init__(name)

        self.device_info.authors = [wei_hsin]
        self.device_info.manufacturer = "oceanoptics"
        self.device_info.model = "python-seabreeze"
        self.device_info.additional_info["seabreeze_backend"] = self.backend

        from seabreeze.spectrometers import Spectrometer

        try:
            if self.serial_n is None:
                self.spectrometer = Spectrometer.from_first_available()
            else:
                self.spectrometer = Spectrometer.from_serial_number(self.serial_n)
        except Exception as exc:
            raise _normalize_open_error(exc) from exc

        self.model: str = self.spectrometer.model
        self.max_intensity: float = self.spectrometer.max_intensity
        self.pixels: int = self.spectrometer.pixels
        self.integration_time_micros_limits: tuple = (
            self.spectrometer.integration_time_micros_limits
        )
        self.wavelengths = self.spectrometer.wavelengths()

    async def initialize(self):
        self.components.append(GeneralSensor("spectrometer", self))

    async def power_on(self):
        self.spectrometer.open()

    async def power_off(self):
        self.spectrometer.close()

    async def get_spectrum(self):
        return self.spectrometer.spectrum()

    def _effective_scans_to_average(self, scans_to_average: int | None = None) -> int:
        scans = self.scans_to_average if scans_to_average is None else scans_to_average
        if scans < 1:
            raise ValueError("scans_to_average must be >= 1")
        return scans

    def _read_raw_intensities(self, scans_to_average: int | None = None) -> list[float]:
        scans = self._effective_scans_to_average(scans_to_average)
        if scans == 1:
            return self.spectrometer.intensities().tolist()

        samples = [self.spectrometer.intensities() for _ in range(scans)]
        return list(np.mean(np.array(samples, dtype=float), axis=0).tolist())

    async def get_intensity(
        self, absolute: bool = False, scans_to_average: int | None = None
    ):
        intensities = self._read_raw_intensities(scans_to_average)
        if absolute:
            return intensities
        return [value / self.max_intensity for value in intensities]

    async def get_wavelength(self):
        return self.wavelengths.tolist()

    async def integration_time(self, int_time: int):
        low, high = self.integration_time_micros_limits
        if low <= int_time <= high:
            self.spectrometer.integration_time_micros(int_time)
        elif int_time < low:
            logger.warning(
                "Requested integration time below device limit; using minimum value instead."
            )
            self.spectrometer.integration_time_micros(low)
        else:
            logger.warning(
                "Requested integration time above device limit; using maximum value instead."
            )
            self.spectrometer.integration_time_micros(high)

    async def set_scans_to_average(self, scans: int):
        scans = int(scans)
        if scans < 1:
            raise ValueError("scans_to_average must be >= 1")
        self.scans_to_average = scans
        return self.scans_to_average

    async def get_scans_to_average(self):
        return self.scans_to_average

    async def set_trigger_mode(self, mode: int):
        mode = int(mode)
        try:
            self.spectrometer.trigger_mode(mode)
        except AttributeError as exc:
            raise RuntimeError(
                "This Ocean Optics device/backend does not support trigger mode control."
            ) from exc
        self.trigger_mode_value = mode
        return self.trigger_mode_value

    async def get_trigger_mode(self):
        return self.trigger_mode_value
