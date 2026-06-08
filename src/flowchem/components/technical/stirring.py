"""Stirring control."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pint
from loguru import logger

from flowchem import ureg
from flowchem.components.flowchem_component import FlowchemComponent

if TYPE_CHECKING:
    from flowchem.devices.flowchem_device import FlowchemDevice


class StirringControl(FlowchemComponent):
    """A generic stirring controller."""

    def __init__(
        self,
        name: str,
        hw_device: FlowchemDevice,
        min_speed: int = 100,
        max_speed: int = 1400,
    ) -> None:
        """Create a StirringControl object."""
        super().__init__(name, hw_device)

        self.add_api_route("/speed", self.set_speed, methods=["PUT"])
        self.add_api_route("/speed", self.get_speed, methods=["GET"])
        self.add_api_route("/speed-setpoint", self.get_speed_setpoint, methods=["GET"])

        self.add_api_route("/power-on", self.power_on, methods=["PUT"])
        self.add_api_route("/power-off", self.power_off, methods=["PUT"])
        self.add_api_route("/is-on", self.is_on, methods=["GET"])

        self.min_speed = min_speed
        self.max_speed = max_speed

    async def set_speed(self, speed: str) -> pint.Quantity:
        """Set the stirring speed using a string in rpm."""
        try:
            float(speed)
        except ValueError:
            pass
        else:
            logger.warning("No units provided to set_speed, assuming rpm.")
            speed = speed + " rpm"

        set_speed: pint.Quantity = ureg.Quantity(speed)

        if set_speed < ureg.Quantity(f"{self.min_speed} rpm"):
            set_speed = ureg.Quantity(f"{self.min_speed} rpm")
            logger.warning(
                f"Speed requested is out of range for {self.name}! "
                f"Setting to {self.min_speed} rpm instead.",
            )

        if set_speed > ureg.Quantity(f"{self.max_speed} rpm"):
            set_speed = ureg.Quantity(f"{self.max_speed} rpm")
            logger.warning(
                f"Speed requested is out of range for {self.name}! "
                f"Setting to {self.max_speed} rpm instead.",
            )

        return set_speed

    async def get_speed(self) -> float:  # type: ignore
        """Return current stirring speed in rpm."""
        ...

    async def get_speed_setpoint(self) -> float:  # type: ignore
        """Return stirring speed setpoint in rpm."""
        ...

    async def power_on(self):
        """Start stirring."""
        ...

    async def power_off(self):
        """Stop stirring."""
        ...

    async def is_on(self) -> bool:  # type: ignore
        """Return whether stirring is active."""
        ...
