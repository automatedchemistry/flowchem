"""Simulated DataApex Clarity chromatography software."""

from __future__ import annotations

from loguru import logger

from flowchem.devices.dataapex.clarity import Clarity


class ClaritySim(Clarity):
    """
    Simulated Clarity chromatography controller.

    The real Clarity spawns a subprocess (claritychrom.exe CLI).  This sim
    skips subprocess creation entirely and records commands for inspection.

    State
    -----
    _sim_commands : list[str]   all commands sent (for test assertions)
    """

    def __init__(
        self,
        name="sim-clarity",
        executable="claritychrom.exe",
        instrument_number=1,
        startup_time=0.0,  # no waiting in simulation
        startup_method="",
        cmd_timeout=3.0,
        user="admin",
        password="",
        cfg_file="",
    ):
        # Skip Clarity.__init__ which validates that the executable exists.
        from flowchem.devices.flowchem_device import FlowchemDevice
        from flowchem.components.device_info import DeviceInfo

        FlowchemDevice.__init__(self, name=name)
        self.device_info = DeviceInfo(
            manufacturer="DataApex",
            model="SimulatedClarity",
        )
        self.instrument = instrument_number
        self.startup_time = startup_time
        self.cmd_timeout = cmd_timeout
        self.executable = executable
        self._init_command = ""
        self._sim_commands: list[str] = []
        logger.info(f"[SIM] Clarity '{name}' initialized.")

    @classmethod
    def from_config(cls, **config) -> "ClaritySim":
        return cls(
            name=config.pop("name", "sim-clarity"),
            instrument_number=int(config.pop("instrument_number", 1)),
            startup_method=config.pop("startup_method", ""),
            user=config.pop("user", "admin"),
            password=config.pop("password", ""),
            cfg_file=config.pop("cfg_file", ""),
        )

    async def initialize(self):
        from flowchem.devices.dataapex.clarity_hplc_control import ClarityComponent

        logger.info("[SIM] Clarity skipping subprocess startup.")
        self.components.append(ClarityComponent(name="clarity", hw_device=self))

    async def execute_command(
        self, command: str, without_instrument_num: bool = False
    ) -> bool:
        """Record command instead of spawning subprocess."""
        self._sim_commands.append(command)
        logger.debug(f"[SIM] Clarity command recorded: {command!r}")
        return True
