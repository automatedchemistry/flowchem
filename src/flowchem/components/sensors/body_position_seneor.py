"""body sensor."""
from flowchem.devices.flowchem_device import FlowchemDevice

from .sensor import Sensor


class BodySensor(Sensor):
    """A pressure sensor."""

    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        super().__init__(name, hw_device)
        self.add_api_route("/position", self.get_position, methods=["GET"])

        # Ontology: Pressure Sensor Device
        self.component_info.owl_subclass_of.append(
            "http://purl.obolibrary.org/obo/NCIT_C190586",
        )

    async def get_position(self):
        """Read from sensor, result to be expressed in units (optional)."""
        ...
