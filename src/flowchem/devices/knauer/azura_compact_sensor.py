"""Azura compact sensor component."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .azura_compact import AzuraCompact

from flowchem.components.sensors.pressure_sensor import PressureSensor


class AzuraCompactSensor(PressureSensor):
    hw_device: AzuraCompact  # for typing's sake

    async def read_pressure(self, units: str = "bar"):
        """Read from sensor, result to be expressed in units (optional)."""
        pressure = await self.hw_device.read_pressure()
        return pressure.m_as(units)
