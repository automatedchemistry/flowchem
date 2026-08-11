"""Temperature sensor."""

from flowchem.devices.flowchem_device import FlowchemDevice

from .sensor import Sensor


class TemperatureSensor(Sensor):
    """A class to represent a read-only temperature sensor."""

    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        super().__init__(name, hw_device)
        self.add_api_route("/temperature", self.get_temperature, methods=["GET"])

    async def get_temperature(self) -> float:
        """Return the current temperature in degrees Celsius."""
        raise NotImplementedError

    async def read(self) -> float:
        """Read the current temperature through the generic sensor route."""
        return await self.get_temperature()
