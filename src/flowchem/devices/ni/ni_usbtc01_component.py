"""Flowchem component for the NI USB-TC01 thermocouple temperature sensor."""

from __future__ import annotations

from typing import TYPE_CHECKING

from flowchem.components.sensors.temperature_sensor import TemperatureSensor

if TYPE_CHECKING:
    from .ni_usbtc01 import NIUSBTC01


class TC01TemperatureSensor(TemperatureSensor):
    """Read-only temperature sensor component for the NI USB-TC01."""

    hw_device: NIUSBTC01

    async def get_temperature(self) -> float:
        """Return the current thermocouple temperature in degrees Celsius."""
        return await self.hw_device.read_temperature()
