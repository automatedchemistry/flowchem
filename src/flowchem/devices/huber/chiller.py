"""Huber chiller control driver."""
import asyncio

import aioserial
import pint
from loguru import logger

from flowchem import ureg
from flowchem.components.device_info import DeviceInfo
from flowchem.components.technical.temperature import TempRange
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.huber.huber_temperature_control import HuberTemperatureControl
from flowchem.devices.huber.pb_command import PBCommand
from flowchem.utils.exceptions import InvalidConfigurationError
from flowchem.utils.people import dario, jakob, wei_hsin


class HuberChiller(FlowchemDevice):
    """Control class for Huber chillers."""

    DEFAULT_CONFIG = {
        "timeout": 0.1,
        "baudrate": 9600,
        "parity": aioserial.PARITY_NONE,
        "stopbits": aioserial.STOPBITS_ONE,
        "bytesize": aioserial.EIGHTBITS,
    }

    def __init__(
        self,
        aio: aioserial.AioSerial,
        name="",
        min_temp: float = -150,
        max_temp: float = 250,
    ) -> None:
        super().__init__(name)
        self._serial = aio
        self._min_t: float = min_temp
        self._max_t: float = max_temp

        self.device_info = DeviceInfo(
            authors=[dario, jakob, wei_hsin],
            manufacturer="Huber",
            model="generic chiller",
        )

    @classmethod
    def from_config(cls, port, name=None, **serial_kwargs):
        """Create instance from config dict. Used by server to initialize obj from config.

        Only required parameter is 'port'. Optional 'loop' + others (see AioSerial())
        """
        # Merge default settings, including serial, with provided ones.
        configuration = HuberChiller.DEFAULT_CONFIG | serial_kwargs

        try:
            serial_object = aioserial.AioSerial(port, **configuration)
        except (OSError, aioserial.SerialException) as serial_exception:
            raise InvalidConfigurationError(
                f"Cannot connect to the HuberChiller on the port <{port}>"
            ) from serial_exception

        return cls(serial_object, name)

    async def initialize(self):
        """Ensure the connection w/ device is working."""
        self.device_info.serial_number = str(await self.serial_number())
        if self.device_info.serial_number == "0":
            raise InvalidConfigurationError("No reply received from Huber Chiller!")
        logger.debug(
            f"Connected with Huber Chiller S/N {self.device_info.serial_number}",
        )

        # Validate temperature limits
        device_limits = await self.temperature_limits()
        if self._min_t < device_limits[0]:
            logger.warning(
                f"The device minimum temperature is higher than the specified minimum temperature!"
                f"The lowest possible temperature will be {device_limits[0]} °C",
            )
            self._min_t = device_limits[0]

        if self._max_t > device_limits[1]:
            logger.warning(
                f"The device maximum temperature is lower than the specified maximum temperature!"
                f"The maximum possible temperature will be {device_limits[1]} °C",
            )
            self._max_t = device_limits[1]

        temperature_range = TempRange(
            min=ureg.Quantity(f"{self._min_t} °C"),
            max=ureg.Quantity(f"{self._max_t} °C"),
        )

        # Set TemperatureControl component.
        self.components.append(
            HuberTemperatureControl("temperature-control", self, temperature_range)
        )

    async def _send_command_and_read_reply(self, command: str) -> str:
        """Send a command to the chiller and read the reply.

        Args:
        ----
            command (str): string to be transmitted

        Returns:
        -------
            str: reply received
        """
        # Send command. Using PBCommand ensure command validation, see PBCommand.to_chiller()
        pb_command = PBCommand(command.upper())
        await self._serial.write_async(pb_command.to_chiller())
        logger.debug(f"Command {command[0:8]} sent!")
        await asyncio.sleep(2)
        # Receive reply and return it after decoding
        try:
            reply = await asyncio.wait_for(self._serial.readline_async(), 1)
        except asyncio.TimeoutError:
            logger.error("No reply received! Unsupported command?")
            return ""

        logger.debug(f"Reply received: {reply}")
        return reply.decode("ascii")

    async def get_temperature(self) -> float:
        """Get temperature. Process preferred, otherwise internal."""
        # if process_t := await self.process_temperature():
        #     return process_t
        return await self.internal_temperature()  # type: ignore

    async def get_temperature_setpoint(self) -> float | None:
        """Return the set point used by temperature controller. Internal if not probe, otherwise process temp."""
        reply = await self._send_command_and_read_reply("{M00****")
        return PBCommand(reply).parse_temperature()

    async def set_temperature(self, temp: pint.Quantity):
        """Set the set point used by temperature controller. Internal if not probe, otherwise process temp."""
        await self._send_command_and_read_reply("{M00" + self._temp_to_string(temp))

    async def target_reached(self) -> bool:
        """Trivially implemented as delta(currentT-setT) < 1°C."""
        current_t = await self.get_temperature()
        set_t = await self.get_temperature_setpoint()
        if set_t:
            return abs(current_t - set_t) < 1
        return False

    async def internal_temperature(self) -> float | None:
        """Return internal temp (bath temperature)."""
        reply = await self._send_command_and_read_reply("{M01****")
        return PBCommand(reply).parse_temperature()

    async def process_temperature(self) -> float | None:
        """Return the current process temperature. If not T probe, the temperature is None."""
        reply = await self._send_command_and_read_reply("{M07****")

        return PBCommand(reply).parse_temperature()

    async def temperature_limits(self) -> tuple[float, float]:
        """Return minimum/maximum accepted value for the temperature setpoint (in Celsius)."""
        min_reply = await self._send_command_and_read_reply("{M30****")
        min_t = PBCommand(min_reply).parse_temperature()
        max_reply = await self._send_command_and_read_reply("{M31****")
        max_t = PBCommand(max_reply).parse_temperature()
        return min_t, max_t

    async def serial_number(self) -> int:
        """Get serial number."""
        serial1 = await self._send_command_and_read_reply("{M1B****")
        serial2 = await self._send_command_and_read_reply("{M1C****")
        pb1, pb2 = PBCommand(serial1), PBCommand(serial2)
        if pb1.data and pb2.data:
            return int(pb1.data + pb2.data, 16)
        else:
            return 0

    @staticmethod
    def _temp_to_string(temp: pint.Quantity) -> str:
        """From temperature to string for command. f^-1 of PCommand.parse_temperature."""
        assert (
            ureg.Quantity("-151 °C") <= temp <= ureg.Quantity("327 °C")
        ), "Protocol temperature limits"
        # Hexadecimal two's complement
        return f"{int(temp.m_as('°C') * 100) & 65535:04X}"

    @staticmethod
    def _int_to_string(number: int) -> str:
        """From int to string for command. f^-1 of PCommand.parse_integer."""
        return f"{number:04X}"

    # async def return_temperature(self) -> float | None:
    #     """Return the temp of the thermal fluid flowing back to the device."""
    #     reply = await self._send_command_and_read_reply("{M02****")
    #     return PBCommand(reply).parse_temperature()
    #
    # async def pump_pressure(self) -> str:
    #     """Return the pump pressure in mbar (note that you probably want barg, i.e. to remove 1 bar)."""
    #     reply = await self._send_command_and_read_reply("{M03****")
    #     pressure = PBCommand(reply).parse_integer()
    #     return str(ureg(f"{pressure} mbar"))
    #
    # async def current_power(self) -> str:
    #     """Return the current power in Watts (negative for cooling, positive for heating)."""
    #     reply = await self._send_command_and_read_reply("{M04****")
    #     power = PBCommand(reply).parse_integer()
    #     return str(ureg(f"{power} watt"))
    #
    # async def status(self) -> dict[str, bool]:
    #     """Return the info contained in `vstatus1` as dict."""
    #     reply = await self._send_command_and_read_reply("{M0A****")
    #     return PBCommand(reply).parse_status1()
    #
    # async def status2(self) -> dict[str, bool]:
    #     """Return the info contained in `vstatus2` as dict."""
    #     reply = await self._send_command_and_read_reply("{M3C****")
    #     return PBCommand(reply).parse_status2()
    #
    # async def is_temperature_control_active(self) -> bool:
    #     """Return whether temperature control is active or not."""
    #     reply = await self._send_command_and_read_reply("{M14****")
    #     return PBCommand(reply).parse_boolean()
    #
    # async def is_circulation_active(self) -> bool:
    #     """Return whether temperature control is active or not."""
    #     reply = await self._send_command_and_read_reply("{M16****")
    #     return PBCommand(reply).parse_boolean()
    #
    # async def start_circulation(self):
    #     """Start circulation pump."""
    #     await self._send_command_and_read_reply("{M160001")
    #
    # async def stop_circulation(self):
    #     """Stop circulation pump."""
    #     await self._send_command_and_read_reply("{M160000")
    #
    # async def pump_speed(self) -> str:
    #     """Return current circulation pump speed (in rpm)."""
    #     reply = await self._send_command_and_read_reply("{M26****")
    #     return PBCommand(reply).parse_rpm()
    #
    # async def pump_speed_setpoint(self) -> str:
    #     """Return the set point of the circulation pump speed (in rpm)."""
    #     reply = await self._send_command_and_read_reply("{M48****")
    #     return PBCommand(reply).parse_rpm()
    #
    # async def set_pump_speed(self, rpm: str):
    #     """Set the pump speed, in rpm. See device display for range."""
    #     parsed_rpm = ureg(rpm)
    #     await self._send_command_and_read_reply(
    #         "{M48" + self._int_to_string(parsed_rpm.m_as("rpm"))
    #     )
    #
    # async def cooling_water_temp(self) -> float | None:
    #     """Return the cooling water inlet temperature (in Celsius)."""
    #     reply = await self._send_command_and_read_reply("{M2C****")
    #     return PBCommand(reply).parse_temperature()
    #
    # async def cooling_water_pressure(self) -> float | None:
    #     """Return the cooling water inlet pressure (in mbar)."""
    #     reply = await self._send_command_and_read_reply("{M2D****")
    #     if pressure := PBCommand(reply).parse_integer() == 64536:
    #         return None
    #     return pressure
    #
    # async def cooling_water_temp_outflow(self) -> float | None:
    #     """Return the cooling water outlet temperature (in Celsius)."""
    #     reply = await self._send_command_and_read_reply("{M4C****")
    #     return PBCommand(reply).parse_temperature()
    #
    # async def alarm_max_internal_temp(self) -> float | None:
    #     """Return the max internal temp before the alarm is triggered and a fault generated."""
    #     reply = await self._send_command_and_read_reply("{M51****")
    #     return PBCommand(reply).parse_temperature()
    #
    # async def set_alarm_max_internal_temp(self, set_temp: str):
    #     """Set the max internal temp before the alarm is triggered and a fault generated."""
    #     temp = ureg(set_temp)
    #     await self._send_command_and_read_reply("{M51" + self._temp_to_string(temp))
    #
    # async def alarm_min_internal_temp(self) -> float | None:
    #     """Return the min internal temp before the alarm is triggered and a fault generated."""
    #     reply = await self._send_command_and_read_reply("{M52****")
    #     return PBCommand(reply).parse_temperature()
    #
    # async def set_alarm_min_internal_temp(self, set_temp: str):
    #     """Set the min internal temp before the alarm is triggered and a fault generated."""
    #     temp = ureg(set_temp)
    #     await self._send_command_and_read_reply("{M52" + self._temp_to_string(temp))
    #
    # async def alarm_max_process_temp(self) -> float | None:
    #     """Return the max process temp before the alarm is triggered and a fault generated."""
    #     reply = await self._send_command_and_read_reply("{M53****")
    #     return PBCommand(reply).parse_temperature()
    #
    # async def set_alarm_max_process_temp(self, set_temp: str):
    #     """Set the max process temp before the alarm is triggered and a fault generated."""
    #     temp = ureg(set_temp)
    #     await self._send_command_and_read_reply("{M53" + self._temp_to_string(temp))
    #
    # async def alarm_min_process_temp(self) -> float | None:
    #     """Return the min process temp before the alarm is triggered and a fault generated."""
    #     reply = await self._send_command_and_read_reply("{M54****")
    #     return PBCommand(reply).parse_temperature()
    #
    # async def set_alarm_min_process_temp(self, set_temp: str):
    #     """Set the min process temp before the alarm is triggered and a fault generated."""
    #     temp = ureg(set_temp)
    #     await self._send_command_and_read_reply("{M54" + self._temp_to_string(temp))
    #
    # async def set_ramp_duration(self, ramp_time: str):
    #     """Set the duration (in seconds) of a ramp to the temperature set by a later call to ramp_to_temperature."""
    #     parsed_time = ureg(ramp_time)
    #     await self._send_command_and_read_reply(
    #         "{M59" + self._int_to_string(parsed_time.m_as("s"))
    #     )
    #
    # async def ramp_to_temperature(self, temperature: str):
    #     """Set the duration (in seconds) of a ramp to the temperature set by a later call to start_ramp()."""
    #     temp = ureg(temperature)
    #     await self._send_command_and_read_reply("{M5A" + self._temp_to_string(temp))
    #
    # async def is_venting(self) -> bool:
    #     """Whether the chiller is venting or not."""
    #     reply = await self._send_command_and_read_reply("{M6F****")
    #     return PBCommand(reply).parse_boolean()
    #
    # async def start_venting(self):
    #     """Start venting. ONLY USE DURING SETUP! READ THE MANUAL!"""
    #     await self._send_command_and_read_reply("{M6F0001")
    #
    # async def stop_venting(self):
    #     """Stop venting."""
    #     await self._send_command_and_read_reply("{M6F0000")
    #
    # async def is_draining(self) -> bool:
    #     """Whether the chiller is venting or not."""
    #     reply = await self._send_command_and_read_reply("{M70****")
    #     return PBCommand(reply).parse_boolean()
    #
    # async def start_draining(self):
    #     """Start venting. ONLY USE DURING SHUT DOWN! READ THE MANUAL!"""
    #     await self._send_command_and_read_reply("{M700001")
    #
    # async def stop_draining(self):
    #     """Stop venting."""
    #     await self._send_command_and_read_reply("{M700000")


if __name__ == "__main__":
    device = HuberChiller(aioserial.AioSerial(port="COM13"))

    async def main(chiller):
        await chiller.initialize()
        print(f"S/N is {await chiller.serial_number()}")

    asyncio.run(main(device))


    import flowchem