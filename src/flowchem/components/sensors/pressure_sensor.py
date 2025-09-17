"""Pressure sensor."""
from flowchem.devices.flowchem_device import FlowchemDevice

from .sensor import Sensor


class PressureSensor(Sensor):
    """
    A class to represent a pressure sensor.

    Attributes:
    -----------
    hw_device : FlowchemDevice
        The hardware device this sensor is interfacing with.

    Methods:
    --------
    read_pressure(units: str = "bar"):
        Read the current pressure from the sensor and return it in the specified units.
    """

    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        """
        Constructs all the necessary attributes for the PressureSensor object.

        Parameters:
        -----------
        name : str
            The name of the pressure sensor.
        hw_device : FlowchemDevice
            The hardware device this sensor is interfacing with.
        """
        super().__init__(name, hw_device)
        self.add_api_route("/read-pressure", self.read_pressure, methods=["GET"])

        # Ontology: Pressure Sensor Device
        self.component_info.owl_subclass_of.append(
            "http://purl.obolibrary.org/obo/NCIT_C50167",
        )

    async def read_pressure(self, units: str = "bar"):
        """
        Read the current pressure from the sensor and return it in the specified units.

        Parameters:
        -----------
        units : str, optional
            The units in which to return the pressure (default is bar).

        Returns:
        --------
        float
            The current pressure in the specified units.
        """
        ...
