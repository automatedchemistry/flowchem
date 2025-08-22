"""
the flame is using usb and  libusb

    1. pip install pyusb
    2. pip install libusb
    3. libusb-1.0.dll will be automatically added to:

    \venv\Lib\site-packages\libusb\_platform\_windows\x64

    \venv\Lib\site-packages\libusb\_platform\_windows\x32

    Now just add those paths (the full path) to Windows Path and restart CMD / PyCharm.
    ref. https://stackoverflow.com/questions/13773132/pyusb-on-windows-no-backend-available#comment135836462_77052975

for more information of seabreeze-python
https://github.com/ap--/python-seabreeze/tree/main?tab=readme-ov-file
"""

import seabreeze
# use the pyseabreeze backend (pyusb)
seabreeze.use("pyseabreeze")

from loguru import logger
import asyncio

from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.oceanoptics.flame_spectrometer import GeneralSensor
from flowchem.utils.people import wei_hsin

class FlameOptical(FlowchemDevice):

    def __init__(
        self,
        serial_number: str | None = None,
        name="",
    ) -> None:
        self.serial_n = serial_number
        super().__init__(name)

        # Metadata
        self.device_info.authors = [wei_hsin]
        self.device_info.manufacturer = "oceanoptics"
        self.device_info.model = "python-seabreeze"

        # use the
        from seabreeze.spectrometers import Spectrometer
        if self.serial_n is None:
            self.spectrometer = Spectrometer.from_first_available()
        else:
            self.spectrometer = Spectrometer.from_serial_number(self.serial_n)

        self.model: str = self.spectrometer.model  # USB4000  #todo: list all model??
        self.max_intensity: float = self.spectrometer.max_intensity  # 65535.0 in (a.u.)
        self.pixels: int = self.spectrometer.pixels  # 3840

        # min and max integration time in micro seconds
        self.integration_time_micros_limits: tuple = self.spectrometer.integration_time_micros_limits

        self.wavelengths = self.spectrometer.wavelengths()  # numpy.ndarray (3840,) in (nm)

    async def initialize(self):
        # await self.power_on()
        self.components.append(GeneralSensor("spectrometer", self))

    async def power_on(self):
        # open the connection to SeaBreezeDevice
        self.spectrometer.open()

    async def power_off(self):
        # close the connection to SeaBreezeDevice
        self.spectrometer.close()

    async def get_spectrum(self):
        # keep the function for reference
        return self.spectrometer.spectrum()

    async def get_intensity(self, absolute: bool = False):
        if absolute:
            return self.spectrometer.intensities().tolist()
        else:
            i_list = self.spectrometer.intensities().tolist()
            return [i / self.max_intensity for i in i_list]

    async def get_wavelength(self):
        return self.wavelengths.tolist()

    async def integration_time(self, int_time: int):
        """
        integration time in microseconds
        """
        # change into to micros
        # get the limitation of lowest and hightest integration time
        l, h = self.integration_time_micros_limits
        # check in the range
        if l <= int_time <= h:
            self.spectrometer.integration_time_micros(int_time)
        elif int_time < l:
            logger.warning("the input integration time lower than the limit. set the lowest integration time int")
            self.spectrometer.integration_time_micros(l)
        else:
            logger.warning("the input integration time higher than the limit. set the highest integration time int")
            self.spectrometer.integration_time_micros(h)


async def main():
    flame =FlameOptical(serial_number="FLMT00079")

    i = await flame.get_intensity()
    print(i)

if __name__ == "__main__":
    # all_usb_devices_by_usb()
    asyncio.run(main())