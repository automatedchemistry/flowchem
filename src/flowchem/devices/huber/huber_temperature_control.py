"""Huber TemperatureControl component."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .chiller import HuberChiller


from flowchem.components.technical.temperature import TemperatureControl


class HuberTemperatureControl(TemperatureControl):
    """
    Temperature control component for Huber Chillers.

    Attributes:
        hw_device (HuberChiller): The hardware device controlling the temperature.
    """
    hw_device: HuberChiller  # for typing's sake

    async def set_temperature(self, temp: str):
        """
        Set the target temperature to the given value.

        Args:
            temp (str): The desired temperature as a string in "magnitude and unit" format (scalar + unit), e.g. "7 °C"

        Returns:
            bool: True if the temperature was successfully set, False otherwise.
        """
        set_t = await super().set_temperature(temp)
        return await self.hw_device.set_temperature(set_t)

    async def get_temperature(self) -> float:
        """
        Get the current temperature.

        Returns:
            float: The current temperature in Celsius.
        """
        return await self.hw_device.get_temperature()

    async def is_target_reached(self) -> bool:
        """
        Check if the set temperature target has been reached.

        Returns:
            bool: True if the target temperature has been reached, False otherwise.
        """
        return await self.hw_device.target_reached()

    async def power_on(self):
        """
        Turn on the temperature control.

        Returns:
            bool: True if the command was successfully sent, False otherwise.
        """
        return await self.hw_device._send_command_and_read_reply("{M140001")

    async def power_off(self):
        """
        Turn off the temperature control.

        Returns:
            bool: True if the command was successfully sent, False otherwise.
        """
        return await self.hw_device._send_command_and_read_reply("{M140000")
