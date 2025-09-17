from __future__ import annotations

from typing import TYPE_CHECKING

from flowchem.devices.flowchem_device import FlowchemDevice

if TYPE_CHECKING:
    from .pressure_sensor import PhidgetPressureSensor
from flowchem.components.sensors.pressure_sensor import PressureSensor


class PhidgetPressureSensorComponent(PressureSensor):
    hw_device: PhidgetPressureSensor  # just for typing

    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        """
        Initialize the PhidgetPressureSensorComponent with a name and hardware device.

        Args:
            name (str): The name of the sensor component.
            hw_device (FlowchemDevice): The hardware device associated with this sensor.
        """
        super().__init__(name, hw_device)

    async def read_pressure(self, units: str = "bar"):
        """
        Read the pressure from the sensor and return it in the specified units.

        Args:
            units (str): The units to express the pressure in. Default is "bar".

        Returns:
            float: The pressure reading expressed in the specified units.
        """
        return self.hw_device.read_pressure().m_as(units)
