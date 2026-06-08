"""Heidolph MR Hei-Connect magnetic stirrer control."""

from __future__ import annotations

import asyncio
import time
from typing import Literal

import aioserial
import pint
from loguru import logger

from flowchem.components.device_info import DeviceInfo
from flowchem.devices.flowchem_device import FlowchemDevice, RepeatedTaskInfo
from flowchem.devices.heidolph.hei_connect_components import (
    HeatingMode,
    HeiConnectControl,
    HeiConnectStirringControl,
    HeiConnectTemperatureControl,
    TemperatureControlMode,
)
from flowchem.utils.exceptions import DeviceError, InvalidConfigurationError
from flowchem.utils.people import dario, jakob, wei_hsin

Status = Literal[
    "manual",
    "remote-start",
    "remote-stop",
    "remote-blocked",
    "error",
]


class HeiConnectBase(FlowchemDevice):
    """Shared Heidolph MR Hei-Connect behavior."""

    STATUS_MAP = {
        0: "manual",
        1: "remote-start",
        2: "remote-stop",
        -1: "remote-blocked",
    }

    def __init__(self, name="", connection_check: bool = True) -> None:
        super().__init__(name)
        self.connection_check = connection_check
        self.device_info = DeviceInfo(
            authors=[dario, jakob, wei_hsin],
            manufacturer="Heidolph",
            model="MR Hei-Connect",
        )

    async def initialize(self):
        """Set up communication and expose FlowChem components."""
        await self._send_checked("PA_NEW", "PA_NEW")
        self.device_info.version = await self.software_version()
        if not self.device_info.version:
            raise InvalidConfigurationError(
                "No software version received from MR Hei-Connect!"
            )

        await self.status()
        if self.connection_check:
            await self._send_checked("CC_ON", "CC_ON")

        self.components.append(HeiConnectStirringControl("stirring-control", self))
        self.components.append(
            HeiConnectTemperatureControl("temperature-control", self)
        )
        self.components.append(HeiConnectControl("control", self))

    def repeated_task(self):
        if not self.connection_check:
            return None

        async def keepalive():
            await self.status()

        return [RepeatedTaskInfo(seconds_every=5, task=keepalive)]

    async def _send_command(self, command: str) -> str:
        raise NotImplementedError

    async def _send_checked(self, command: str, expected_prefix: str) -> str:
        reply = await self._send_command(command)
        if not reply.startswith(expected_prefix):
            raise DeviceError(f"Unexpected reply to `{command}`: `{reply}`")
        return reply

    @staticmethod
    def _value_from_reply(reply: str, prefix: str) -> str:
        if not reply.startswith(prefix):
            raise DeviceError(
                f"Unexpected reply: `{reply}` does not start with `{prefix}`"
            )
        return reply[len(prefix) :].strip()

    async def _get_float(self, command: str) -> float:
        reply = await self._send_checked(command, command)
        return float(self._value_from_reply(reply, command))

    async def _get_int(self, command: str) -> int:
        reply = await self._send_checked(command, command)
        return int(float(self._value_from_reply(reply, command)))

    async def software_version(self) -> str:
        return await self._send_command("SW_VERS")

    async def set_temperature(self, temperature: pint.Quantity) -> bool:
        value = int(round(temperature.m_as("degC")))
        await self._send_checked(f"OUT_SP_1 {value}", "OUT_SP_1")
        return True

    async def get_temperature(self) -> float:
        mode = await self.get_temperature_control_mode()
        return await self._get_float(
            "IN_PV_1" if mode == "external-sensor" else "IN_PV_3"
        )

    async def get_temperature_setpoint(self) -> float:
        return await self._get_float("IN_SP_1")

    async def start_heating(self) -> bool:
        await self._send_checked("START_1", "START_1")
        return True

    async def stop_heating(self) -> bool:
        await self._send_checked("STOP_1", "STOP_1")
        return True

    async def is_temperature_target_reached(self) -> bool:
        return (
            abs(await self.get_temperature() - await self.get_temperature_setpoint())
            < 1
        )

    async def get_heating_mode(self) -> HeatingMode:
        mode = await self._get_int("IN_MODE_4")
        if mode == 0:
            return "precise"
        if mode == 1:
            return "fast"
        raise DeviceError(f"Unknown heating mode `{mode}`")

    async def set_heating_mode(self, mode: HeatingMode) -> bool:
        mode_value = {"precise": 0, "fast": 1}[mode]
        await self._send_checked(f"OUT_MODE_4 {mode_value}", "IN_MODE_4")
        return True

    async def get_temperature_control_mode(self) -> TemperatureControlMode:
        mode = await self._get_int("IN_MODE_1")
        if mode == 0:
            return "hotplate"
        if mode == 1:
            return "external-sensor"
        raise DeviceError(f"Unknown temperature control mode `{mode}`")

    async def set_speed(self, speed: pint.Quantity) -> bool:
        value = int(round(speed.m_as("rpm")))
        await self._send_checked(f"OUT_SP_3 {value}", "OUT_SP_3")
        return True

    async def get_speed(self) -> float:
        return await self._get_float("IN_PV_5")

    async def get_speed_setpoint(self) -> float:
        return await self._get_float("IN_SP_3")

    async def start_stirring(self) -> bool:
        await self._send_checked("START_2", "START_2")
        return True

    async def stop_stirring(self) -> bool:
        await self._send_checked("STOP_2", "STOP_2")
        return True

    async def is_stirring_on(self) -> bool:
        return await self.get_speed() > 0

    async def status(self) -> Status:
        status_code = await self._get_int("STATUS")
        if status_code in self.STATUS_MAP:
            return self.STATUS_MAP[status_code]  # type: ignore
        return "error"


