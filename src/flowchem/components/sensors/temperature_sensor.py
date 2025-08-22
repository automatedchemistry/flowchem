"""Temperature sensor."""
from typing import TYPE_CHECKING, NamedTuple
from flowchem.devices.flowchem_device import FlowchemDevice

import pint

from flowchem import ureg
from .sensor import Sensor

if TYPE_CHECKING:
    from flowchem.devices.flowchem_device import FlowchemDevice


class TempRange(NamedTuple):
    min: pint.Quantity = ureg.Quantity("-100 °C")
    max: pint.Quantity = ureg.Quantity("+250 °C")


class TemperatureSensor(Sensor):
    """A temperature sensor."""

    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        super().__init__(name, hw_device)
        self.add_api_route("/read-temperature", self.read_temperature, methods=["GET"])

        # Ontology: Pressure Sensor Device
        self.component_info.owl_subclass_of.append(
            "http://purl.obolibrary.org/obo/NCIT_C50304",
        )

    async def read_temperature(self, units: str = "°C"):
        """Return temperature in Celsius."""
        ...
