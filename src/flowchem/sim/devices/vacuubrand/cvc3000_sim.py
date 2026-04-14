"""Simulated Vacuubrand CVC3000 vacuum controller."""

from __future__ import annotations

from loguru import logger

from flowchem.devices.vacuubrand.cvc3000 import CVC3000


class CVC3000Sim(CVC3000):
    """
    Simulated CVC3000 vacuum controller.

    State
    -----
    _sim_pressure  : float   current pressure in mbar
    _sim_setpoint  : float   pressure setpoint in mbar
    _sim_speed     : int     motor speed 0-100 %
    _sim_version   : str     firmware version string
    """

    def __init__(self, aio=None, name=""):
        from flowchem.devices.flowchem_device import FlowchemDevice
        from flowchem.components.device_info import DeviceInfo

        FlowchemDevice.__init__(self, name)
        self._serial = None
        self.device_info = DeviceInfo(
            manufacturer="Vacuubrand",
            model="SimulatedCVC3000",
            serial_number="SIM-CVC",
        )
        self._sim_pressure: float = 1013.0  # mbar (atmospheric)
        self._sim_setpoint: float = 500.0  # mbar
        self._sim_speed: int = 100
        self._sim_version: str = "CVC 3000 V3.10"

    @classmethod
    def from_config(cls, port, name=None, **serial_kwargs) -> "CVC3000Sim":
        return cls(name=name or "sim-cvc3000")

    async def _send_command_and_read_reply(self, command: str) -> str:
        cmd = command.strip().upper()
        logger.debug(f"[SIM] CVC3000 ← {cmd!r}")

        if cmd == "IN_VER":
            return self._sim_version

        if cmd.startswith("OUT_SP_1 "):
            self._sim_setpoint = float(cmd.split()[-1])
            return "OK\r\n"

        if cmd == "IN_PV_1":
            return f"{self._sim_pressure:.1f} mbar\r\n"

        if cmd.startswith("OUT_SP_2 "):
            self._sim_speed = int(cmd.split()[-1])
            return "OK\r\n"

        if cmd == "IN_STAT":
            # Format: 6-char status string: pump_on, inline_valve, coolant, vent, mode, state
            # "100020" → pump on, inline open, coolant closed, vent closed, AUTO mode, VACUUM_REACHED
            return "100020\r\n"

        # Configuration commands — just acknowledge
        if cmd in ("CVC 3", "STORE", "ECHO 1", "REMOTE 1", "OUT_CFG 00001"):
            return "OK\r\n"

        logger.debug(f"[SIM] CVC3000 unhandled: {cmd!r}")
        return "OK\r\n"
