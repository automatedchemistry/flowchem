"""Sensor device."""
from __future__ import annotations

from flowchem.components.sensor_core import SensorBase
from flowchem.devices.flowchem_device import FlowchemDevice


class Sensor(SensorBase):
    """
    A generic sensor device class.

    Attributes:
    -----------
    hw_device : FlowchemDevice
        The hardware device this sensor is interfacing with.

    Methods:
    --------
    power_on():
        Power on the sensor.
    power_off():
        Power off the sensor.
    """

    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        """
        Constructs all the necessary attributes for the Sensor object.

        Parameters:
        -----------
        name : str
            The name of the sensor.
        hw_device : FlowchemDevice
            The hardware device this sensor is interfacing with.
        """
        super().__init__(name, hw_device)
        self.add_api_route("/power-on", self.power_on, methods=["PUT"])
        self.add_api_route("/power-off", self.power_off, methods=["PUT"])
        # Ontology: HPLC isocratic pump
        self.component_info.owl_subclass_of.append(
            "http://purl.obolibrary.org/obo/NCIT_C50166",
        )

    async def power_on(self):
        """
        Power on the sensor.

        Returns:
        --------
        None
        """
        ...

    async def power_off(self):
        """
        Power off the sensor.

        Returns:
        --------
        None
        """
        ...
