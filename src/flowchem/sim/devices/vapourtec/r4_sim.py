"""Simulated Vapourtec R4 heater module."""

from __future__ import annotations

from typing import Any, cast

from loguru import logger

from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.components.device_info import DeviceInfo
from flowchem.devices.vapourtec.r4_heater import R4Heater


class _StubR4Commands:
    """Minimal stub for VapourtecR4Commands (NDA package)."""

    VERSION = "V"
    SET_TEMPERATURE = "ST {channel} {temperature_in_C}"
    GET_STATUS = "GS {channel}"
    POWER_ON = "PON {channel}"
    POWER_OFF = "POFF {channel}"


class R4HeaterSim(FlowchemDevice):
    """
    Simulated Vapourtec R4 heater module.

    The real R4Heater uses a proprietary NDA command package
    (flowchem_vapourtec) and communicates over serial.  This sim
    subclasses FlowchemDevice directly and provides stub implementations
    of every method called by R4HeaterChannelControl.

    State
    -----
    _sim_temps    : dict  channel (0-3) → float °C
    _sim_enabled  : dict  channel (0-3) → bool
    _sim_version  : str   firmware version string
    """

    def __init__(
        self,
        name: str = "",
        min_temp: float | list = -100,
        max_temp: float | list = 250,
        **config,
    ):
        super().__init__(name)
        # Normalise min/max to lists of 4
        if not isinstance(min_temp, list):
            min_temp = [min_temp] * 4
        if not isinstance(max_temp, list):
            max_temp = [max_temp] * 4
        self._min_t = min_temp
        self._max_t = max_temp

        self.cmd = _StubR4Commands()
        self._serial = None

        self.device_info = DeviceInfo(
            manufacturer="Vapourtec",
            model="SimulatedR4",
            version="SIM-1.0",
        )

        # Per-channel state
        self._sim_temps: dict[int, float] = {0: 25.0, 1: 25.0, 2: 25.0, 3: 25.0}
        self._sim_enabled: dict[int, bool] = {0: False, 1: False, 2: False, 3: False}
        self._sim_version: str = "SIM-R4-1.0"
        logger.info(f"[SIM] R4Heater '{name}' initialized.")

    @classmethod
    def from_config(cls, **config) -> "R4HeaterSim":
        config.pop("port", None)
        return cls(
            name=config.pop("name", "sim-r4"),
            min_temp=config.pop("min_temp", -100),
            max_temp=config.pop("max_temp", 250),
        )

    async def initialize(self):
        """Register four R4HeaterChannelControl components."""
        from flowchem import ureg
        from flowchem.components.technical.temperature import TempRange
        from flowchem.devices.vapourtec.r4_heater_channel_control import (
            R4HeaterChannelControl,
        )

        temp_limits = {
            n: TempRange(
                min=ureg.Quantity(f"{self._min_t[n]} °C"),
                max=ureg.Quantity(f"{self._max_t[n]} °C"),
            )
            for n in range(4)
        }
        self.components.extend(
            [
                R4HeaterChannelControl(
                    f"reactor{n + 1}", cast(Any, self), n, temp_limits[n]
                )
                for n in range(4)
            ]
        )

    # ------------------------------------------------------------------
    # Public API used by R4HeaterChannelControl
    # ------------------------------------------------------------------

    async def version(self) -> str:
        return self._sim_version

    async def write_and_read_reply(self, command: str) -> str:
        """Low-level dispatch — only needed if anything calls it directly."""
        logger.debug(f"[SIM] R4Heater ← {command!r}")
        cmd = command.strip()
        if cmd == _StubR4Commands.VERSION:
            return self._sim_version
        return "OK"

    async def set_temperature(self, channel: int, temperature):
        """Set temperature for one channel (accepts pint.Quantity or float °C)."""
        try:
            t_c = temperature.m_as("°C")
        except AttributeError:
            t_c = float(temperature)
        self._sim_temps[channel] = t_c
        self._sim_enabled[channel] = True
        logger.debug(f"[SIM] R4Heater ch{channel} → {t_c:.1f} °C")

    async def get_status(self, channel: int) -> R4Heater.ChannelStatus:
        """Return a ChannelStatus namedtuple.  State is 'S' (stable) or 'U' (unplugged)."""
        temp = self._sim_temps[channel]
        return R4Heater.ChannelStatus(state="S", temperature=str(temp))

    async def get_temperature(self, channel: int) -> str:
        """Return temperature as string (matches real device contract)."""
        return str(self._sim_temps[channel])

    async def power_on(self, channel: int):
        self._sim_enabled[channel] = True
        logger.debug(f"[SIM] R4Heater ch{channel} power ON")

    async def power_off(self, channel: int):
        self._sim_enabled[channel] = False
        logger.debug(f"[SIM] R4Heater ch{channel} power OFF")
