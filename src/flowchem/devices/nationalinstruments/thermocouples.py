"""
Thermocouples are the most commonly used temperature sensors.
https://www.ni.com/docs/en-US/bundle/ni-daqmx/page/thermocouples.html


Running nidaqmx requires NI-DAQmx to be installed. For more information pls check:
https://nidaqmx-python.readthedocs.io/en/latest/index.html

"""
import asyncio

from loguru import logger
from flowchem.components.device_info import DeviceInfo
from flowchem.devices.flowchem_device import FlowchemDevice

from flowchem.utils.people import wei_hsin

from flowchem import ureg
from flowchem.utils.exceptions import InvalidConfigurationError

from .thermocouples_component import NItemperatureSensor

try:
    import nidaqmx
    from nidaqmx.constants import TemperatureUnits, ThermocoupleType, CJCSource

    HAS_nidaqmx = True

except ImportError:
    HAS_nidaqmx = False


class Thermocouple(FlowchemDevice):
    """current input to translate from -80 mV-80 mV to the corresponding temperature range by type of thermocouple."""
    def __init__(
        self,
        physical_channel: str | None = None,
        thermocouple_type: str = "K",
        temperature_range:  tuple[str, str] = ("0 °C", "100 °C"),
        name: str = "",
    ) -> None:
        """Initialize PressureSensor with the given pressure range (sensor-specific!)."""
        super().__init__(name=name)

        # current meter
        self.physical_channel = physical_channel
        self.thermocouple_type = thermocouple_type
        self.system = None

        if not HAS_nidaqmx:
            raise InvalidConfigurationError(
                "HAS_NIMax unusable: library or package not installed."
            )

        self.system = nidaqmx.system.System.local()
        if self.system is None:
            raise InvalidConfigurationError("System did not have DAQmx application")
        if self.physical_channel is None:
            # only work with one device and one physical channel existed
            channels_dict = self._find_physical_channels_by_device(self.system.devices[0])
            # get_first_non_empty_channel
            self.physical_channel = next((value[0] for value in channels_dict.values() if value), None)

        # Sensor range
        sensor_min, sensor_max = temperature_range
        self._min_temperature = ureg.Quantity(sensor_min)
        self._max_temperature = ureg.Quantity(sensor_max)

        self.device_info = DeviceInfo(
            authors=[wei_hsin],
            manufacturer="National Instruments",
            model="NI USB-TC01",
        )

        self.task = nidaqmx.Task()
        self.task.ai_channels.add_ai_thrmcpl_chan(
            physical_channel=self.physical_channel,
            thermocouple_type=ThermocoupleType[self.thermocouple_type],
            units=TemperatureUnits.DEG_C,
            cjc_source=CJCSource.BUILT_IN)

    async def initialize(self):
        self.components.append((NItemperatureSensor("sensor", self)))

    async def read_temperature(self) -> float:
        return self.task.read(number_of_samples_per_channel=1)[0]

    async def read_voltage(self) -> float:
        # self.task.ai_channels.add_ai_voltage_chan(max_val=0.008, min_val=-0.008)
        pass

    def __del__(self) -> None:
        """Ensure connection closure upon deletion."""
        if hasattr(self, 'task'):
            self.task.close()

    def _find_device(self) -> nidaqmx.system.device.Device:
        if len(self.system.devices) != 1:
            logger.warning("System have zero or multiple devices")

        if self.system.devices:
            print("NI Devices found:")
            for device in self.system.devices:
                logger.debug(f"Device: {device.name}")
        else:
            print("No NI devices found. Ensure NI-DAQmx driver is installed.")

    def _find_physical_channels_by_device(self, device:nidaqmx.system.device.Device) -> dict:
        # List AI (Analog Input) channels
        channels_dict = {"ai": [], "ao": [], "di": [], "do": [], "ci": [], "co": []}

        # Analog Input Channels (AI)
        channels_dict["ai"].extend([ai_channel.name for ai_channel in device.ai_physical_chans])
        # Analog Output Channels (AO)
        channels_dict["ao"].extend([ao_channel.name for ao_channel in device.ao_physical_chans])
        # Digital Input Lines (DI)
        channels_dict["di"].extend([di_channel.name for di_channel in device.di_lines])
        # Digital Output Lines (DO)
        channels_dict["do"].extend([do_channel.name for do_channel in device.do_lines])
        # Counter Input Channels (CI)
        channels_dict["ci"].extend([ci_channel.name for ci_channel in device.ci_physical_chans])
        # Counter Output Channels (CO)
        channels_dict["co"].extend([co_channel.name for co_channel in device.co_physical_chans])

        return channels_dict


async def main(tempo):
    for i in range(10):
        print(await tempo.read_temperature())
        await asyncio.sleep(1)

if __name__ == "__main__":
    tempo = Thermocouple("Dev1/ai0")
    # asyncio.run(tempo.read_temperature())
    asyncio.run(main(tempo))