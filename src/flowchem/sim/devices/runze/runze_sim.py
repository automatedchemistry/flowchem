"""Simulated Runze SV-06 multi-position valve and Smart SY-01 syringe pump."""

from __future__ import annotations

from loguru import logger

from flowchem.devices.runze._common import RunzeCommand, RunzeSerialIO
from flowchem.devices.runze.runze_syringe_pump import RunzeSyringePump
from flowchem.devices.runze.runze_valve import (
    RunzeValve,
    RunzeValveHeads,
    RunzeValveIO,
    SV06Command,
)


class SimulatedRunzeValveIO(RunzeValveIO):
    """
    Stateful in-memory replacement for RunzeValveIO.

    State
    -----
    _sim_position  : int   current valve position (1-N)
    _sim_num_ports : int   number of ports (determines valid range)
    """

    def __init__(self, num_ports: int = 6):
        # Skip RunzeValveIO.__init__ which opens serial port.
        self._serial = type("_FakeSerial", (), {"port": "SIM", "name": "SIM"})()
        self._sim_position: int = 1
        self._sim_num_ports: int = num_ports

    @classmethod
    def from_config(cls, config) -> "SimulatedRunzeValveIO":
        return cls(num_ports=int(config.get("num_ports", 6)))

    async def _write_async(self, command: bytes) -> None:
        logger.debug(f"[SIM] RunzeValve ← {command.hex()!r}")

    async def _read_reply_async(self) -> str:
        return ""  # Not used in sim path

    async def write_and_read_reply_async(
        self,
        command: SV06Command,
        raise_errors: bool = True,
        read_timeout: float | None = None,
    ) -> tuple[str, str]:
        fc = command.function_code.lower()

        # GET position: function code 0x3E
        if fc == "3e":
            return "00", f"{self._sim_position:02x}"

        # SET position: function code 0x44
        if fc == "44":
            target = command.parameter
            if 1 <= target <= self._sim_num_ports:
                self._sim_position = target
                return "00", f"{self._sim_position:02x}"
            else:
                if raise_errors:
                    from flowchem.utils.exceptions import DeviceError

                    raise DeviceError(
                        f"Position {target} out of range for {self._sim_num_ports}-port valve"
                    )
                return "02", "00"  # Parameter error

        logger.debug(f"[SIM] RunzeValve unhandled fc={fc!r}")
        return "00", "00"


class RunzeValveSim(RunzeValve):
    """
    Simulated Runze SV-06 multi-position valve.

    TOML usage
    ----------
        [device.my-valve]
        type = "RunzeValve"          # replaced by flowchem-sim
        num_ports = 6                # optional, default 6
    """

    sim_io: SimulatedRunzeValveIO

    @classmethod
    def from_config(cls, **config) -> "RunzeValveSim":
        num_ports = int(config.pop("num_ports", 6))
        config.pop("port", None)
        sim_io = SimulatedRunzeValveIO(num_ports=num_ports)
        instance = cls(
            valve_io=sim_io,
            name=config.pop("name", "sim-runze"),
            address=int(config.pop("address", 1)),
        )
        instance.sim_io = sim_io
        return instance

    async def get_valve_type(self) -> RunzeValveHeads:
        """Return the simulated valve head from the configured port count."""
        return RunzeValveHeads(str(self.sim_io._sim_num_ports))


class SimulatedRunzeSyringePumpIO(RunzeSerialIO):
    """
    Stateful in-memory replacement for RunzeSerialIO, driving a simulated
    Smart SY-01 (plunger plus built-in distribution valve -- the valve
    reuses the exact 0x44/0x4a commands already simulated for the standalone
    SV-06 above).

    State
    -----
    _sim_plunger_position : int   plunger position in steps from home
    _sim_valve_position    : int  current built-in valve position (1-N)
    _sim_num_ports         : int  built-in valve port count (determines valid range)
    _total_steps            : int  full plunger stroke, for clamping moves
    """

    def __init__(self, num_ports: int = 6, total_steps: int = 12000):
        # Skip RunzeSerialIO.__init__ which opens a real serial port.
        self._serial = type("_FakeSerial", (), {"port": "SIM", "name": "SIM"})()
        self._sim_plunger_position: int = 0
        self._sim_valve_position: int = 1
        self._sim_num_ports: int = num_ports
        self._total_steps: int = total_steps

    async def write_and_read_reply_async(
        self,
        command: RunzeCommand,
        raise_errors: bool = True,
        read_timeout: float | None = None,
    ) -> tuple[str, str]:
        fc = command.function_code.lower()

        # SET built-in valve position: function code 0x44.
        if fc == "44":
            target = command.parameter
            if 1 <= target <= self._sim_num_ports:
                self._sim_valve_position = target
                return "00", f"{self._sim_valve_position:02x}"
            else:
                if raise_errors:
                    from flowchem.utils.exceptions import DeviceError

                    raise DeviceError(
                        f"Position {target} out of range for {self._sim_num_ports}-port valve"
                    )
                return "02", "00"  # Parameter error

        # Dispense/injection: function code 0x42 -- toward home.
        if fc == "42":
            self._sim_plunger_position = max(
                0, self._sim_plunger_position - command.parameter
            )
            return "00", "00"

        # Aspirate/suction: function code 0x43 -- away from home.
        if fc == "43":
            self._sim_plunger_position = min(
                self._total_steps, self._sim_plunger_position + command.parameter
            )
            return "00", "00"

        # Home: function code 0x45 -- runs to the reset optocoupler (position 0).
        if fc == "45":
            self._sim_plunger_position = 0
            return "00", "00"

        # Sync position: function code 0x67 -- no-op, 0x45 above already
        # zeroes the tracked position.
        if fc == "67":
            return "00", "00"

        # Read plunger position: function code 0x66.
        if fc == "66":
            return "00", f"{self._sim_plunger_position:x}"

        # Stop: function code 0x49.
        if fc == "49":
            return "00", "00"

        # Get motor status: function code 0x4a -- simulated moves complete
        # instantly, so the pump is always idle by the time this is polled.
        if fc == "4a":
            return "00", "00"

        # Factory command: set address (0x00).
        if fc == "00":
            return "00", "00"

        logger.debug(f"[SIM] RunzeSyringePump unhandled fc={fc!r}")
        return "00", "00"


class RunzeSyringePumpSim(RunzeSyringePump):
    """
    Simulated Runze Smart SY-01 syringe pump (plunger + built-in valve).

    TOML usage
    ----------
        [device.my-pump]
        type = "RunzeSyringePump"    # replaced by flowchem-sim
        syringe_volume = "5 mL"
        total_steps = 12000          # optional, default 12000
        num_ports = 6                # optional, default 6 (built-in valve head)
    """

    sim_io: SimulatedRunzeSyringePumpIO

    @classmethod
    def from_config(cls, **config) -> "RunzeSyringePumpSim":
        num_ports = int(config.pop("num_ports", 6))
        config.pop("port", None)
        total_steps = int(config.get("total_steps", 12000))
        sim_io = SimulatedRunzeSyringePumpIO(
            num_ports=num_ports, total_steps=total_steps
        )
        instance = cls(
            pump_io=sim_io,
            address=int(config.pop("address", 1)),
            name=config.pop("name", "sim-runze-pump"),
            syringe_volume=config.pop("syringe_volume", ""),
            total_steps=total_steps,
        )
        instance.sim_io = sim_io
        return instance
