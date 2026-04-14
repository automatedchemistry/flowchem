"""Simulated Phidget pressure sensor."""

from __future__ import annotations

from loguru import logger

from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.components.device_info import DeviceInfo
from flowchem import ureg
import pint


class PhidgetPressureSensorSim(FlowchemDevice):
    """
    Simulated Phidget pressure sensor.

    The Phidget device uses a proprietary C-extension SDK that cannot be
    imported without hardware.  This sim bypasses the SDK entirely by
    subclassing FlowchemDevice directly (not PhidgetPressureSensor, which
    tries to import and open the Phidget hardware in __init__).

    State
    -----
    _sim_pressure : pint.Quantity   current pressure
    _min_pressure : pint.Quantity   sensor min
    _max_pressure : pint.Quantity   sensor max
    """

    def __init__(
        self,
        pressure_range: tuple[str, str] = ("0 bar", "10 bar"),
        vint_serial_number: int = -1,
        vint_channel: int = -1,
        phidget_is_remote: bool = False,
        name: str = "",
    ):
        super().__init__(name=name)
        sensor_min, sensor_max = pressure_range
        self._min_pressure: pint.Quantity = ureg.Quantity(sensor_min)
        self._max_pressure: pint.Quantity = ureg.Quantity(sensor_max)
        self._sim_pressure: pint.Quantity = ureg.Quantity("1.0 bar")

        self.device_info = DeviceInfo(
            manufacturer="Phidget",
            model="SimulatedVINT",
            serial_number=str(vint_serial_number),
        )
        logger.info(f"[SIM] PhidgetPressureSensor '{name}' initialized.")

    @classmethod
    def from_config(cls, **config) -> "PhidgetPressureSensorSim":
        pressure_range = (
            config.pop("min_pressure", "0 bar"),
            config.pop("max_pressure", "10 bar"),
        )
        return cls(
            pressure_range=pressure_range,
            name=config.pop("name", "sim-phidget-pressure"),
            **{
                k: v
                for k, v in config.items()
                if k in ("vint_serial_number", "vint_channel", "phidget_is_remote")
            },
        )

    async def initialize(self):
        from flowchem.devices.phidgets.pressure_sensor_component import (
            PhidgetPressureSensorComponent,
        )

        self.components.append(PhidgetPressureSensorComponent("pressure-sensor", self))

    def is_attached(self) -> bool:
        return True

    def read_pressure(self) -> pint.Quantity:
        """Return the simulated pressure. Tests can set _sim_pressure directly."""
        return self._sim_pressure
