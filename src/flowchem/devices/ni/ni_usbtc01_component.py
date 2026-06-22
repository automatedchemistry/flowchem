"""Flowchem component for the NI USB-TC01 thermocouple temperature sensor."""

from __future__ import annotations

from typing import TYPE_CHECKING

from flowchem.components.flowchem_component import FlowchemComponent

if TYPE_CHECKING:
    from .ni_usbtc01 import NIUSBTC01


class TC01TemperatureSensor(FlowchemComponent):
    """Read-only temperature sensor component for the NI USB-TC01."""

    hw_device: NIUSBTC01

    def __init__(self, name: str, hw_device: NIUSBTC01) -> None:
        super().__init__(name, hw_device)
        self.add_api_route("/temperature", self.get_temperature, methods=["GET"])

    async def get_temperature(self) -> float:
        """Return the current thermocouple temperature in degrees Celsius."""
        return await self.hw_device.read_temperature()
