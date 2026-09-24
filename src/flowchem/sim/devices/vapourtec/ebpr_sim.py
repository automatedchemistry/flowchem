"""Simulated Vapourtec eBPR back pressure regulator."""

from __future__ import annotations

from typing import Any, cast

from loguru import logger

from flowchem.components.device_info import DeviceInfo
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.vapourtec.ebpr import EBPR


class EBPRSim(FlowchemDevice):
    """
    Simulated Vapourtec eBPR back pressure regulator.

    The real EBPR uses a proprietary NDA command package (flowchem_vapourtec)
    and communicates over serial. This sim subclasses FlowchemDevice directly
    and provides stub implementations of every method called by
    EBPRPressureControl.

    State
    -----
    _sim_control_on    : bool   pressure control on/off
    _sim_setpoint_mbar : float  pressure setpoint, mbar
    _sim_pressure_mbar : float  "measured" pressure, mbar (tracks setpoint instantly)
    """

    def __init__(self, name: str = "", **config) -> None:
        super().__init__(name)
        self._serial = None
        self.device_info = DeviceInfo(
            manufacturer="Vapourtec",
            model="SimulatedEBPR",
            version="SIM-1.0",
        )
        self._sim_control_on: bool = False
        self._sim_setpoint_mbar: float = 0.0
        self._sim_pressure_mbar: float = 0.0
        self._sim_version: str = "SIM-EBPR-1.0"
        logger.info(f"[SIM] EBPR '{name}' initialized.")

    @classmethod
    def from_config(cls, **config) -> "EBPRSim":
        config.pop("port", None)
        return cls(name=config.pop("name", "sim-ebpr"))

    async def initialize(self):
        """Register the real, unmodified EBPRPressureControl component."""
        from flowchem.devices.vapourtec.ebpr_component_control import (
            EBPRPressureControl,
        )

        self.device_info.version = await self.version()
        self.components.append(EBPRPressureControl("pressure", cast(Any, self)))

    async def version(self) -> str:
        return self._sim_version

    async def get_status(self) -> EBPR.Status:
        pressure_bar = self._sim_pressure_mbar / 1000.0
        return EBPR.Status(
            self._sim_control_on,
            "25.0",
            f"{pressure_bar:.3f}",
            str(round(self._sim_setpoint_mbar, 3)),
            "0",
        )

    async def get_pressure(self) -> float:
        """Get the current pressure in bar."""
        return self._sim_pressure_mbar / 1000.0

    async def set_pressure(self, pressure_mbar: float):
        """Set the pressure set point in mbar; measured pressure converges instantly."""
        self._sim_setpoint_mbar = float(pressure_mbar)
        self._sim_pressure_mbar = self._sim_setpoint_mbar
        logger.debug(f"[SIM] EBPR → {self._sim_setpoint_mbar:.1f} mbar")

    async def power_on(self):
        self._sim_control_on = True

    async def power_off(self):
        self._sim_control_on = False
