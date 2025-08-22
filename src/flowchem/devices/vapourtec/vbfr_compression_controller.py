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

from flowchem.devices.vapourtec.vbfr_components_control import VbfrPressureControl, VbfrBodySensor

try:
    # noinspection PyUnresolvedReferences
    from flowchem_vapourtec import VapourtecVBFRCommands

    HAS_VAPOURTEC_COMMANDS = True
except ImportError:
    HAS_VAPOURTEC_COMMANDS = False


class VBFReactor(FlowchemDevice):
    """column compression control class from Vapourtec."""

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

        # physical operating limitation
        self.lowerPressDiff = 0.01  # in bar
        self.higherPressDiff = 9

        # follows previous setting
        self.lowerPoslimit = None
        self.upperPoslimit = None
        self.lowerDblimit = None
        self.upperDblimit = None

        self.column_size = column
        self.column_dic = {"0": "6.6 mm", "1": "10 mm", "2": "15 mm", "3": "35 mm"}

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
        configuration = VBFReactor.DEFAULT_CONFIG | config
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
            model="variable bed flow reactor module",
        )

    async def initialize(self):
        """Ensure connection."""
        self.device_info.version = await self.version()
        logger.info(f"Connected with variable bed flow reactor version {self.device_info.version}")

        await self.set_column_size(self.column_size)
        logger.debug(f"{self.column_size} is set.")
        await self.get_position_limit()
        logger.info(f"Position range: {self.lowerPoslimit} to {self.upperPoslimit} mm.")
        await self.get_deadband()
        logger.info(f"Deadband range: lower {self.lowerDblimit} to upper {self.upperDblimit} mbar.")

        self.components.extend([VbfrPressureControl("PressureControl", self),
                                VbfrBodySensor("BodySensor", self)])

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
            msg = "No response received from VBFR module!"
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
                return VBFReactor.Status._make(raw_status.split(","))
            except InvalidConfigurationError as ex:
                failure += 1
                if failure > 3:
                    raise ex

    async def get_position_limit(self):
        """Get upper and lower setting limit of position."""
        state = await self.get_status()
        self.upperPoslimit = float(state.UpperLimitMm)
        self.lowerPoslimit = float(state.LowerLimitMm)
        return self.upperPoslimit, self.lowerPoslimit

    async def set_position_limit(self, upper: float = None, lower: float = None):
        """Set the upper & lower limit of the position (in mm)"""
        s_upper = self.upperPoslimit if upper is None else upper
        s_lower = self.lowerPoslimit if lower is None else lower
        cmd = self.cmd.SET_POSITION_LIMITS.format(lower=s_lower, upper=s_upper)
        await self.write_and_read_reply(cmd)

    async def get_position(self) -> float:
        """Get position (in mm) of variable bed flow reactor"""
        return float(await self.write_and_read_reply(self.cmd.GET_POSITION))

    async def calibrate_position(self):
        """set current position to zero"""
        await self.write_and_read_reply(self.cmd.ZERO_CURRENT_POSITION)

    async def get_column_size(self) -> str:
        """Get inner diameter of VBFR column"""
        state = await self.get_status()
        return self.column_dic[state.ColumnSize]

    async def set_column_size(self, column_size: str = "6.6 mm"):
        """Acceptable column size: [6.6 mm, 10 mm, 15 mm, 35 mm]"""
        rev_col_dic = {v: k for k, v in self.column_dic.items()}
        if not column_size in rev_col_dic:
            raise DeviceError(f"{column_size} column cannot be used on VBFR."
                              f"Please change to one of the following: {list(rev_col_dic.keys())}")
        await self.write_and_read_reply(self.cmd.SET_COLUMN_SIZE.format(column_number=rev_col_dic[column_size]))

    async def get_target_pressure_difference(self) -> int:
        """Get set pressure difference (in mbar) of VBFR column"""
        state = await self.get_status()
        return state.RegDiffPressMbar

    async def get_current_pressure_difference(self) -> int:
        """Get current pressure difference (in mbar)"""
        state = await self.get_status()
        return state.ColumnDiffPressureMbar

    async def calibrate_pressure(self) -> bool:
        """Get current pressure to zero"""
        await self.write_and_read_reply(self.cmd.CALIB_PRESSURE)
        return True

    async def set_pressure_difference(self, pressure: float):
        """set pressure differnence in bar"""
        if self.lowerPressDiff <= pressure <= self.higherPressDiff:
            s_pressure = pressure
        elif pressure <= self.lowerPressDiff:
            s_pressure = self.lowerPressDiff
        else:
            s_pressure = self.higherPressDiff
        await self.write_and_read_reply(self.cmd.SET_DIFF_PRESSURE.format(pressure=s_pressure))

    async def get_deadband(self):
        """get up and down deadband in mbar"""
        state = await self.get_status()
        self.lowerDblimit = int(state.RegDeadBandLower)
        self.upperDblimit = int(state.RegDeadBandUpper)
        return self.upperDblimit, self.lowerDblimit

    async def set_deadband(self, up: int = None, down: int = None):
        """
        Deadband is the up & down acceptable offset from required pressure difference.
        Set upper & lower beadband in mbar
        """
        s_up = self.upperDblimit if up is None else up
        s_down = self.lowerDblimit if down is None else down
        await self.write_and_read_reply(self.cmd.SET_DEADBAND.format(up=s_up, down=s_down))

    async def power_on(self):
        """Turn on position sensor."""
        await self.write_and_read_reply(self.cmd.POWER_ON)

    async def power_off(self):
        """Turn off channel."""
        await self.write_and_read_reply(self.cmd.POWER_OFF)


if __name__ == "__main__":
    import asyncio

    vbfr_device = VBFReactor(port="COM15")
    async def main(device):
        """Test function."""
        await device.initialize()
        await device.calibrate_position()
        print(f"target pressure difference: {await device.get_target_pressure_difference()} mbar")
        print(f"current pressure difference: {await device.get_current_pressure_difference()} mm")
        print(f"column size {await device.get_column_size()}")

    asyncio.run(main(vbfr_device))
    asyncio.run(vbfr_device.power_on())