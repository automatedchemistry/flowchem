"""Simulated Huber chiller."""

from __future__ import annotations

from loguru import logger

from flowchem.devices.huber.chiller import HuberChiller


def _huber_reply(code_hex: str, value: int) -> str:
    """Build a Huber PB slave reply string: {S<code><value_hex4>\r\n"""
    return f"{{S{code_hex}{value & 0xFFFF:04X}\r\n"


class HuberChillerSim(HuberChiller):
    """
    Simulated Huber chiller.

    State
    -----
    _sim_temp_set   : int     temperature setpoint in protocol units (°C × 100, two's complement)
    _sim_temp_cur   : float   current temperature °C
    _sim_serial     : int     fake serial number
    _sim_t_min      : int     min temperature in protocol units
    _sim_t_max      : int     max temperature in protocol units
    """

    def __init__(
        self, aio=None, name="", min_temp: float = -40.0, max_temp: float = 150.0
    ):
        # Skip HuberChiller.__init__ which opens a serial port.
        from flowchem.devices.flowchem_device import FlowchemDevice
        from flowchem.components.device_info import DeviceInfo

        FlowchemDevice.__init__(self, name)
        self._serial = None
        self._min_t = min_temp
        self._max_t = max_temp
        self.device_info = DeviceInfo(
            manufacturer="Huber",
            model="SimulatedChiller",
            serial_number="SIM-HUBER",
        )

        self._sim_temp_set: int = 2500  # 25.00 °C
        self._sim_temp_cur: float = 25.0
        self._sim_serial: int = 0x12345678
        self._sim_t_min: int = int(min_temp * 100) & 0xFFFF
        self._sim_t_max: int = int(max_temp * 100) & 0xFFFF

    @classmethod
    def from_config(cls, port, name=None, **serial_kwargs) -> "HuberChillerSim":
        return cls(
            name=name or "sim-huber",
            min_temp=float(serial_kwargs.pop("min_temp", -40.0)),
            max_temp=float(serial_kwargs.pop("max_temp", 150.0)),
        )

    async def _send_command_and_read_reply(self, command: str) -> str:
        """Parse the PB protocol command and return a realistic reply."""
        cmd = command.upper().strip()
        logger.debug(f"[SIM] HuberChiller ← {cmd!r}")

        if not cmd.startswith("{M"):
            return _huber_reply("00", 0)

        code = cmd[2:4]  # hex code, e.g. "00", "01", "1B"
        data = cmd[4:8]  # "****" (read) or a 4-hex-char value (write)

        # Temperature setpoint GET / SET  → code 0x00 = "00"
        if code == "00":
            if data != "****":
                self._sim_temp_set = int(data, 16)
                # Two's complement → actual °C
                raw = self._sim_temp_set
                self._sim_temp_cur = ((raw - 65536) / 100) if raw > 32767 else raw / 100
            return _huber_reply("00", self._sim_temp_set)

        # Internal temperature  → code 0x01 = "01"
        if code == "01":
            raw = int(self._sim_temp_cur * 100) & 0xFFFF
            return _huber_reply("01", raw)

        # Process temperature  → code 0x07 = "07"
        if code == "07":
            raw = int(self._sim_temp_cur * 100) & 0xFFFF
            return _huber_reply("07", raw)

        # Min temperature  → code 0x30 = "30"
        if code == "30":
            return _huber_reply("30", self._sim_t_min)

        # Max temperature  → code 0x31 = "31"
        if code == "31":
            return _huber_reply("31", self._sim_t_max)

        # Serial number high word  → code 0x1B = "1B"
        if code == "1B":
            return _huber_reply("1B", (self._sim_serial >> 16) & 0xFFFF)

        # Serial number low word  → code 0x1C = "1C"
        if code == "1C":
            return _huber_reply("1C", self._sim_serial & 0xFFFF)

        logger.debug(f"[SIM] HuberChiller unhandled code {code!r}")
        return _huber_reply(code, 0)
