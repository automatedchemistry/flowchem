"""Bubble sensor."""

from flowchem.devices.flowchem_device import FlowchemDevice

from .photo_sensor import PhotoSensor


class BubbleSensor(PhotoSensor):
    """
    An optical sensor on a tube that tells liquid from gas (a bubble).

    ``acquire-signal`` and ``read`` return the raw signal in device-specific units
    (e.g. % of 5 V for the Phidget sensor, a raw ADC value for the FlowControl board).
    ``bubble-detected`` is the device-independent answer.

    Devices that tell an empty tube apart from a bubble (FlowControl board) report an empty
    tube as no bubble; threshold-based sensors (Phidget) can't, and report it as a bubble.
    """

    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        super().__init__(name, hw_device)
        self.add_api_route("/bubble-detected", self.bubble_detected, methods=["GET"])

    async def bubble_detected(self) -> bool:
        """True while the sensor sees a gas bubble instead of liquid."""
        raise NotImplementedError
