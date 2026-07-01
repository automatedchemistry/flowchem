"""Simulated Ocean Optics / Ocean Insight spectrometer (Flame)."""

from __future__ import annotations

import numpy as np
from loguru import logger

from flowchem.components.device_info import DeviceInfo
from flowchem.devices.flowchem_device import FlowchemDevice


class FlameOpticalSim(FlowchemDevice):
    """
    Simulated Ocean Optics Flame spectrometer.

    The real FlameOptical opens a USB spectrometer via the ``seabreeze`` SDK in
    ``__init__``, which requires hardware, OS-level USB drivers and (on Windows)
    libusb.  This sim bypasses ``seabreeze`` entirely by subclassing
    ``FlowchemDevice`` directly and generating a synthetic spectrum instead.

    State
    -----
    scans_to_average      : int         number of scans averaged per read
    trigger_mode_value    : int | None  last trigger mode set
    _sim_integration_time_us : int      integration time in microseconds
    _sim_powered           : bool       whether the device is "powered on"
    """

    def __init__(
        self,
        serial_number: str | None = None,
        backend: str | None = None,
        name: str = "",
    ) -> None:
        super().__init__(name)
        self.serial_n = serial_number
        self.backend = backend or "sim"
        self.pixels = 2048
        self.max_intensity = 200_000.0
        self.integration_time_micros_limits = (1_000, 65_000_000)
        self.wavelengths = np.linspace(200.0, 850.0, self.pixels)

        self.scans_to_average = 1
        self.trigger_mode_value: int | None = None
        self._sim_integration_time_us = 100_000
        self._sim_powered = False

        self.device_info = DeviceInfo(
            manufacturer="oceanoptics",
            model="SimulatedFlame",
            serial_number=self.serial_n or "SIM-FLAME",
        )
        logger.info(f"[SIM] FlameOptical '{name}' initialized.")

    @classmethod
    def from_config(cls, **config) -> "FlameOpticalSim":
        return cls(
            serial_number=config.pop("serial_number", None),
            backend=config.pop("backend", None),
            name=config.pop("name", "sim-flame"),
        )

    async def initialize(self):
        from flowchem.devices.oceanoptics.flame_spectrometer import GeneralSensor

        self.components.append(GeneralSensor("spectrometer", self))

    def _synthetic_intensities(self) -> np.ndarray:
        """A synthetic spectrum: a gaussian peak on top of a flat baseline."""
        peak = self.max_intensity * 0.5 * np.exp(-((self.wavelengths - 500.0) ** 2) / (2 * 40.0**2))
        baseline = self.max_intensity * 0.01
        return peak + baseline

    async def power_on(self):
        self._sim_powered = True

    async def power_off(self):
        self._sim_powered = False

    async def get_spectrum(self):
        return self._synthetic_intensities()

    async def get_intensity(self, absolute: bool = False, scans_to_average: int | None = None):
        intensities = self._synthetic_intensities()
        if absolute:
            return intensities.tolist()
        return (intensities / self.max_intensity).tolist()

    async def get_wavelength(self):
        return self.wavelengths.tolist()

    async def integration_time(self, int_time: int):
        low, high = self.integration_time_micros_limits
        self._sim_integration_time_us = min(max(int_time, low), high)

    async def set_scans_to_average(self, scans: int):
        scans = int(scans)
        if scans < 1:
            raise ValueError("scans_to_average must be >= 1")
        self.scans_to_average = scans
        return self.scans_to_average

    async def get_scans_to_average(self):
        return self.scans_to_average

    async def set_trigger_mode(self, mode: int):
        self.trigger_mode_value = int(mode)
        return self.trigger_mode_value

    async def get_trigger_mode(self):
        return self.trigger_mode_value
