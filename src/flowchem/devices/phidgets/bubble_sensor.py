"""Use Phidgets to control lab devices. So far, only 0-5 volt interface for bubble-sensor.

PhidgetBubbleSensor_power control the power of the bubble sensor
PhidgetBubbleSensor measure the signal of the bubble sensor

"""

import time

from loguru import logger

from flowchem.components.device_info import DeviceInfo
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.phidgets.bubble_sensor_component import (
    PhidgetBubbleSensorComponent,
    PhidgetBubbleSensorPowerComponent,
)
from flowchem.utils.people import dario, jakob, wei_hsin

try:
    from Phidget22.Devices.DigitalOutput import DigitalOutput  # power source
    from Phidget22.Devices.VoltageInput import PowerSupply, VoltageInput  # Sensor
    from Phidget22.PhidgetException import PhidgetException

    HAS_PHIDGET = True
except ImportError:
    HAS_PHIDGET = False

from flowchem.utils.exceptions import (
    InvalidConfigurationError,
)  # configuration is not valid


class PhidgetPowerSource5V(FlowchemDevice):
    """Use a Phidget power source to apply power to the sensor."""

    def __init__(
        self,
        vint_serial_number: int = -1,
        vint_hub_port: int = -1,
        vint_channel: int = -1,
        phidget_is_remote: bool = False,
        name: str = "",
    ) -> None:
        """Initialize BubbleSensor with the given voltage range (sensor-specific!)."""
        super().__init__(name=name)
        if not HAS_PHIDGET:
            raise InvalidConfigurationError(
                "Phidget unusable: library or package not installed."
            )

        # power switch
        self.phidget = DigitalOutput()

        # Ensure connection with the right sensor (ideally these are from config)
        if vint_serial_number > -1:
            self.phidget.setDeviceSerialNumber(vint_serial_number)
        if vint_hub_port > -1:
            self.phidget.setHubPort(vint_hub_port)
            self.phidget.setIsHubPortDevice(True)
        if vint_channel > -1:
            self.phidget.setChannel(vint_channel)

        # Fancy remote sensors?
        if phidget_is_remote:
            from Phidget22.Net import Net
            from Phidget22.PhidgetServerType import PhidgetServerType

            Net.enableServerDiscovery(PhidgetServerType.PHIDGETSERVER_DEVICEREMOTE)
            self.phidget.setIsRemote(True)

        try:
            self.phidget.openWaitForAttachment(1000)
            logger.debug("power of tube sensor is connected!")
        except PhidgetException as pe:
            raise InvalidConfigurationError(
                "Cannot connect to sensor! Check it is not already opened elsewhere and settings..."
            ) from pe

        # Set power supply to 5V to provide power
        self.phidget.setDutyCycle(0.0)
        logger.info("power of tube sensor is turn off!")
        # self.phidget.setState(True)  #setting DutyCycle to 1.0

        self.device_info = DeviceInfo(
            authors=[dario, jakob, wei_hsin],
            manufacturer="Phidget",
            model="VINT",
            serial_number=vint_serial_number,
        )

    async def initialize(self):
        self.components.append(PhidgetBubbleSensorPowerComponent("5V", self))

    def __del__(self) -> None:
        """Ensure connection closure upon deletion."""
        self.phidget.close()

    def power_on(self):
        """Control the power of the device."""
        self.phidget.setDutyCycle(1.0)  # self.phidget.setState(True)
        logger.debug("tube sensor power is turn on!")

    def power_off(self):
        self.phidget.setState(False)
        logger.debug("tube sensor power is turn off!")

    def is_attached(self) -> bool:
        """Whether the device is connected."""
        return bool(self.phidget.getAttached())

    def is_poweron(self) -> bool:
        """Whether the power is on."""
        return bool(self.phidget.getState())


