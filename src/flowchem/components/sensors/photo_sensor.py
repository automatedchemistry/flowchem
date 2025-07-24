"""Pressure sensor."""
from flowchem.devices.flowchem_device import FlowchemDevice

from .sensor import Sensor


class PhotoSensor(Sensor):
    """A photo sensor."""

    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        super().__init__(name, hw_device)
        self.add_api_route("/acquire-signal", self.acquire_signal, methods=["GET"])
        self.add_api_route("/calibration", self.calibrate_zero, methods=["PUT"])

    async def calibrate_zero(self):
        """re-calibrate the sensors to their factory zero points."""
        ...

    async def acquire_signal(self):
        """Read from sensor, result to be expressed in % (optional)."""
        ...
