from __future__ import annotations

from typing import TYPE_CHECKING

from flowchem.components.technical.power import PowerSwitch
from flowchem.devices.flowchem_device import FlowchemDevice

if TYPE_CHECKING:
    from .bubble_sensor import PhidgetBubbleSensor, PhidgetPowerSource5V

from flowchem.components.sensors.bubble_sensor import BubbleSensor


class PhidgetBubbleSensorComponent(BubbleSensor):
    hw_device: PhidgetBubbleSensor  # just for typing

    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        super().__init__(name, hw_device)
        # self.add_api_route("/set-data-Interval", self.set_dataInterval, methods=["PUT"])
        self.add_api_route("/read-voltage", self.read_voltage, methods=["GET"])

    async def power_on(self) -> bool:
        self.hw_device.power_on()
        return True

    async def power_off(self) -> bool:
        self.hw_device.power_off()
        return True

    async def read_voltage(self) -> float:
        """Read from sensor in Volt."""
        return self.hw_device.read_voltage()

    async def acquire_signal(self) -> float:
        """Transform the voltage from sensor to be expressed in percentage(%)."""
        return self.hw_device.read_intensity()

    async def read(self) -> float:
        """Read the generic bubble-sensor signal endpoint."""
        return await self.acquire_signal()

    async def bubble_detected(self) -> bool:
        """True while the signal (% of 5 V) is below the bubble_threshold of the device config.

        An empty tube reads as a bubble too.
        """
        return self.hw_device.read_intensity() < self.hw_device.bubble_threshold

    async def set_dataInterval(self, datainterval: int) -> bool:
        """Set data interval at the range 20-60000 ms (default unit: ms)."""
        self.hw_device.set_dataInterval(datainterval)
        return True


class PhidgetBubbleSensorPowerComponent(PowerSwitch):
    hw_device: PhidgetPowerSource5V  # just for typing

    async def power_on(self) -> bool:
        self.hw_device.power_on()
        return True

    async def power_off(self) -> bool:
        self.hw_device.power_off()
        return True
