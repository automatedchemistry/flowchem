"""Control module for the Vapourtec R4 heater."""
from __future__ import annotations

from typing import TYPE_CHECKING

from flowchem.components.technical.temperature import TemperatureControl, TempRange

if TYPE_CHECKING:
    from .r4_heater import R4Heater


class R4HeaterChannelControl(TemperatureControl):
    """Control class for a single channel of the R4 reactor heater."""

    hw_device: R4Heater  # for typing's sake

    def __init__(
        self,
        name: str,
        hw_device: R4Heater,
        channel: int,
        temp_limits: TempRange,
    ) -> None:
        """
        Initialize the R4HeaterChannelControl with a name, hardware device, channel, and temperature limits.

        Args:
            name (str): The name of the heater channel control.
            hw_device (R4Heater): The R4 heater hardware device.
            channel (int): The channel number to control.
            temp_limits (TempRange): The temperature limits for this channel.
        """
        super().__init__(name, hw_device, temp_limits)
        self.channel = channel

    async def set_temperature(self, temp: str):
        """
        Set the target temperature for this channel using a "magnitude and unit" format string.

        Args:
            temp (str): The desired temperature as a string (e.g., '50 °C', '75.5 °C').

        Returns:
            Awaitable: Result of the set temperature operation from the hardware device.
        """
        set_t = await super().set_temperature(temp)
        return await self.hw_device.set_temperature(self.channel, set_t)

    async def get_temperature(self) -> float:  # type: ignore
        """
        Retrieve the current temperature of this channel in degrees Celsius.

        Returns:
            float: The current temperature in degrees Celsius.
        """
        return float(await self.hw_device.get_temperature(self.channel))

    async def is_target_reached(self) -> bool:  # type: ignore
        """
        Check if the set temperature target has been reached for this channel.

        Returns:
            bool: True if the target temperature has been reached, False otherwise.
        """
        status = await self.hw_device.get_status(self.channel)
        return status.state == "S"

    async def power_on(self):
        """
        Turn on the temperature control for this channel.

        Returns:
            Awaitable: Result of the power on operation from the hardware device.
        """
        return await self.hw_device.power_on(self.channel)

    async def power_off(self):
        """
        Turn off the temperature control for this channel.

        Returns:
            Awaitable: Result of the power off operation from the hardware device.
        """
        return await self.hw_device.power_off(self.channel)
