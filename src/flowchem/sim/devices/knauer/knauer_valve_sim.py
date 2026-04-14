"""Simulated Knauer multi-position valve."""

from __future__ import annotations

from typing import Any, cast

from loguru import logger

from flowchem.components.flowchem_component import FlowchemComponent
from flowchem.devices.knauer.knauer_valve import KnauerValve
from flowchem.sim.devices.knauer._knauer_base import SimulatedKnauerEthernetDevice


class KnauerValveSim(SimulatedKnauerEthernetDevice, KnauerValve):
    """
    Simulated Knauer valve.

    State
    -----
    position    : str   current position (e.g. "1", "L")
    valve_type  : str   "LI" | "6" | "12" | "16"
    """

    def __init__(
        self, ip_address="127.0.0.1", mac_address=None, valve_type: str = "6", **kwargs
    ):
        super().__init__(ip_address=ip_address, mac_address=mac_address, **kwargs)
        self._sim_valve_type: str = valve_type  # "LI" | "6" | "12" | "16"
        self._sim_position: str = "1"

    def _handle_command(self, message: str) -> str:
        msg = message.strip()

        if msg == "T":
            return f"VALVE {self._sim_valve_type}"
        if msg == "P":
            return self._sim_position
        # Any other message is treated as a position set command
        self._sim_position = msg
        logger.debug(f"[SIM] KnauerValve position set to {msg!r}")
        return msg  # Real valve echoes the position

    async def initialize(self):
        """Initialize the simulated valve without opening a TCP connection."""
        from flowchem.devices.knauer.knauer_valve import KnauerValveHeads
        from flowchem.devices.knauer.knauer_valve_component import (
            Knauer12PortDistributionValve,
            Knauer16PortDistributionValve,
            Knauer6PortDistributionValve,
            KnauerInjectionValve,
        )

        logger.info(
            f"[SIM] {self.__class__.__name__} '{self.name}' — skipping TCP connection."
        )

        self.device_info.additional_info["valve-type"] = await self.get_valve_type()
        valve_component: FlowchemComponent

        match self.device_info.additional_info["valve-type"]:
            case KnauerValveHeads.SIX_PORT_TWO_POSITION:
                valve_component = KnauerInjectionValve(
                    "injection-valve", cast(Any, self)
                )
            case KnauerValveHeads.SIX_PORT_SIX_POSITION:
                valve_component = Knauer6PortDistributionValve(
                    "distribution-valve", cast(Any, self)
                )
            case KnauerValveHeads.TWELVE_PORT_TWELVE_POSITION:
                valve_component = Knauer12PortDistributionValve(
                    "distribution-valve", cast(Any, self)
                )
            case KnauerValveHeads.SIXTEEN_PORT_SIXTEEN_POSITION:
                valve_component = Knauer16PortDistributionValve(
                    "distribution-valve", cast(Any, self)
                )
            case _:
                raise RuntimeError("Unknown valve type")

        self.components.append(valve_component)

    @classmethod
    def from_config(cls, **config) -> "KnauerValveSim":
        config.pop("ip_address", None)
        config.pop("mac_address", None)
        valve_type = config.pop("valve_type", "6")
        return cls(
            name=config.pop("name", "sim-knauer-valve"), valve_type=valve_type, **config
        )