class PhidgetBubbleSensor(FlowchemDevice):
    """Use a Phidget voltage input to translate a Tube Liquid Sensor OPB350 5 Voltage signal
    to the corresponding light penetration value.
    """

    def __init__(
        self,
        vint_serial_number: int = -1,
        vint_hub_port: int = -1,
        vint_channel: int = -1,
        phidget_is_remote: bool = False,
        data_interval: int = 250,  # ms
        name: str = "",
    ) -> None:
        """Initialize BubbleSensor with the given voltage range (sensor-specific!)."""
        super().__init__(name=name)
        if not HAS_PHIDGET:
            raise InvalidConfigurationError(
                "Phidget unusable: library or package not installed."
            )

        # Sensor range
        # sensor_min, sensor_max = intensity_range
        # self._min_intensity = sensor_min
        # self._max_intensity = sensor_max

        # Voltage meter by Versatile input Phidget DAQ1400_0
        self.phidget = VoltageInput()

        # Ensure connection with the right sensor (ideally these are from config)
        if vint_serial_number > -1:
            self.phidget.setDeviceSerialNumber(vint_serial_number)
        if vint_hub_port > -1:
            self.phidget.setHubPort(vint_hub_port)
        if vint_channel > -1:
            self.phidget.setChannel(vint_channel)

        # Fancy remote sensors?
        if phidget_is_remote:
            from Phidget22.Net import Net
            from Phidget22.PhidgetServerType import PhidgetServerType

            Net.enableServerDiscovery(PhidgetServerType.PHIDGETSERVER_DEVICEREMOTE)
            self.phidget.setIsRemote(True)

        try:
            self.phidget.openWaitForAttachment(1000)
            logger.debug("tube sensor is connected!")
        except PhidgetException as pe:
            raise InvalidConfigurationError(
                "Cannot connect to sensor! Check it is not already opened elsewhere and settings..."
            ) from pe

        # Set power supply to 12V to start measurement
        self.phidget.setPowerSupply(PowerSupply.POWER_SUPPLY_OFF)
        logger.info(
            f"default tube sensor is turn off, default data interval is {data_interval} ms!"
        )
        self.phidget.setDataInterval(data_interval)

        self.device_info = DeviceInfo(
            authors=[dario, jakob, wei_hsin],
            manufacturer="Phidget",
            model="VINT",
            serial_number=vint_serial_number,
        )

    async def initialize(self):
        self.components.append(PhidgetBubbleSensorComponent("bubble-sensor", self))

    def __del__(self) -> None:
        """Ensure connection closure upon deletion."""
        self.phidget.close()

    def power_on(self):
        """Turn on the measurement of the bubble sensor."""
        self.phidget.setPowerSupply(PowerSupply.POWER_SUPPLY_12V)
        logger.debug("measurement of tube sensor is turn on!")

    def power_off(self):
        """Turn off the supply to stop measurement."""
        self.phidget.setPowerSupply(PowerSupply.POWER_SUPPLY_OFF)
        logger.debug("measurement of tube sensor is turn off!")

    def is_attached(self) -> bool:
        """Whether the device is connected."""
        return bool(self.phidget.getAttached())

    def get_dataInterval(self) -> int:
        """Get Data Interval form the initial setting."""
        return self.phidget.getDataInterval()

    def set_dataInterval(self, datainterval: int) -> None:
        """Set Data Interval: 20-6000 ms."""
        self.phidget.setDataInterval(datainterval)
        logger.debug(f"change data interval to {datainterval}!")

    def _voltage_to_intensity(self, voltage_in_volt: float) -> float:
        """Convert current reading into percentage."""
        intensity_reading = voltage_in_volt * 20
        logger.debug(f"Read intensity {intensity_reading}!")
        return intensity_reading

    def read_voltage(self) -> float:  # type: ignore
        """Read intensity from the sensor and returns it as float."""
        try:
            voltage = self.phidget.getVoltage()
            logger.debug(f"Actual voltage: {voltage}")
            return voltage
        except PhidgetException:
            logger.error("Cannot read intensity!")
            return 0

    def read_intensity(self) -> float:  # type: ignore
        """Read intensity from voltage."""
        voltage = self.read_voltage()
        return self._voltage_to_intensity(voltage)

    # def getMaxVoltage(self):
    # https: // www.phidgets.com /?view = api


if __name__ == "__main__":
    # turn on the  power of the bubble tube
    power = PhidgetPowerSource5V(
        vint_serial_number=627768,
        vint_hub_port=3,
        vint_channel=0,
    )

    # turn on the sensor
    BubbleSensor_1 = PhidgetBubbleSensor(
        vint_serial_number=627768,
        vint_hub_port=0,
        vint_channel=0,
    )

    while True:
        print(BubbleSensor_1.read_intensity())
        time.sleep(0.1)
