from typing import TYPE_CHECKING

import pint
from flowchem import ureg

from flowchem.components.sensors.temperature_sensor import TemperatureSensor
from flowchem.devices.flowchem_device import FlowchemDevice

if TYPE_CHECKING:
    from flowchem.devices.nationalinstruments.thermocouples import Thermocouple


class NItemperatureSensor(TemperatureSensor):
    # hw_device: Thermocouple  # just for typing

    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        super().__init__(name, hw_device)

    async def read_temperature(self, units: str = "°C") -> float:
        """Read from sensor, result to be expressed in units (optional)."""
        return await self.hw_device.read_temperature()
