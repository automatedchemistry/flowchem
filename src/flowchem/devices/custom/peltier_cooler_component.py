"""Control module for the Custom Peltier cooler components."""
from __future__ import annotations

from typing import TYPE_CHECKING
from flowchem.components.technical.temperature import TemperatureControl, TempRange


if TYPE_CHECKING:
    from .peltier_cooler import PeltierCooler

class PeltierCoolerTemperatureControl(TemperatureControl):
    """Peltier Cooler ."""

    hw_device: PeltierCooler  # for typing's sake

    def __init__(
        self, name: str, hw_device: PeltierCooler, temp_limits: TempRange
    ) -> None:
        """Create a TemperatureControl object."""
        super().__init__(name, hw_device, temp_limits)

    async def set_temperature(self, temperature: str):
        """Set the target temperature to the given string in "magnitude and unit" format."""
        set_t = await super().set_temperature(temperature)
        return await self.hw_device.set_temperature(set_t)

    async def get_temperature(self) -> float:  # type: ignore
        """Return temperature in Celsius."""
        return await self.hw_device.get_temperature()

    async def is_target_reached(self) -> bool | None:  # type: ignore
        """Return True if the set temperature target has been reached."""
        current_temp = await self.hw_device.get_temperature()
        params = await self.hw_device.get_parameters()
        values = params.split(',')
        target_temp = float(values[0])
        if abs(current_temp - target_temp) <= 2:
            return True
        else:
            return False

    async def power_on(self):
        """Turn on temperature control."""
        return await self.hw_device.start_control()

    async def power_off(self):
        """Turn off temperature control."""
        return await self.hw_device.stop_control()

    async def temperature_limits(self) -> TempRange:
        """Return a dict with `min` and `max` temperature in Celsius."""
        return self._limits
