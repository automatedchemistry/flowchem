"""Simulated custom Peltier cooler."""

from __future__ import annotations

from loguru import logger

from flowchem.devices.custom.peltier_cooler import (
    PeltierCommand,
    PeltierCooler,
    PeltierIO,
)


class SimulatedPeltierIO(PeltierIO):
    """
    Stateful in-memory replacement for PeltierIO.

    State
    -----
    _sim_temp_set     : float   temperature setpoint °C
    _sim_temp_cur     : float   current temperature °C
    _sim_sink_temp    : float   heat sink temperature °C
    _sim_enabled      : bool    temperature control active
    _sim_cool_limit   : float   cooling current limit A
    _sim_heat_limit   : float   heating current limit A
    _sim_p, _i, _d    : float   PID parameters
    _sim_t_max        : float   max temperature °C
    _sim_t_min        : float   min temperature °C
    """

    def __init__(self, address: int = 0):
        # Skip PeltierIO.__init__ which opens a serial port.
        from asyncio import Lock

        self.lock = Lock()
        self._serial = type("_FakeSerial", (), {"port": "SIM", "name": "SIM"})()
        self._address = address

        self._sim_temp_set: float = 25.0
        self._sim_temp_cur: float = 25.0
        self._sim_sink_temp: float = 30.0
        self._sim_enabled: bool = False
        self._sim_cool_limit: float = 3.0
        self._sim_heat_limit: float = 3.0
        self._sim_p: float = 2.83
        self._sim_i: float = 2.36
        self._sim_d: float = 0.59
        self._sim_t_max: float = 50.0
        self._sim_t_min: float = -55.0
        self._sim_slope: float = 0.0

    def reset_buffer(self):
        pass

    async def write_and_read_reply(self, command: PeltierCommand) -> str:
        """Dispatch the command and return a simulated response."""
        cmd_str = command.command_string.upper()
        arg = command.command_argument
        logger.debug(
            f"[SIM] Peltier addr={command.target_peltier_address} cmd={cmd_str!r} arg={arg!r}"
        )

        # Temperature get/set
        if cmd_str == "GT1":
            return str(round(self._sim_temp_cur, 2))
        if cmd_str == "GT2":
            return str(round(self._sim_sink_temp, 2))
        if cmd_str == "STV":
            val = float(arg) / 100
            self._sim_temp_set = val
            self._sim_temp_cur = val  # instant settle in sim
            return str(val)

        # Slope
        if cmd_str == "STS":
            self._sim_slope = float(arg) / 100
            return str(self._sim_slope)

        # On/Off
        if cmd_str == "SEN":
            self._sim_enabled = True
            return "1"
        if cmd_str == "SDI":
            self._sim_enabled = False
            return "0"

        # Current limits
        if cmd_str == "SCC":
            self._sim_cool_limit = float(arg) / 100
            return str(self._sim_cool_limit)
        if cmd_str == "SHC":
            self._sim_heat_limit = float(arg) / 100
            return str(self._sim_heat_limit)

        # PID
        if cmd_str == "SDF":
            self._sim_d = float(arg) / 100
            return str(self._sim_d)
        if cmd_str == "SIF":
            self._sim_i = float(arg) / 100
            return str(self._sim_i)
        if cmd_str == "SPF":
            self._sim_p = float(arg) / 100
            return str(self._sim_p)

        # Limits
        if cmd_str == "SMA":
            self._sim_t_max = float(arg) / 100
            return str(self._sim_t_max)
        if cmd_str == "SMI":
            self._sim_t_min = float(arg) / 100
            return str(self._sim_t_min)

        # Power / current readings
        if cmd_str == "GCU":
            return "0.0"
        if cmd_str == "GPW":
            return "0"

        # Settings dump
        if cmd_str == "GPA":
            return (
                f"{self._sim_temp_set},"
                f"{self._sim_temp_cur},"
                f"{self._sim_p},"
                f"{self._sim_i},"
                f"{self._sim_d}"
            )

        # Empty / prompt probe
        if cmd_str == "":
            return "0"

        logger.debug(f"[SIM] Peltier unhandled: {cmd_str!r}")
        return "0"


class PeltierCoolerSim(PeltierCooler):
    """
    Simulated Peltier cooler.

    Injects SimulatedPeltierIO so all PeltierCooler logic runs unchanged.
    """

    sim_io: SimulatedPeltierIO

    @classmethod
    def from_config(
        cls,
        port: str = "SIM",
        address: int = 0,
        name: str = "",
        peltier_defaults: str | None = None,
        **serial_kwargs,
    ) -> "PeltierCoolerSim":
        sim_io = SimulatedPeltierIO(address=address)
        instance = cls(
            peltier_io=sim_io,
            address=address,
            name=name or "sim-peltier",
            peltier_defaults=peltier_defaults,
        )
        instance.sim_io = sim_io
        return instance
