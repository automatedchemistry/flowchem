"""Simulated Mettler-Toledo iCIR (FlowIR / ReactIR)."""

from __future__ import annotations

import datetime
from typing import Any, cast

from loguru import logger

from flowchem.components.analytics.ir import IRSpectrum
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.components.device_info import DeviceInfo


class IcIRSim(FlowchemDevice):
    """
    Simulated Mettler-Toledo iCIR spectrometer.

    The real IcIR connects to an OPC-UA server (asyncua.Client) which cannot
    exist without the iCIR software running.  This sim bypasses the OPC-UA
    layer entirely by subclassing FlowchemDevice directly.

    State
    -----
    _sim_running      : bool       whether an experiment is running
    _sim_sample_count : int        auto-increments each fake acquisition
    _sim_spectrum     : IRSpectrum static fake spectrum returned for all queries
    """

    def __init__(self, template="", url="", name=""):
        super().__init__(name)
        self.device_info = DeviceInfo(
            manufacturer="Mettler-Toledo",
            model="SimulatedIcIR",
            version="7.1.91.0",
        )
        self._template = template
        self._sim_running: bool = False
        self._sim_sample_count: int = 0
        # A minimal fake spectrum: 10 wavenumber/intensity pairs
        wn = [float(value) for value in range(4000, 650, -335)]
        self._sim_spectrum = IRSpectrum(wavenumber=wn, intensity=[0.1] * len(wn))
        logger.info(f"[SIM] IcIR '{name}' initialized.")

    @classmethod
    def from_config(cls, **config) -> "IcIRSim":
        return cls(
            template=config.pop("template", ""),
            url=config.pop("url", ""),
            name=config.pop("name", "sim-icir"),
        )

    async def initialize(self):
        from flowchem.devices.mettlertoledo.icir_control import IcIRControl

        logger.info("[SIM] IcIR skipping OPC-UA connection.")
        self.components.append(IcIRControl("ir-control", cast(Any, self)))

    # Implement the public API that IcIRControl calls
    async def is_iCIR_connected(self) -> bool:
        return True

    async def probe_status(self) -> str:
        return "Running" if self._sim_running else "Not running"

    async def sample_count(self) -> int:
        return self._sim_sample_count

    async def last_sample_time(self) -> datetime.datetime:
        return datetime.datetime.now()

    async def last_spectrum_treated(self) -> IRSpectrum:
        self._sim_sample_count += 1
        return self._sim_spectrum

    async def last_spectrum_raw(self) -> IRSpectrum:
        return self._sim_spectrum

    async def last_spectrum_background(self) -> IRSpectrum:
        return self._sim_spectrum

    async def start_experiment(self, template: str = "", name: str = "sim-exp"):
        self._sim_running = True
        logger.info(f"[SIM] IcIR experiment '{name}' started.")
        return True

    async def stop_experiment(self):
        self._sim_running = False
        logger.info("[SIM] IcIR experiment stopped.")

    async def wait_until_idle(self):
        self._sim_running = False

    def list_protocols(self) -> list[str]:
        return ["PROTON", "CARBON", "FLUORINE"]
