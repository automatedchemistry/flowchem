"""Use Phidgets to control lab devices. So far, only 4..20mA interface for Swagelock Pressure-sensor."""

import time

import pint
from loguru import logger

from flowchem.components.device_info import DeviceInfo
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.phidgets.pressure_sensor_component import (
    PhidgetPressureSensorComponent,
)
from flowchem.utils.people import dario, jakob, wei_hsin

try:
    from Phidget22.Devices.CurrentInput import CurrentInput, PowerSupply
    from Phidget22.PhidgetException import PhidgetException

    HAS_PHIDGET = True
except ImportError:
    HAS_PHIDGET = False


from flowchem import ureg
from flowchem.utils.exceptions import InvalidConfigurationError


class PhidgetPressureSensor(FlowchemDevice):
    """Use a Phidget current input to translate a Swagelock 4..20mA signal to the corresponding pressure value."""

    def __init__(
        self,
        pressure_range: tuple[str, str] = ("0 bar", "10 bar"),
        vint_serial_number: int = -1,
        vint_channel: int = -1,
        phidget_is_remote: bool = False,
        name: str = "",
    ) -> None:
        """Initialize PressureSensor with the given pressure range (sensor-specific!)."""
        super().__init__(name=name)
        if not HAS_PHIDGET:
            raise InvalidConfigurationError(
                "Phidget unusable: library or package not installed."
            )

        # Sensor range
        sensor_min, sensor_max = pressure_range
        self._min_pressure: pint.Quantity = ureg.Quantity(sensor_min)
        self._max_pressure: pint.Quantity = ureg.Quantity(sensor_max)
        # current meter
        self.phidget = CurrentInput()

        # Ensure connection with the right sensor (ideally these are from config)
        if vint_serial_number > -1:
            self.phidget.setDeviceSerialNumber(vint_serial_number)
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
            logger.debug("Pressure sensor connected!")
        except PhidgetException as pe:
            raise InvalidConfigurationError(
                "Cannot connect to sensor! Check it is not already opened elsewhere and settings..."
            ) from pe

        # Set power supply to 24V
        self.phidget.setPowerSupply(PowerSupply.POWER_SUPPLY_24V)
        self.phidget.setDataInterval(200)  # 200ms

        self.device_info = DeviceInfo(
            authors=[dario, jakob, wei_hsin],
            manufacturer="Phidget",
            model="VINT",
            serial_number=vint_serial_number,
        )

    async def initialize(self):

        self.components.extend(
            [PhidgetPressureSensorComponent("pressure-sensor", self)]
        )

    def __del__(self) -> None:
        """Ensure connection closure upon deletion."""
        self.phidget.close()

    def is_attached(self) -> bool:
        """Whether the device is connected."""
        return bool(self.phidget.getAttached())

    def _current_to_pressure(self, current_in_ampere: float) -> pint.Quantity:
        """Convert current reading into pressure value."""
        mill_amp = current_in_ampere * 1000
        # minP..maxP is 4..20mA
        pressure_reading = self._min_pressure + ((mill_amp - 4) / 16) * (
            self._max_pressure - self._min_pressure
        )
        logger.debug(f"Read pressure {pressure_reading}!")
        return pressure_reading

    def read_pressure(self) -> pint.Quantity:  # type: ignore
        """Read pressure from the sensor and returns it as pint.Quantity.

        This is the main class method, and it never fails, but rather return None. Why?

        Well, initialization exception are fair play, upon startup any misconfiguration
        should be addressed.
        However, during experiment execution temporarily unavailability of a datasource
        should not be critical when the sensor is readonly.
        If the P-sensor is safety-critical than an event handler should be attached to it.
        If not we can live with it, returning None and letting the caller decide what
        to do with that.
        """
        try:
            current = self.phidget.getCurrent()
            logger.debug(f"Actual current: {current}")
        except PhidgetException:
            logger.error("Cannot read pressure!")
            return 0 * ureg.bar
        else:
            return self._current_to_pressure(current)


if __name__ == "__main__":
    test = PhidgetPressureSensor(
        pressure_range=("0 bar", "25 bar"),
        vint_serial_number=627768,
        vint_channel=0,
    )
    while True:
        print(test.read_pressure())
        time.sleep(1)
