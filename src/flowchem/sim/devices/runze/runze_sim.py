"""Simulated Runze SV-06 multi-position valve."""

from __future__ import annotations

from loguru import logger

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
        self, command: SV06Command, raise_errors: bool = True
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
