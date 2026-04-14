"""Simulated Knauer AzuraCompact HPLC pump."""

from __future__ import annotations
from loguru import logger
from flowchem.devices.knauer.azura_compact import AzuraCompact
from flowchem.sim.devices.knauer._knauer_base import SimulatedKnauerEthernetDevice


class AzuraCompactSim(SimulatedKnauerEthernetDevice, AzuraCompact):
    """
    Simulated Knauer Azura Compact pump.

    State
    -----
    flow_rate_ul_min : int    current flow rate setpoint (µL/min)
    pressure_01mpa   : int    current pressure reading (0.1 MPa units)
    running          : bool   pump on/off state
    head_type        : int    10 or 50 (ml/min head)
    """

    def __init__(
        self,
        ip_address="127.0.0.1",
        mac_address=None,
        max_pressure: str = "",
        min_pressure: str = "",
        **kwargs,
    ):
        # Bypass KnauerEthernetDevice network init via our sim base.
        super().__init__(
            ip_address=ip_address,
            mac_address=mac_address,
            max_pressure=max_pressure,
            min_pressure=min_pressure,
            **kwargs,
        )
        self._sim_flow: int = 0  # µL/min
        self._sim_pressure: int = 10  # 0.1 MPa units  → 1 bar
        self._sim_running: bool = False
        self._sim_head: int = 10  # 10 ml/min head by default

    # Called by SimulatedKnauerEthernetDevice._send_and_receive
    def _handle_command(self, message: str) -> str:
        msg = message.strip()

        # GETTER queries end with '?'
        if msg == "HEADTYPE?":
            return f"HEADTYPE:{self._sim_head}"
        if msg == "FLOW?":
            return f"FLOW:{self._sim_flow}"
        if msg.startswith("PMAX") and msg.endswith("?"):
            return f"{msg[:-1]}:400"
        if msg.startswith("PMIN") and msg.endswith("?"):
            return f"{msg[:-1]}:0"
        if msg == "PRESSURE?":
            return str(self._sim_pressure)
        if msg == "IMOTOR?":
            return "IMOTOR:50"
        if msg == "STARTLEVEL?":
            return "STARTLEVEL:1"
        if msg == "STARTMODE?":
            return "STARTMODE:0"
        if msg.startswith("ADJ") and msg.endswith("?"):
            return f"{msg[:-1]}:1000"
        if msg.startswith("CORR") and msg.endswith("?"):
            return f"{msg[:-1]}:100"
        if msg == "EXTFLOW?":
            return "0"
        if msg == "EXTCONTR?":
            return "EXTCONTR:0"
        if msg.startswith("ERRORS"):
            return "ERRORS:0,0,0,0,0"

        # SETTER commands contain ':'
        if ":" in msg:
            key, value = msg.split(":", 1)
            if key == "HEADTYPE":
                self._sim_head = int(value)
                return "HEADTYPE:OK"
            if key == "FLOW":
                self._sim_flow = int(value)
                return "FLOW:OK"
            if key in (
                "PMAX10",
                "PMAX50",
                "PMIN10",
                "PMIN50",
                "IMIN10",
                "IMIN50",
                "STARTLEVEL",
                "STARTMODE",
                "ADJ10",
                "ADJ50",
                "CORR10",
                "CORR50",
                "EXTCONTR",
            ):
                return f"{key}:OK"
            if key == "REMOTE":
                return "REMOTE:OK"
            if key == "LOCAL":
                return "LOCAL:OK"
            return f"{key}:OK"

        # ON / OFF
        if msg == "ON":
            self._sim_running = True
            return "OK"
        if msg == "OFF":
            self._sim_running = False
            return "OK"

        logger.debug(f"[SIM] AzuraCompact unhandled: {msg!r}")
        return "OK"

    async def initialize(self):
        """Initialize the simulated pump without opening a TCP connection."""
        from flowchem.devices.knauer.azura_compact_pump import AzuraCompactPump
        from flowchem.devices.knauer.azura_compact_sensor import AzuraCompactSensor

        logger.info(
            f"[SIM] {self.__class__.__name__} '{self.name}' — skipping TCP connection."
        )

        await self.get_headtype()
        await self.remote_control()
        await self.stop()

        if self._pressure_max:
            await self.set_maximum_pressure(self._pressure_max)
        if self._pressure_min:
            await self.set_minimum_pressure(self._pressure_min)

        self.components.extend(
            [AzuraCompactPump("pump", self), AzuraCompactSensor("pressure", self)]
        )

    @classmethod
    def from_config(cls, **config) -> "AzuraCompactSim":
        config.pop("ip_address", None)
        config.pop("mac_address", None)
        return cls(name=config.pop("name", "sim-azura"), **config)
