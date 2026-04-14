"""Simulated Vici Valco injection valve."""

from __future__ import annotations

from loguru import logger

from flowchem.devices.vicivalco.vici_valve import (
    ViciValve,
    ViciValcoValveIO,
    ViciCommand,
)


class SimulatedViciValcoValveIO(ViciValcoValveIO):
    """
    Stateful in-memory replacement for ViciValcoValveIO.

    State
    -----
    _sim_position : str   current position ("A" / "B")
    _sim_version  : str   firmware version string
    """

    def __init__(self):
        # Skip ViciValcoValveIO.__init__ which opens serial port.
        self._serial = type("_FakeSerial", (), {"name": "SIM", "port": "SIM"})()
        self._sim_position: str = "A"
        self._sim_version: str = "Firmware v2.34"

    @classmethod
    def from_config(cls, port, **serial_kwargs) -> "SimulatedViciValcoValveIO":
        return cls()

    @property
    def name(self) -> str:
        return "SIM"

    async def write_and_read_reply(self, command: ViciCommand) -> str:
        cmd = command.command.strip().upper()
        logger.debug(
            f"[SIM] ViciValve addr={command.valve_id} cmd={cmd!r} val={command.value!r}"
        )

        if cmd == "LRN":
            return ""  # reply_lines=0

        if cmd == "HM":
            self._sim_position = "A"
            return ""  # reply_lines=0

        if cmd == "CP":
            return self._sim_position

        if cmd == "VR":
            return self._sim_version

        if cmd == "GO":
            self._sim_position = command.value.strip() or "A"
            return ""

        if cmd == "DT":
            return ""  # set delay — no reply

        if cmd == "TT":
            # Toggle position
            self._sim_position = "B" if self._sim_position == "A" else "A"
            return ""

        logger.debug(f"[SIM] ViciValve unhandled: {cmd!r}")
        return ""


class ViciValveSim(ViciValve):
    """
    Simulated Vici Valco injection valve.

    All ViciValve logic runs unmodified; only the IO layer is replaced.
    """

    sim_io: SimulatedViciValcoValveIO

    @classmethod
    def from_config(
        cls,
        port: str = "SIM",
        address: int = 0,
        name: str = "sim-vici",
        **serial_kwargs,
    ) -> "ViciValveSim":
        sim_io = SimulatedViciValcoValveIO()
        instance = cls(valve_io=sim_io, address=address, name=name)
        instance.sim_io = sim_io
        return instance
