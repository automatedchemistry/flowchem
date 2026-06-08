"""Tests for Heidolph MR Hei-Connect support."""

import pytest

from flowchem import ureg
from flowchem.devices.heidolph import HeiConnect, SimulatedHeiConnect
from flowchem.utils.exceptions import DeviceError


class FakeHeiConnectSerial:
    """Small stateful fake for the MR Hei-Connect serial protocol."""

    def __init__(self) -> None:
        self.commands: list[bytes] = []
        self.last_command = ""
        self.temperature_setpoint = 25.0
        self.temperature_hotplate = 25.0
        self.temperature_sample = 25.0
        self.speed_setpoint = 100.0
        self.stirring_on = False
        self.heating_on = False
        self.heating_mode = 1
        self.temperature_control_mode = 0
        self.connection_check = False
        self.forced_reply: bytes | None = None

    def reset_input_buffer(self):
        pass

    async def write_async(self, text: bytes):
        self.commands.append(text)
        self.last_command = text.decode("ascii").strip()

    async def readline_async(self, size: int = -1) -> bytes:
        if self.forced_reply is not None:
            return self.forced_reply
        return self._reply(self.last_command).encode("ascii") + b"\r\n"

    def _reply(self, command: str) -> str:
        parts = command.split()
        command_name = parts[0]
        value = parts[1] if len(parts) > 1 else None

        if command_name == "PA_NEW":
            return "PA_NEW"
        if command_name == "SW_VERS":
            return "MR Hei-Connect V1.23"
        if command_name == "CC_ON":
            self.connection_check = True
            return "CC_ON"
        if command_name == "OUT_SP_1" and value is not None:
            self.temperature_setpoint = float(value)
            return f"OUT_SP_1 {self.temperature_setpoint:g}"
        if command_name == "OUT_SP_3" and value is not None:
            self.speed_setpoint = float(value)
            return f"OUT_SP_3 {self.speed_setpoint:g}"
        if command_name == "OUT_MODE_4" and value is not None:
            self.heating_mode = int(value)
            return f"IN_MODE_4 {self.heating_mode}"
        if command_name == "START_1":
            self.heating_on = True
            self.temperature_hotplate = self.temperature_setpoint
            self.temperature_sample = self.temperature_setpoint
            return "START_1"
        if command_name == "STOP_1":
            self.heating_on = False
            return "STOP_1"
        if command_name == "START_2":
            self.stirring_on = True
            return "START_2"
        if command_name == "STOP_2":
            self.stirring_on = False
            return "STOP_2"
        if command_name == "IN_PV_1":
            return f"IN_PV_1 {self.temperature_sample:g}"
        if command_name == "IN_PV_3":
            return f"IN_PV_3 {self.temperature_hotplate:g}"
        if command_name == "IN_PV_5":
            speed = self.speed_setpoint if self.stirring_on else 0
            return f"IN_PV_5 {speed:g}"
        if command_name == "IN_SP_1":
            return f"IN_SP_1 {self.temperature_setpoint:g}"
        if command_name == "IN_SP_3":
            return f"IN_SP_3 {self.speed_setpoint:g}"
        if command_name == "IN_MODE_1":
            return f"IN_MODE_1 {self.temperature_control_mode}"
        if command_name == "IN_MODE_4":
            return f"IN_MODE_4 {self.heating_mode}"
        if command_name == "STATUS":
            if self.stirring_on or self.heating_on:
                return "STATUS 1"
            return "STATUS 2"
        raise AssertionError(f"Unexpected command: {command}")


def fake_device(connection_check: bool = True) -> HeiConnect:
    device = HeiConnect(
        FakeHeiConnectSerial(), name="hei-test", connection_check=connection_check
    )
    device.COMMAND_DELAY = 0
    return device


async def test_initialization_uses_extended_protocol_and_does_not_start():
    device = fake_device()
    await device.initialize()

    assert device.device_info.version == "MR Hei-Connect V1.23"
    assert [component.name for component in device.components] == [
        "stirring-control",
        "temperature-control",
        "control",
    ]
    assert device._serial.commands == [  # type: ignore[attr-defined]
        b"PA_NEW\r\n",
        b"SW_VERS\r\n",
        b"STATUS\r\n",
        b"CC_ON\r\n",
    ]
    assert not device._serial.stirring_on  # type: ignore[attr-defined]
    assert not device._serial.heating_on  # type: ignore[attr-defined]


async def test_serial_command_encoding_and_response_validation():
    device = fake_device(connection_check=False)

    assert await device.status() == "remote-stop"
    assert device._serial.commands[-1] == b"STATUS\r\n"  # type: ignore[attr-defined]

    device._serial.forced_reply = b"NOT_STATUS 2\r\n"  # type: ignore[attr-defined]
    with pytest.raises(DeviceError):
        await device.status()


async def test_stirring_component_validates_and_delegates():
    device = fake_device(connection_check=False)
    await device.initialize()
    stirring = device.components[0]

    assert await stirring.set_speed("5000 rpm")
    assert await device.get_speed_setpoint() == 1400
    assert not await stirring.is_on()

    assert await stirring.power_on()
    assert await stirring.is_on()
    assert await stirring.get_speed() == 1400

    assert await stirring.power_off()
    assert not await stirring.is_on()


async def test_temperature_component_validates_modes_and_delegates():
    device = fake_device(connection_check=False)
    await device.initialize()
    temperature = device.components[1]

    assert await temperature.set_temperature("500 degC")
    assert await temperature.get_temperature_setpoint() == 300

    assert await temperature.set_heating_mode("precise")
    assert await temperature.get_heating_mode() == "precise"
    assert await temperature.get_temperature_control_mode() == "hotplate"

    assert await temperature.power_on()
    assert await temperature.is_target_reached()
    assert await temperature.power_off()


async def test_simulated_hei_connect_exposes_same_components_without_serial():
    device = SimulatedHeiConnect(name="hei-sim")
    await device.initialize()

    components = {component.name: component for component in device.components}
    assert sorted(components) == ["control", "stirring-control", "temperature-control"]

    stirring = components["stirring-control"]
    temperature = components["temperature-control"]
    control = components["control"]

    assert await stirring.set_speed("250 rpm")
    assert await stirring.get_speed_setpoint() == 250
    assert not await stirring.is_on()
    assert await stirring.power_on()
    assert await stirring.get_speed() == 250

    assert await temperature.set_temperature("80 degC")
    assert await temperature.get_temperature_setpoint() == 80
    assert await temperature.set_heating_mode("fast")
    assert await temperature.get_heating_mode() == "fast"
    assert await temperature.get_temperature_control_mode() == "hotplate"

    assert await control.status() == "remote-start"
    assert await control.software_version() == "Simulated MR Hei-Connect 1.0"


@pytest.mark.Heidolph
async def test_hardware_smoke_does_not_start_heating_or_stirring():
    device = HeiConnect.from_config(port="COM1", name="hei-connect")
    await device.initialize()

    assert await device.software_version()
    assert await device.status() in {
        "manual",
        "remote-start",
        "remote-stop",
        "remote-blocked",
        "error",
    }
    assert await device.set_speed(ureg.Quantity("100 rpm"))
    assert await device.set_temperature(ureg.Quantity("20 degC"))
