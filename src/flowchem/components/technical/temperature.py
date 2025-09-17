"""Temperature control, either for heating or cooling."""
from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

import pint
from loguru import logger

from flowchem import ureg
from flowchem.components.flowchem_component import FlowchemComponent

if TYPE_CHECKING:
    from flowchem.devices.flowchem_device import FlowchemDevice


class TempRange(NamedTuple):
    min: pint.Quantity = ureg.Quantity("-100 °C")
    max: pint.Quantity = ureg.Quantity("+250 °C")


class TemperatureControl(FlowchemComponent):
    """A generic temperature controller."""

    def __init__(
        self, name: str, hw_device: FlowchemDevice, temp_limits: TempRange
    ) -> None:
        """Create a TemperatureControl object."""
        super().__init__(name, hw_device)

        self.add_api_route("/temperature", self.set_temperature, methods=["PUT"])
        self.add_api_route("/temperature", self.get_temperature, methods=["GET"])

        self.add_api_route("/power-on", self.power_on, methods=["PUT"])
        self.add_api_route("/power-off", self.power_off, methods=["PUT"])

        self.add_api_route("/target-reached", self.is_target_reached, methods=["GET"])
        # self.add_api_route("/limits", self.temperature_limits, methods=["GET"])

        self._limits = temp_limits

    async def set_temperature(self, temp: str) -> pint.Quantity:
        """Set the target temperature to the given string in "magnitude and unit" format."""
        if temp.isnumeric():
            temp = temp + "°C"
            logger.warning("No units provided to set_temperature, assuming Celsius.")
        set_t = ureg.Quantity(temp)

        if set_t < self._limits[0]:
            set_t = self._limits[0]
            logger.warning(
                f"Temperature requested {set_t} is out of range [{self._limits}] for {self.name}!"
                f"Setting to {self._limits[0]} instead.",
            )

        if set_t > self._limits[1]:
            set_t = self._limits[1]
            logger.warning(
                f"Temperature requested {set_t} is out of range [{self._limits}] for {self.name}!"
                f"Setting to {self._limits[1]} instead.",
            )
        return set_t

    async def get_temperature(self) -> float:  # type: ignore
        """Return temperature in Celsius."""
        ...

    async def is_target_reached(self) -> bool:  # type: ignore
        """Return True if the set temperature target has been reached."""
        ...

    async def temperature_limits(self) -> TempRange:
        """Return a dict with `min` and `max` temperature in Celsius."""
        return self._limits

    async def power_on(self):
        """Turn on temperature control."""
        ...

    async def power_off(self):
        """Turn off temperature control."""
        ...
