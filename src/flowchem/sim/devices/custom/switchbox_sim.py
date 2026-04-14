"""Simulated MPIKG Switch Box."""

from __future__ import annotations

import asyncio
from loguru import logger

from flowchem.devices.custom.mpikg_switch_box import (
    SwitchBoxBeferelayCommand,
    SwitchBoxGeneralCommand,
    SwitchBoxIO,
    SwitchBoxMPIKG,
)


class SimulatedSwitchBoxIO(SwitchBoxIO):
    """
    Stateful in-memory replacement for SwitchBoxIO.

    State
    -----
    _sim_ports   : dict   port → 16-bit int  (relay state, ports a-d)
    _sim_dac     : dict   channel → int      (DAC setpoints, 0-4095)
    _sim_version : str    firmware version string
    """

    def __init__(self):
        # Skip SwitchBoxIO.__init__ which opens a serial port.
        self.lock = asyncio.Lock()
        self._serial = type("_FakeSerial", (), {"port": "SIM", "name": "SIM"})()
        self._sim_ports: dict[str, int] = {"a": 0, "b": 0, "c": 0, "d": 0}
        self._sim_dac: dict[int, int] = {}  # channel → bits
        self._sim_version: str = "SIM-SWITCHBOX-V1.0"

    @classmethod
    def from_config(cls, port, **serial_kwargs) -> "SimulatedSwitchBoxIO":
        return cls()

    def reset_buffer(self):
        pass  # Nothing to reset

    async def write_and_read_reply(
        self, command: SwitchBoxGeneralCommand | SwitchBoxBeferelayCommand
    ) -> str:
        async with self.lock:
            compiled = command.compile().decode("ascii").strip()
            logger.debug(f"[SIM] SwitchBox ← {compiled!r}")
            return self._dispatch(compiled)

    def _dispatch(self, compiled: str) -> str:
        parts = compiled.lower().split()
        if not parts:
            return "OK"

        verb = parts[0]  # "get" or "set"

        # ---- VERSION ----
        if verb == "get" and len(parts) > 1 and parts[1] == "ver":
            return self._sim_version

        # ---- RELAY (port) COMMANDS ----
        if len(parts) >= 2:
            target = parts[1].split(":")[0]  # e.g. "a", "abcd", "starta"

            if verb == "get":
                if target == "abcd":
                    parts_list = []
                    for p in ("a", "b", "c", "d"):
                        parts_list.append(f"{p}:{self._sim_ports[p]}")
                    return ",".join(parts_list)
                elif target in self._sim_ports:
                    return f"{target}:{self._sim_ports[target]}"
                elif target.startswith("dac"):
                    ch = int(target[3:]) if target[3:].isdigit() else 1
                    bits = self._sim_dac.get(ch, 0)
                    return f"dac{ch}:{bits}"
                elif target.startswith("adc"):
                    return ";".join(f"adc{channel}:0.000" for channel in range(1, 9))

            elif verb == "set":
                if ":" in parts[1]:
                    key, val = parts[1].split(":", 1)
                    key = key.lower()
                    if key == "abcd":
                        vals = [int(v) for v in val.split(",")]
                        for i, p in enumerate(("a", "b", "c", "d")):
                            if i < len(vals):
                                self._sim_ports[p] = vals[i]
                        return "OK"
                    elif key in self._sim_ports:
                        self._sim_ports[key] = int(val)
                        return "OK"
                    elif key.startswith("dac"):
                        ch = int(key[3:]) if key[3:].isdigit() else 1
                        self._sim_dac[ch] = int(val)
                        return "OK"
                    elif key.startswith("start"):
                        # Startup values — acknowledge but don't need to store
                        return "OK"

        logger.debug(f"[SIM] SwitchBox unhandled: {compiled!r}")
        return "OK"


class SwitchBoxMPIKGSim(SwitchBoxMPIKG):
    """
    Simulated MPIKG Switch Box.

    Injects SimulatedSwitchBoxIO so all SwitchBoxMPIKG logic runs unchanged.
    """

    sim_io: SimulatedSwitchBoxIO

    @classmethod
    def from_config(
        cls, port: str = "SIM", name: str = "", **serial_kwargs
    ) -> "SwitchBoxMPIKGSim":
        sim_io = SimulatedSwitchBoxIO()
        instance = cls(box_io=sim_io, name=name or "sim-switchbox")
        instance.sim_io = sim_io
        return instance
