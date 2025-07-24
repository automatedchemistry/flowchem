from typing import TYPE_CHECKING
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.components.sensors.photo_sensor import PhotoSensor

if TYPE_CHECKING:
    from flowchem.devices.oceanoptics.flame import FlameOptical


class GeneralSensor(PhotoSensor):
    # fixme: to aviod circular import
    # hw_device: FlameOptical

    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        """Create a DADControl object."""
        super().__init__(name, hw_device)

        # additional parameters
        self.add_api_route("/get-wavelength", self.get_wavelength, methods=["GET"])
        self.add_api_route("/set-integration-time", self.set_integration_time, methods=["PUT"])

    async def acquire_signal(self, absolute: bool = True) -> list:
        """Read from sensor, result to be expressed in % (optional)."""
        return await self.hw_device.get_intensity(absolute=absolute)

    async def get_wavelength(self) -> list:
        """Set acquisition wavelength (nm) in the range of 0-999 nm."""
        return await self.hw_device.get_wavelength()

    async def set_integration_time(self, int_time: int):
        """Set integration time in ms."""
        return await self.hw_device.integration_time(int_time)

    async def power_on(self) -> str:
        """Check the lamp status."""
        return await self.hw_device.power_on()

    async def power_off(self) -> str:
        """Deactivate the measurement channel."""
        return await self.hw_device.power_off()
