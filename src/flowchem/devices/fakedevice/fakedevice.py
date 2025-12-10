from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.components.device_info import DeviceInfo
from flowchem.utils.people import samuel_saraiva
from flowchem.devices.fakedevice.fakedevice_component import FakeSpecificComponent, FakeSpecificComponent2
from loguru import logger


class FakeDeviceExample(FlowchemDevice):
    """Our plugins fake device!"""
    device_info = DeviceInfo(
        authors=[samuel_saraiva],
        manufacturer="Fake-device",
        model="FakeDevice",
        serial_number=42,
        version="v1.0",
    )

    def __init__(self, name, another_attribute: str = "some_attribute"):
        super().__init__(name)
        self.device_info = DeviceInfo(
            authors=[samuel_saraiva],
            manufacturer="FakeDeviceExample",
            model="Universal testing Actuator",
        )
        self.another_attribute = another_attribute

    async def initialize(self):
        logger.info('FakeDevice devices was successfully initialized!')
        self.components.extend([FakeSpecificComponent("FakeSpecificComponent",self)])
        self.components.extend([FakeSpecificComponent2("FakeSpecificComponent2", self)])

    async def send_command(self, command):
        logger.info(command)  # This is in


if __name__ == '__main__':
    import asyncio

    device = FakeDeviceExample(name='Fake')
    asyncio.run(device.initialize())





