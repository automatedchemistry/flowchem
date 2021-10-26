import logging
import time
import warnings
from typing import Optional

from Phidget22.Devices.CurrentInput import CurrentInput, PowerSupply
from Phidget22.Devices.Log import Log, LogLevel
from Phidget22.PhidgetException import PhidgetException

from flowchem.constants import DeviceError

try:
    Log.enable(LogLevel.PHIDGET_LOG_INFO, "phidget.log")
except FileNotFoundError as e:
    warnings.warn("Phidget library not installed, disabling component?\n"
                  "Get it from https://www.phidgets.com/docs/Operating_System_Support")


class PressureSensor:
    """ Use a Phidget current input to translate a Swagelock 4..20mA signal to the corresponding pressure value """

    def __init__(
        self,
        sensor_min_bar: float = 0,
        sensor_max_bar: float = 10,
        vint_serial_number: int = None,
        vint_channel: int = None,
        phidget_is_remote: bool = False,
    ):

        # Logger
        self.log = logging.getLogger(__name__).getChild(self.__class__.__name__)

        # Sensor range
        self._minP = sensor_min_bar
        self._maxP = sensor_max_bar
        # current meter
        self.phidget = CurrentInput()

        # Ensure connection with the right sensor (ideally these are from graph)
        if vint_serial_number:
            self.phidget.setDeviceSerialNumber(vint_serial_number)
        if vint_channel:
            self.phidget.setChannel(vint_channel)

        # Fancy remote sensors?
        if phidget_is_remote:
            from Phidget22.Net import Net
            from Phidget22.PhidgetServerType import PhidgetServerType

            Net.enableServerDiscovery(PhidgetServerType.PHIDGETSERVER_DEVICEREMOTE)
            self.phidget.setIsRemote(True)

        try:
            self.phidget.openWaitForAttachment(1000)
            self.log.debug("Pressure sensor connected!")
        except PhidgetException as e:
            raise DeviceError(
                "Cannot connect to sensor! Check settings..."
            ) from e

        # Set power supply to 24V
        self.phidget.setPowerSupply(PowerSupply.POWER_SUPPLY_24V)
        self.phidget.setDataInterval(200)  # 200ms

    def __del__(self):
        self.phidget.close()

    def get_router(self):
        """ Creates an APIRouter for this object. """
        from fastapi import APIRouter

        router = APIRouter()
        router.add_api_route("/attached", self.is_attached, methods=["GET"])
        router.add_api_route("/pressure", self.read_pressure, methods=["GET"])

        return router

    def is_attached(self) -> bool:
        """ Whether the device is connected """
        return bool(self.phidget.getAttached())

    def _current_to_pressure(self, current_in_ampere: float) -> float:
        """ Converts current reading into pressure value """
        ma = current_in_ampere * 1000
        # minP..maxP is 4..20mA
        pressure_reading = self._minP + ((ma - 4) / 16) * (self._maxP - self._minP)
        self.log.debug(f"Read pressure {pressure_reading} barg!")
        return pressure_reading

    def read_pressure(self) -> Optional[float]:
        """
        Read pressure from sensor, in bar.

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
            self.log.debug(f"Current pressure: {current}")
        except PhidgetException:
            warnings.warn("Cannot read pressure!")
            return None
        else:
            return self._current_to_pressure(current)


if __name__ == "__main__":
    test = PressureSensor(
        sensor_min_bar=0, sensor_max_bar=25, vint_serial_number=627768, vint_channel=0
    )
    while True:
        print(test.read_pressure())
        time.sleep(1)