class HeiConnect(HeiConnectBase):
    """Control class for Heidolph MR Hei-Connect magnetic stirrers."""

    DEFAULT_CONFIG = {
        "timeout": 1,
        "baudrate": 9600,
        "parity": aioserial.PARITY_EVEN,
        "stopbits": aioserial.STOPBITS_ONE,
        "bytesize": aioserial.SEVENBITS,
    }
    COMMAND_DELAY = 0.1

    def __init__(
        self, aio: aioserial.AioSerial, name="", connection_check: bool = True
    ) -> None:
        super().__init__(name=name, connection_check=connection_check)
        self._serial = aio
        self._lock = asyncio.Lock()
        self._last_command_at = 0.0

    @classmethod
    def from_config(cls, port, name="", connection_check: bool = True, **serial_kwargs):
        """Create instance from config dict. Used by server to initialize obj from config."""
        configuration = cls.DEFAULT_CONFIG | serial_kwargs
        try:
            serial_object = aioserial.AioSerial(port, **configuration)
        except (OSError, aioserial.SerialException) as serial_exception:
            raise InvalidConfigurationError(
                f"Cannot connect to the Heidolph MR Hei-Connect on the port <{port}>"
            ) from serial_exception

        return cls(serial_object, name=name, connection_check=connection_check)

    async def _send_command(self, command: str) -> str:
        async with self._lock:
            elapsed = time.monotonic() - self._last_command_at
            if elapsed < self.COMMAND_DELAY:
                await asyncio.sleep(self.COMMAND_DELAY - elapsed)

            if hasattr(self._serial, "reset_input_buffer"):
                self._serial.reset_input_buffer()

            await self._serial.write_async(f"{command}\r\n".encode("ascii"))
            self._last_command_at = time.monotonic()
            logger.debug(f"Heidolph command `{command}` sent")

            try:
                reply = await asyncio.wait_for(self._serial.readline_async(), 2)
            except asyncio.TimeoutError:
                raise DeviceError(
                    f"No reply received from MR Hei-Connect for `{command}`"
                )

            decoded_reply = reply.decode("ascii").strip()
            logger.debug(f"Heidolph reply received: {decoded_reply}")
            return decoded_reply


