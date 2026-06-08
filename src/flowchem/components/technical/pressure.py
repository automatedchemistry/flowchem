"""Pressure control."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pint
from loguru import logger

from flowchem import ureg
from flowchem.components.flowchem_component import FlowchemComponent

if TYPE_CHECKING:
    from flowchem.devices.flowchem_device import FlowchemDevice


class PressureControl(FlowchemComponent):
    """A generic pressure controller for managing and monitoring pressure."""

    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        super().__init__(name, hw_device)

        self.add_api_route("/pressure", self.set_pressure, methods=["PUT"])
        self.add_api_route("/pressure", self.get_pressure, methods=["GET"])

        self.add_api_route("/power-on", self.power_on, methods=["PUT"])
        self.add_api_route("/power-off", self.power_off, methods=["PUT"])

        self.add_api_route("/target-reached", self.is_target_reached, methods=["GET"])

    async def set_pressure(self, pressure: str) -> pint.Quantity:
        """Set the target pressure using a string representation.

        If no units are specified, 'mbar' is assumed as the default unit.
        """
        try:
            float(pressure)
        except ValueError:
            pass
        else:
            logger.warning("No units provided to set_pressure, assuming mbar.")
            pressure = pressure + "mbar"
        return ureg.Quantity(pressure)

    async def get_pressure(self) -> float:
        """Retrieve the current pressure from the device."""
        raise NotImplementedError

    async def is_target_reached(self) -> bool:
        """Check if the target pressure has been reached."""
        raise NotImplementedError

    async def power_on(self):
        """Turn on the pressure control."""
        raise NotImplementedError

    async def power_off(self):
        """Turn off the pressure control."""
        raise NotImplementedError
