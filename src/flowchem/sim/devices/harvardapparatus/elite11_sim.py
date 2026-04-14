"""Simulated Harvard Apparatus Elite11 syringe pump."""

from __future__ import annotations

import asyncio
from loguru import logger

from flowchem.devices.harvardapparatus.elite11 import Elite11
from flowchem.devices.harvardapparatus._pumpio import (
    HarvardApparatusPumpIO,
    Protocol11Command,
    PumpStatus,
)


class SimulatedHarvardApparatusPumpIO(HarvardApparatusPumpIO):
    """
    Stateful in-memory replacement for HarvardApparatusPumpIO.

    State
    -----
    syringe_diameter_mm : float
    syringe_volume_ml   : float
    flow_rate_ml_min    : float
    withdraw_rate_ml_min: float
    target_volume_ml    : float
    force_pct           : int
    status              : PumpStatus
    firmware_version    : str
    """

    def __init__(self, address: int = 0):
        # Skip HarvardApparatusPumpIO.__init__ which opens serial port.
        self.lock = asyncio.Lock()
        self._serial = type("_FakeSerial", (), {"name": "SIM", "port": "SIM"})()
        self._address = address

        self._sim_diameter: float = 14.567
        self._sim_syringe_volume: float = 10.0
        self._sim_flow_rate: float = 1.0
        self._sim_withdraw_rate: float = 1.0
        self._sim_target_volume: float = 0.0
        self._sim_force: int = 30
        self._sim_status: PumpStatus = PumpStatus.IDLE
        self._sim_fw: str = "11 ELITE I/W Single 3.0.4"

    def autodiscover_address(self) -> int:
        return self._address

    async def write_and_read_reply(
        self, command: Protocol11Command, return_parsed: bool = True
    ) -> list[str]:
        """Dispatch command and return a realistic response list."""
        async with self.lock:
            response = self._dispatch(command)
            logger.debug(f"[SIM] Elite11 {command.command!r} → {response!r}")
            if not return_parsed:
                return response

            _, _, parsed_response = self.parse_response(response)
            return list(parsed_response)

    def _make_reply(self, body: str = "") -> list[str]:
        """Wrap body in the standard prompt format: '00:  <body>'"""
        status_char = self._sim_status.value
        return [f"0{self._address}{status_char}  {body}".strip()]

    def _dispatch(self, cmd: Protocol11Command) -> list[str]:
        c = cmd.command.strip().lower()
        arg = cmd.arguments.strip()

        if c == "ver":
            return self._make_reply(self._sim_fw)

        if c == "diameter":
            if arg:
                self._sim_diameter = float(arg.split()[0])
                return self._make_reply()
            return self._make_reply(f"{self._sim_diameter:.4f} mm")

        if c == "svolume":
            if arg:
                self._sim_syringe_volume = float(arg.split()[0])
                return self._make_reply()
            return self._make_reply(f"{self._sim_syringe_volume:.4f} ml")

        if c == "force":
            if arg:
                self._sim_force = int(arg)
                return self._make_reply()
            return self._make_reply(f"{self._sim_force}%")

        if c in {"irate", "irate lim"}:
            if c.endswith(" lim") or "lim" in arg:
                # Return rate limits as a function of syringe diameter.
                return self._make_reply("1.000 nl/min to 25.000 ml/min")
            if arg:
                self._sim_flow_rate = float(arg.split()[0])
                return self._make_reply()
            return self._make_reply(f"{self._sim_flow_rate:.6f} ml/min")

        if c in {"wrate", "wrate lim"}:
            if c.endswith(" lim") or "lim" in arg:
                return self._make_reply("1.000 nl/min to 25.000 ml/min")
            if arg:
                self._sim_withdraw_rate = float(arg.split()[0])
                return self._make_reply()
            return self._make_reply(f"{self._sim_withdraw_rate:.6f} ml/min")

        if c == "tvolume":
            if arg:
                self._sim_target_volume = float(arg.split()[0])
                return self._make_reply()
            return self._make_reply(f"{self._sim_target_volume:.6f} ml")

        if c == "cvolume":
            # Clear accumulated volume
            return self._make_reply()

        if c == "ctvolume":
            self._sim_target_volume = 0.0
            return self._make_reply()

        if c == "irun":
            self._sim_status = PumpStatus.INFUSING
            return self._make_reply()

        if c == "wrun":
            self._sim_status = PumpStatus.WITHDRAWING
            return self._make_reply()

        if c == "stp":
            self._sim_status = PumpStatus.IDLE
            return self._make_reply()

        if c == " ":
            # Status query
            return self._make_reply()

        if c == "metrics":
            lines = [
                f"0{self._address}:  Pump type          Pump 11",
                f"0{self._address}:  Pump type string   11 ELITE I/W Single",
                f"0{self._address}:  Direction          Infuse/withdraw",
                f"0{self._address}:  ",
            ]
            return lines

        logger.debug(f"[SIM] Elite11 unhandled command {c!r}")
        return self._make_reply()


class Elite11Sim(Elite11):
    """
    Simulated Harvard Apparatus Elite11 syringe pump.

    Subclasses Elite11 and injects SimulatedHarvardApparatusPumpIO.
    All Elite11 logic runs unmodified.
    """

    sim_io: SimulatedHarvardApparatusPumpIO

    @classmethod
    def from_config(
        cls,
        port: str = "SIM",
        syringe_diameter: str = "14.567 mm",
        syringe_volume: str = "10 ml",
        address: int = 0,
        name: str = "sim-elite11",
        force: int = 30,
        **serial_kwargs,
    ) -> "Elite11Sim":
        sim_io = SimulatedHarvardApparatusPumpIO(address=address)
        instance = cls(
            pump_io=sim_io,
            syringe_diameter=syringe_diameter,
            syringe_volume=syringe_volume,
            address=address,
            name=name,
            force=force,
        )
        instance.sim_io = sim_io
        return instance
