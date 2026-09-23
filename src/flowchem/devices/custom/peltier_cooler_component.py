"""Control module for the Custom Peltier cooler components."""

from __future__ import annotations

from typing import TYPE_CHECKING
from flowchem.components.technical.temperature import TemperatureControl, TempRange

if TYPE_CHECKING:
    from .peltier_cooler import PeltierCooler


class PeltierCoolerTemperatureControl(TemperatureControl):
    """Peltier Cooler ."""

    hw_device: PeltierCooler  # for typing's sake

    def __init__(self, name: str, hw_device: PeltierCooler, temp_limits: TempRange) -> None:
        super().__init__(name, hw_device, temp_limits)
        self.add_api_route("/parameters", self.get_controller_parameters, methods=["GET"])

    async def set_temperature(self, temperature: str):
        """Set the target temperature to the given string in "magnitude and unit" format."""
        set_t = await super().set_temperature(temperature)
        return await self.hw_device.set_temperature(set_t)

    async def get_temperature(self) -> float:  # type: ignore
        """Return temperature in Celsius."""
        return await self.hw_device.get_temperature()

    async def is_target_reached(self) -> bool | None:  # type: ignore
        """Return True if the set temperature target has been reached."""
        current_temp = await self.hw_device.get_temperature()
        params = await self.hw_device.get_parameters()
        values = params.split(",")
        target_temp = float(values[0])
        if abs(current_temp - target_temp) <= 2:
            return True
        else:
            return False

    async def get_temperature_setpoint(self) -> float:
        """Return the current set temperature from the Peltier parameter list."""
        params = await self.hw_device.get_parameters()
        values = params.split(",")
        return float(values[0])

    async def get_controller_parameters(self) -> dict:
        """Return the driver's configured defaults next to what the controller reports (GPA).

        driver_file tells which copy of peltier_cooler.py the server imported.
        GPA fields decoded here (checked against chiller_pid_test logs): 0 setpoint,
        3 heating current limit, 4 cooling current limit, 5 P, 6 I, 9 T_min, 10 T_max.
        D is not decoded - its position in the GPA reply is unverified.
        """
        from . import peltier_cooler

        defaults = self.hw_device.peltier_defaults
        raw = await self.hw_device.get_parameters()
        values = raw.split(",")
        return {
            "driver_file": peltier_cooler.__file__,
            "defaults": {
                "class": type(defaults).__name__,
                "cooling_pid": list(defaults.COOLING_PID),
                "heating_pid": list(defaults.HEATING_PID),
                "base_temp_C": defaults.BASE_TEMP,
                # rows: temperature, cooling limit (A), heating limit (A)
                "current_limits": defaults.STATE_DEPENDANT_CURRENT_LIMITS.T.tolist(),
            },
            "controller": {
                "setpoint_C": float(values[0]),
                "heating_limit_A": float(values[3]),
                "cooling_limit_A": float(values[4]),
                "P": float(values[5]),
                "I": float(values[6]),
                "T_min_C": float(values[9]),
                "T_max_C": float(values[10]),
                "raw": raw,
            },
        }

    async def power_on(self):
        """Turn on temperature control."""
        return await self.hw_device.start_control()

    async def power_off(self):
        """Turn off temperature control."""
        return await self.hw_device.stop_control()

    async def temperature_limits(self) -> TempRange:
        """Return a dict with `min` and `max` temperature in Celsius."""
        return self._limits
