"""FlowChem components for Heidolph MR Hei-Connect."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, cast

import pint
from flowchem import ureg
from flowchem.components.flowchem_component import FlowchemComponent
from flowchem.components.technical.stirring import StirringControl
from flowchem.components.technical.temperature import TemperatureControl, TempRange

if TYPE_CHECKING:
    from flowchem.devices.heidolph.hei_connect import HeiConnectBase


HeatingMode = Literal["precise", "fast"]
TemperatureControlMode = Literal["hotplate", "external-sensor"]


class HeiConnectStirringControl(StirringControl):
    """Stirring control component for the Heidolph MR Hei-Connect."""

    hw_device: HeiConnectBase

    async def set_speed(self, speed: str) -> bool:
        """Set the stirring speed using a string in rpm."""
        set_speed = cast(pint.Quantity, await super().set_speed(speed))
        return await self.hw_device.set_speed(set_speed)

    async def get_speed(self) -> float:
        """Return current stirring speed in rpm."""
        return await self.hw_device.get_speed()

    async def get_speed_setpoint(self) -> float:
        """Return stirring speed setpoint in rpm."""
        return await self.hw_device.get_speed_setpoint()

    async def power_on(self) -> bool:
        return await self.hw_device.start_stirring()

    async def power_off(self) -> bool:
        return await self.hw_device.stop_stirring()

    async def is_on(self) -> bool:
        """Return whether stirring is active."""
        return await self.hw_device.is_stirring_on()


class HeiConnectTemperatureControl(TemperatureControl):
    """Temperature control component for the Heidolph MR Hei-Connect."""

    hw_device: HeiConnectBase

    def __init__(self, name: str, hw_device: HeiConnectBase) -> None:
        super().__init__(
            name,
            hw_device,
            TempRange(
                min=ureg.Quantity("20 degC"),
                max=ureg.Quantity("300 degC"),
            ),
        )
        self.add_api_route(
            "/temperature-setpoint", self.get_temperature_setpoint, methods=["GET"]
        )
        self.add_api_route("/heating-mode", self.get_heating_mode, methods=["GET"])
        self.add_api_route("/heating-mode", self.set_heating_mode, methods=["PUT"])
        self.add_api_route(
            "/temperature-control-mode",
            self.get_temperature_control_mode,
            methods=["GET"],
        )

    async def set_temperature(self, temp: str) -> bool:
        """Set the target temperature to the given string in "magnitude and (optional - unit degC)" format."""
        try:
            float(temp)
        except ValueError:
            pass
        else:
            temp = f"{temp} degC"
        set_t = cast(pint.Quantity, await super().set_temperature(temp))
        return await self.hw_device.set_temperature(set_t)

    async def get_temperature(self) -> float:
        """Return temperature in Celsius."""
        return await self.hw_device.get_temperature()

    async def get_temperature_setpoint(self) -> float:
        """Return temperature in Celsius."""
        return await self.hw_device.get_temperature_setpoint()

    async def power_on(self) -> bool:
        return await self.hw_device.start_heating()

    async def power_off(self) -> bool:
        return await self.hw_device.stop_heating()

    async def is_target_reached(self) -> bool:
        return await self.hw_device.is_temperature_target_reached()

    async def get_heating_mode(self) -> HeatingMode:
        """Get the heating mode.
        precise - ptsensor
        fast - hotplate
        """
        return await self.hw_device.get_heating_mode()

    async def set_heating_mode(self, mode: HeatingMode) -> bool:
        """Set the heating mode.
        precise - ptsensor
        fast - hotplate
        """
        return await self.hw_device.set_heating_mode(mode)

    async def get_temperature_control_mode(self) -> TemperatureControlMode:
        """Return the current temperature control mode.
        hotplate or external-sensor
        """
        return await self.hw_device.get_temperature_control_mode()


class HeiConnectControl(FlowchemComponent):
    """Device-level control and status component for the Heidolph MR Hei-Connect."""

    hw_device: HeiConnectBase

    def __init__(self, name: str, hw_device: HeiConnectBase) -> None:
        super().__init__(name, hw_device)
        self.add_api_route("/status", self.status, methods=["GET"])
        self.add_api_route("/software-version", self.software_version, methods=["GET"])

    async def status(self) -> str:
        return await self.hw_device.status()

    async def software_version(self) -> str:
        return await self.hw_device.software_version()