class SimulatedHeiConnect(HeiConnectBase):
    """In-memory Heidolph MR Hei-Connect simulator."""

    def __init__(self, name="", connection_check: bool = True) -> None:
        super().__init__(name=name, connection_check=connection_check)
        self._version = "Simulated MR Hei-Connect 1.0"
        self._temperature_setpoint = 25.0
        self._temperature_hotplate = 25.0
        self._temperature_sample = 25.0
        self._speed_setpoint = 100.0
        self._stirring_on = False
        self._heating_on = False
        self._heating_mode = 1
        self._temperature_control_mode = 0
        self._connection_check_enabled = False

    @classmethod
    def from_config(cls, name="", connection_check: bool = True):
        """Create simulated device from config."""
        return cls(name=name, connection_check=connection_check)

    async def _send_command(self, command: str) -> str:
        parts = command.split()
        command_name = parts[0]
        value = parts[1] if len(parts) > 1 else None

        if command_name == "PA_NEW":
            return "PA_NEW"
        if command_name == "SW_VERS":
            return self._version
        if command_name == "CC_ON":
            self._connection_check_enabled = True
            return "CC_ON"
        if command_name == "CC_OFF":
            self._connection_check_enabled = False
            return "CC_OFF"

        if command_name == "OUT_SP_1" and value is not None:
            self._temperature_setpoint = float(value)
            return f"OUT_SP_1 {self._temperature_setpoint:g}"
        if command_name == "OUT_SP_3" and value is not None:
            self._speed_setpoint = float(value)
            return f"OUT_SP_3 {self._speed_setpoint:g}"
        if command_name == "OUT_MODE_4" and value is not None:
            self._heating_mode = int(value)
            return f"IN_MODE_4 {self._heating_mode}"

        if command_name == "START_1":
            self._heating_on = True
            self._temperature_hotplate = self._temperature_setpoint
            self._temperature_sample = self._temperature_setpoint
            return "START_1"
        if command_name == "STOP_1":
            self._heating_on = False
            return "STOP_1"
        if command_name == "START_2":
            self._stirring_on = True
            return "START_2"
        if command_name == "STOP_2":
            self._stirring_on = False
            return "STOP_2"

        if command_name == "IN_PV_1":
            return f"IN_PV_1 {self._temperature_sample:g}"
        if command_name == "IN_PV_2":
            return f"IN_PV_2 {self._temperature_sample + 25:g}"
        if command_name == "IN_PV_3":
            return f"IN_PV_3 {self._temperature_hotplate:g}"
        if command_name == "IN_PV_4":
            return f"IN_PV_4 {self._temperature_hotplate + 25:g}"
        if command_name == "IN_PV_5":
            speed = self._speed_setpoint if self._stirring_on else 0
            return f"IN_PV_5 {speed:g}"
        if command_name == "IN_SP_1":
            return f"IN_SP_1 {self._temperature_setpoint:g}"
        if command_name == "IN_SP_2":
            return "IN_SP_2 25"
        if command_name == "IN_SP_3":
            return f"IN_SP_3 {self._speed_setpoint:g}"
        if command_name == "IN_MODE_1":
            return f"IN_MODE_1 {self._temperature_control_mode}"
        if command_name == "IN_MODE_2":
            return "IN_MODE_2 0"
        if command_name == "IN_MODE_4":
            return f"IN_MODE_4 {self._heating_mode}"
        if command_name == "STATUS":
            if self._heating_on or self._stirring_on:
                return "STATUS 1"
            return "STATUS 2"
        if command_name == "RESET":
            self._heating_on = False
            self._stirring_on = False
            self._connection_check_enabled = False
            return "RESET"

        raise DeviceError(f"Unsupported simulated Heidolph command `{command}`")
