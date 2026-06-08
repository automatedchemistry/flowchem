"""Simulated Manson power supply."""

from __future__ import annotations

from loguru import logger

from flowchem.devices.manson.manson_power_supply import MansonPowerSupply


class MansonPowerSupplySim(MansonPowerSupply):
    """
    Simulated Manson HCS-3xxx power supply.

    State
    -----
    _sim_voltage  : float   output voltage (V)
    _sim_current  : float   output current (A)
    _sim_on       : bool    output enabled
    _sim_model    : str     model string
    """

    def __init__(self, aio=None, name=""):
        from flowchem.devices.flowchem_device import FlowchemDevice
        from flowchem.components.device_info import DeviceInfo

        FlowchemDevice.__init__(self, name)
        self._serial = None
        self.device_info = DeviceInfo(
            manufacturer="Manson",
            model="HCS-3102",
            serial_number="SIM-MANSON",
        )
        self._sim_voltage: float = 5.0
        self._sim_current: float = 1.0
        self._sim_on: bool = False
        self._sim_model: str = "HCS-3102"

    @classmethod
    def from_config(cls, port, name="", **serial_kwargs) -> "MansonPowerSupplySim":
        return cls(name=name or "sim-manson")

    async def get_info(self) -> str:
        """Return the simulated model without serial reply parsing."""
        return self._sim_model

    async def _send_command(self, command: str) -> str:
        cmd = command.strip().upper()
        logger.debug(f"[SIM] Manson ← {cmd!r}")

        if cmd == "GMOD":
            return f"{self._sim_model} "

        if cmd == "SOUT0":
            self._sim_on = True
            return "OK"

        if cmd == "SOUT1":
            self._sim_on = False
            return "OK"

        if cmd == "GETD":
            # Format: VVVVCCCCM  (voltage ×100, current ×100, mode 0=CV 1=CC)
            v = int(self._sim_voltage * 100)
            c = int(self._sim_current * 100)
            return f"{v:04d}{c:04d}0"

        if cmd == "GMAX":
            # Format: VVVCCC  (voltage ×10, current ×10 for HCS-3102)
            v = int(30 * 10)
            c = int(10 * 10)
            return f"{v:03d}{c:03d}"

        if cmd == "GETS":
            v = int(self._sim_voltage * 10)
            c = int(self._sim_current * 10)
            return f"{v:03d}{c:03d}"

        if cmd.startswith("VOLT"):
            self._sim_voltage = int(cmd[4:]) / 10.0
            return "OK"

        if cmd.startswith("CURR"):
            self._sim_current = int(cmd[4:]) / 100.0
            return "OK"

        if cmd in ("SPRO0", "SPRO1"):
            return "OK"

        if cmd.startswith("GETM"):
            # Three preset lines
            lines = []
            for _ in range(3):
                v = int(self._sim_voltage * 10)
                c = int(self._sim_current * 10)
                lines.append(f"{v:03d}{c:03d}")
            return "\r".join(lines)

        if cmd.startswith("PROM") or cmd.startswith("RUNM"):
            return "OK"

        logger.debug(f"[SIM] Manson unhandled: {cmd!r}")
        return "OK"
