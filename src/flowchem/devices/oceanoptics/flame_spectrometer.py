from typing import TYPE_CHECKING

from flowchem.components.sensors.photo_sensor import PhotoSensor
from flowchem.devices.flowchem_device import FlowchemDevice

if TYPE_CHECKING:
    from flowchem.devices.oceanoptics.flame import FlameOptical


class GeneralSensor(PhotoSensor):
    hw_device: "FlameOptical"  # just for typing

    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        super().__init__(name, hw_device)
        self.add_api_route("/get-wavelength", self.get_wavelength, methods=["GET"])
        self.add_api_route(
            "/set-integration-time", self.set_integration_time, methods=["PUT"]
        )
        self.add_api_route(
            "/get-scans-to-average", self.get_scans_to_average, methods=["GET"]
        )
        self.add_api_route(
            "/set-scans-to-average", self.set_scans_to_average, methods=["PUT"]
        )
        self.add_api_route("/get-trigger-mode", self.get_trigger_mode, methods=["GET"])
        self.add_api_route("/set-trigger-mode", self.set_trigger_mode, methods=["PUT"])

    async def acquire_signal(self, absolute: bool = True) -> list:
        return await self.hw_device.get_intensity(
            absolute=absolute,
            scans_to_average=getattr(self.hw_device, "scans_to_average", 1),
        )

    async def get_wavelength(self) -> list:
        return await self.hw_device.get_wavelength()

    async def set_integration_time(self, int_time: int):
        return await self.hw_device.integration_time(int_time)

    async def get_scans_to_average(self):
        return await self.hw_device.get_scans_to_average()

    async def set_scans_to_average(self, scans: int):
        return await self.hw_device.set_scans_to_average(scans)

    async def get_trigger_mode(self):
        return await self.hw_device.get_trigger_mode()

    async def set_trigger_mode(self, mode: int):
        return await self.hw_device.set_trigger_mode(mode)

    async def power_on(self):
        return await self.hw_device.power_on()

    async def power_off(self):
        return await self.hw_device.power_off()
