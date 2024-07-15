"""
Variable Bed Flow Reactor (VBFR)
# fixme : the ureg should be used
"""

from __future__ import annotations

from collections import namedtuple
from collections.abc import Iterable

import aioserial
import pint
from loguru import logger

from flowchem import ureg
from flowchem.components.device_info import DeviceInfo
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.utils.exceptions import InvalidConfigurationError, DeviceError
from flowchem.utils.people import wei_hsin

try:
    # noinspection PyUnresolvedReferences
    from flowchem_vapourtec import VapourtecVBFRCommands

    HAS_VAPOURTEC_COMMANDS = True
except ImportError:
    HAS_VAPOURTEC_COMMANDS = False


class VBFRController(FlowchemDevice):
    """column compression control class."""

    DEFAULT_CONFIG = {
        "timeout": 0.1,
        "baudrate": 9600,
        "parity": aioserial.PARITY_NONE,
        "stopbits": aioserial.STOPBITS_ONE,
        "bytesize": aioserial.EIGHTBITS,
    }

    Status = namedtuple("Status",
                        "CurrentPosMm, UpperLimitMm, LowerLimitMm, "
                        "RegDiffPressMbar, ColumnDiffPressureMbar, "
                        "RegDeadBandUpper, RegDeadBandLower, ColumnSize")

    def __init__(
            self,
            name: str = "",
            column: str = "6.6 mm",
            **config,
    ) -> None:
        super().__init__(name)

        self.lowerPressDiff = 0.01  # in bar
        self.higherPressDiff = 9
        self.lowerPoslimit = None
        self.upperPoslimit = None
        self.lowerDblimit = None
        self.upperDblimit = None
        self.column_size = column

        self.column_dic = {
            "0": "6.6 mm",
            "1": "10 mm",
            "2": "15 mm",
            "3": "35 mm"
        }
        if not HAS_VAPOURTEC_COMMANDS:
            msg = (
                "You tried to use a Vapourtec device but the relevant commands are missing!"
                "Unfortunately, we cannot publish those as they were provided under NDA."
                "Contact Vapourtec for further assistance."
            )
            raise InvalidConfigurationError(
                msg,
            )

        self.cmd = VapourtecVBFRCommands()

        # Merge default settings, including serial, with provided ones.
        configuration = VBFRController.DEFAULT_CONFIG | config
        try:
            self._serial = aioserial.AioSerial(**configuration)
        except aioserial.SerialException as ex:
            msg = f"Cannot connect to the R4Heater on the port <{config.get('port')}>"
            raise InvalidConfigurationError(
                msg,
            ) from ex

        self.device_info = DeviceInfo(
            authors=[wei_hsin],
            manufacturer="Vapourtec",
            model="vbfr reactor module",
        )

    async def initialize(self):
        """Ensure connection."""
        self.device_info.version = await self.version()
        logger.info(f"Connected with variable bed flow reacter version {self.device_info.version}")

        await self.set_column_size("6.6 mm")
        await self.get_position_limit()
        await self.get_deadband()

        # todo add compound

    async def _write(self, command: str):
        """Write a command to the pump."""
        cmd = command + "\r\n"
        await self._serial.write_async(cmd.encode("ascii"))
        logger.debug(f"Sent command: {command!r}")

    async def _read_reply(self) -> str:
        """Read the pump reply from serial communication."""
        reply_string = await self._serial.readline_async()
        logger.debug(f"Reply received: {reply_string.decode('ascii').rstrip()}")
        return reply_string.decode("ascii")

    async def write_and_read_reply(self, command: str) -> str:
        """Send a command to the pump, read the replies and return it, optionally parsed."""
        self._serial.reset_input_buffer()
        await self._write(command)
        logger.debug(f"Command {command} sent to VBFReactor!")
        response = await self._read_reply()

        if not response:
            msg = "No response received from heating module!"
            raise InvalidConfigurationError(msg)

        logger.debug(f"Reply received: {response}")
        return response.rstrip()

    async def version(self):
        """Get firmware version."""
        return await self.write_and_read_reply(self.cmd.VERSION)

    async def get_status(self) -> Status:
        """
        Get status.
        [0.000000,10,-10,9000,0,200,200,0]
        """
        # This command is a bit fragile for unknown reasons.
        failure = 0
        while failure <= 3:
            try:
                raw_status = await self.write_and_read_reply(self.cmd.GET_STATUS.format())
                return VBFRController.Status._make(raw_status.split(","))
            except InvalidConfigurationError as ex:
                failure += 1
                if failure > 3:
                    raise ex

    async def get_position_limit(self):
        state = await self.get_status()
        self.upperlimit = float(state.UpperLimitMm)
        self.lowerlimit = float(state.LowerLimitMm)
        logger.info(f"position limits: from {self.lowerlimit} to {self.upperlimit}")
        return self.lowerlimit, self.upperlimit

    async def set_position_limit(self, upper: float = None, lower: float = None):
        """Set the upper & lower limit of the position (in mm)"""
        s_upper = self.upperlimit if upper is None else upper
        s_lower = self.lowerlimit if lower is None else lower
        cmd = self.cmd.SET_POSITION_LIMITS.format(lower=s_lower, upper=s_upper)
        await self.write_and_read_reply(cmd)

    async def get_position(self) -> float:
        """Get position (in mm) of variable bed flow reactor"""
        return float(await self.write_and_read_reply(self.cmd.GET_POSITION))

    async def get_column_size(self) -> str:
        """Get inner diameter of VBFR column"""
        state = await self.get_status()
        return self.column_dic[state.ColumnSize]

    async def set_column_size(self, column_size: str = "6.6 mm"):
        """Acceptable column size: ['6.6 mm', '10 mm', '15 mm', '35 mm']"""
        rev_col_dic = {v: k for k, v in self.column_dic.items()}
        if not column_size in rev_col_dic:
            raise DeviceError(f"{column_size} column cannot be used on VBFR."
                              f"Please change to one of the following: {list(rev_col_dic.keys())}")
        await self.write_and_read_reply(self.cmd.SET_COLUMN_SIZE.format(column_number=rev_col_dic[column_size]))

    async def get_target_pressure_difference(self):
        """Get set pressure difference (in mbar) of VBFR column"""
        state = await self.get_status()
        return self.column_dic[state.RegDiffPressMbar]

    async def get_current_pressure_difference(self):
        """Get current pressure difference (in mbar)"""
        state = await self.get_status()
        return self.column_dic[state.ColumnDiffPressureMbar]

    async def set_pressure_difference(self, pressure: float):
        """set pressure differnence in bar"""
        if self.lowerPressDiff <= pressure <= self.higherPressDiff:
            s_pressure = pressure

        await self.write_and_read_reply(self.cmd.SET_DIFF_PRESSURE.format(pressure=pressure))

    async def get_deadband(self):
        """get up and down deadband in mbar"""
        state = await self.get_status()
        self.lowerDblimit = int(state.RegDeadBandLower)
        self.upperDblimit = int(state.RegDeadBandUpper)
        return self.lowerDblimit, self.upperDblimit

    async def set_deadband(self, up: int = None, down: int = None):
        """
        Deadband is the up & down acceptable offset from required pressure difference.
        Set upper & lower beadband in mbar
        """
        if self.upperDblimit is None or self.lowerDblimit is None:
            await self.get_deadband()
        s_up = self.upperlimit if up is None else up
        s_down = self.lowerlimit if down is None else down
        await self.write_and_read_reply(self.cmd.SET_POSITION_LIMITS.format(up=s_up, down=s_down))

    async def power_on(self):
        """Turn on channel."""
        await self.write_and_read_reply(self.cmd.POWER_ON)

    async def power_off(self):
        """Turn off channel."""
        await self.write_and_read_reply(self.cmd.POWER_OFF)


if __name__ == "__main__":
    import asyncio

    vbfr_device = VBFRController(port="COM15")


    async def main(heat):
        """Test function."""
        await heat.initialize()
        # Get reactors
        r1, r2, r3, r4 = heat.components()

        await r1.set_temperature("30 °C")
        print(f"Temperature is {await r1.get_temperature()}")


    asyncio.run(main(vbfr_device))
