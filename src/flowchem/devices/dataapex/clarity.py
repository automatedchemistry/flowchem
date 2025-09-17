"""Controls a local ClarityChrom instance via the CLI interface."""
# See https://www.dataapex.com/documentation/Content/Help/110-technical-specifications/110.020-command-line-parameters/110.020-command-line-parameters.htm
import asyncio
from pathlib import Path
from shutil import which

from loguru import logger

from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.utils.people import jakob, wei_hsin

from .clarity_hplc_control import ClarityComponent


class Clarity(FlowchemDevice):
    """
    Controls a local ClarityChrom instance via the CLI interface.

    This class manages software startup, configuration, and command execution for
    ClarityChrom chromatography software. It validates executable paths, constructs
    initialization commands, and handles CLI interactions with timeout management.

    Attributes:
    -----------
    executable : str
        Path to the ClarityChrom executable. Automatically quoted if spaces are detected.
    instrument_number : int
        Target instrument number for multi-instrument setups (default: 1).
    startup_time : float
        Time (seconds) allowed for software initialization before operation.
    cmd_timeout : float
        Maximum duration (seconds) allowed for individual command execution.
    _init_command : str
        Pre-built initialization command combining config file, credentials,
        and startup method parameters.

    Methods:
    --------
    initialize() -> None
        Start ClarityChrom with configured parameters and register components.
    execute_command(command: str, without_instrument_num: bool = False) -> bool
        Execute CLI commands with optional instrument number bypass.
    """
    def __init__(
        self,
        name,
        executable: str = r"C:\claritychrom\bin\claritychrom.exe",
        instrument_number: int = 1,
        startup_time: float = 20,
        startup_method: str = "",
        cmd_timeout: float = 3,
        user: str = "admin",
        password: str = "",
        cfg_file: str = "",
    ) -> None:
        """
        Constructs all the necessary attributes for the Clarity object.

        Parameters:
        -----------
        name : str
            The name of the Clarity instance.
        executable : str, optional
            Path to the ClarityChrom executable (default is r"C:\claritychrom\bin\claritychrom.exe").
        instrument_number : int, optional
            The instrument number to control (default is 1).
        startup_time : float, optional
            The time to wait for ClarityChrom to start up and become responsive (default is 20 seconds).
        startup_method : str, optional
            The startup method to use (default is an empty string).
        cmd_timeout : float, optional
            The timeout duration for command execution (default is 3 seconds).
        user : str, optional
            The username for ClarityChrom (default is "admin").
        password : str, optional
            The password for ClarityChrom (default is an empty string).
        cfg_file : str, optional (PATH\FILENAME)
            The configuration file for ClarityChrom (default is an empty string).
        """
        super().__init__(name=name)
        # Metadata
        self.device_info.authors = [jakob, wei_hsin]
        self.device_info.manufacturer = "DataApex"
        self.device_info.model = "Clarity Chromatography"

        # Validate executable
        if which(executable):
            self.executable = executable
        else:
            assert '"' not in executable
            self.executable = f'"{executable}"'
        assert which(executable) or Path(executable).is_file(), "Valid executable found"

        # Save instance variables
        self.instrument = instrument_number
        self.startup_time = startup_time
        self.cmd_timeout = cmd_timeout

        # Pre-form initialization command to avoid passing tons of vars to initialize()
        self._init_command = ""
        self._init_command += f" cfg={cfg_file}" if cfg_file else ""
        self._init_command += f" u={user}" if user else ""
        self._init_command += f" p={password}" if password else ""
        self._init_command += f' "{startup_method}"'

    async def initialize(self):
        """Start ClarityChrom and wait for it to be responsive."""
        await self.execute_command(self._init_command)
        logger.info(f"Clarity startup: waiting {self.startup_time} seconds")
        await asyncio.sleep(self.startup_time)
        self.components.append(ClarityComponent(name="clarity", hw_device=self))

    async def execute_command(self, command: str, without_instrument_num: bool = False):
        """
        Execute ClarityChrom CLI command with timeout handling.

        Commands in string format that are accepted by the device.
        There is a list of the command available.
        (See more detail in the documentation and/or the manual reference)

        Parameters:
        -----------
        command : str
            Command string to execute (without instrument specification).
        without_instrument_num : bool
            Skip adding instrument number parameter (for global commands).

        Returns:
        --------
        bool
            True if command completed successfully, False on timeout.
        """
        if without_instrument_num:
            cmd_string = self.executable + f" {command}"
        else:
            cmd_string = self.executable + f" i={self.instrument} {command}"

        logger.debug(f"Executing Clarity command `{command}`")
        process = await asyncio.create_subprocess_shell(cmd_string)
        try:
            await asyncio.wait_for(process.wait(), timeout=self.cmd_timeout)
            return True
        except TimeoutError:
            logger.error(f"Subprocess timeout expired (timeout = {self.cmd_timeout} s)")
            return False
