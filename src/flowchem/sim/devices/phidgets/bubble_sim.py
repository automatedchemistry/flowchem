"""Simulated Phidget bubble sensor and 5 V power source."""

from __future__ import annotations

from loguru import logger

from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.components.device_info import DeviceInfo


class PhidgetPowerSource5VSim(FlowchemDevice):
    """
    Simulated Phidget 5 V digital-output power source.

    The real device uses the Phidget22 SDK ``DigitalOutput`` which cannot
    be imported without hardware.  This sim subclasses FlowchemDevice
    directly and provides the same public API.

    State
    -----
    _sim_power : bool   current power state
    """

    def __init__(
        self,
        vint_serial_number: int = -1,
        vint_hub_port: int = -1,
        vint_channel: int = -1,
        phidget_is_remote: bool = False,
        name: str = "",
    ):
        super().__init__(name=name)
        self._sim_power: bool = False
        self.device_info = DeviceInfo(
            manufacturer="Phidget",
            model="Simulated5VPowerSource",
            serial_number=str(vint_serial_number),
        )
        logger.info(f"[SIM] PhidgetPowerSource5V '{name}' initialized.")

    @classmethod
    def from_config(cls, **config) -> "PhidgetPowerSource5VSim":
        return cls(
            name=config.pop("name", "sim-phidget-5v"),
            vint_serial_number=int(config.pop("vint_serial_number", -1)),
            vint_hub_port=int(config.pop("vint_hub_port", -1)),
            vint_channel=int(config.pop("vint_channel", -1)),
        )

    async def initialize(self):
        from flowchem.devices.phidgets.bubble_sensor_component import (
            PhidgetBubbleSensorPowerComponent,
        )

        self.components.append(PhidgetBubbleSensorPowerComponent("5V", self))

    # Same synchronous API as the real device
    def power_on(self):
        self._sim_power = True
        logger.debug("[SIM] PhidgetPowerSource5V ON")

    def power_off(self):
        self._sim_power = False
        logger.debug("[SIM] PhidgetPowerSource5V OFF")

    def is_attached(self) -> bool:
        return True

    def is_poweron(self) -> bool:
        return self._sim_power


class PhidgetBubbleSensorSim(FlowchemDevice):
    """
    Simulated Phidget bubble sensor (OPB350 0–5 V interface).

    The real device uses the Phidget22 SDK ``VoltageInput`` which cannot
    be imported without hardware.  This sim subclasses FlowchemDevice
    directly.

    State
    -----
    _sim_voltage      : float   current voltage reading (V)
    _sim_power        : bool    measurement active (power supply on)
    _sim_data_interval: int     data interval ms
    """

    def __init__(
        self,
        vint_serial_number: int = -1,
        vint_hub_port: int = -1,
        vint_channel: int = -1,
        phidget_is_remote: bool = False,
        data_interval: int = 250,
        name: str = "",
    ):
        super().__init__(name=name)
        self._sim_voltage: float = 0.0
        self._sim_power: bool = False
        self._sim_data_interval: int = data_interval
        self.device_info = DeviceInfo(
            manufacturer="Phidget",
            model="SimulatedBubbleSensor",
            serial_number=str(vint_serial_number),
        )
        logger.info(f"[SIM] PhidgetBubbleSensor '{name}' initialized.")

    @classmethod
    def from_config(cls, **config) -> "PhidgetBubbleSensorSim":
        return cls(
            name=config.pop("name", "sim-phidget-bubble"),
            vint_serial_number=int(config.pop("vint_serial_number", -1)),
            vint_hub_port=int(config.pop("vint_hub_port", -1)),
            vint_channel=int(config.pop("vint_channel", -1)),
            data_interval=int(config.pop("data_interval", 250)),
        )

    async def initialize(self):
        from flowchem.devices.phidgets.bubble_sensor_component import (
            PhidgetBubbleSensorComponent,
        )

        self.components.append(PhidgetBubbleSensorComponent("bubble-sensor", self))

    # Same synchronous API as the real device
    def power_on(self):
        self._sim_power = True
        logger.debug("[SIM] PhidgetBubbleSensor measurement ON")

    def power_off(self):
        self._sim_power = False
        logger.debug("[SIM] PhidgetBubbleSensor measurement OFF")

    def is_attached(self) -> bool:
        return True

    def get_dataInterval(self) -> int:
        return self._sim_data_interval

    def set_dataInterval(self, datainterval: int) -> None:
        self._sim_data_interval = datainterval

    def _voltage_to_intensity(self, voltage_in_volt: float) -> float:
        return voltage_in_volt * 20

    def read_voltage(self) -> float:
        return self._sim_voltage

    def read_intensity(self) -> float:
        return self._voltage_to_intensity(self._sim_voltage)
