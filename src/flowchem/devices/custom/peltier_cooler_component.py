"""Control module for the Custom Peltier cooler components."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import pint
from flowchem.components.technical.temperature import TemperatureControl, TempRange

if TYPE_CHECKING:
    from .peltier_cooler import PeltierCooler


class PeltierCoolerTemperatureControl(TemperatureControl):
    """Peltier Cooler ."""

    hw_device: PeltierCooler  # for typing's sake

    def __init__(
        self, name: str, hw_device: PeltierCooler, temp_limits: TempRange
    ) -> None:
        super().__init__(name, hw_device, temp_limits)
        self.add_api_route("/parameters", self.parameters, methods=["GET"])

    async def parameters(self) -> dict[str, Any]:
        """Return configured (TOML) defaults and a live hardware readback of Peltier parameters."""
        defaults = self.hw_device.peltier_defaults
        raw = await self.hw_device.get_parameters()
        return {
            "configured": {
                "heating_pid": defaults.HEATING_PID,
                "cooling_pid": defaults.COOLING_PID,
                "base_temp": defaults.BASE_TEMP,
                "t_max": defaults.T_MAX,
                "t_min": defaults.T_MIN,
                "state_dependent_data": defaults.state_dependent_data,
            },
            "live": {
                # Only the first field of the controller's GPA reply is documented
                # by existing usage (see is_target_reached/get_temperature_setpoint).
                # The remaining fields are an undocumented vendor-specific dump, so
                # the full raw reply is included as-is rather than guessing at
                # field semantics that could misrepresent real values.
                "temperature_setpoint": float(raw.split(",")[0]),
                "raw_gpa_reply": raw,
            },
        }

    async def set_temperature(self, temperature: str):
        """Set the target temperature to the given string in "magnitude and unit" format."""
        set_t = cast(pint.Quantity, await super().set_temperature(temperature))
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

    async def is_idle(self) -> bool:
        """Check whether the set temperature target has been reached."""
        return await self.is_target_reached() is not False

    async def get_temperature_setpoint(self) -> float:
        """Return the current set temperature from the Peltier parameter list."""
        params = await self.hw_device.get_parameters()
        values = params.split(",")
        return float(values[0])

    async def power_on(self):
        """Turn on temperature control."""
        return await self.hw_device.start_control()

    async def power_off(self):
        """Turn off temperature control."""
        return await self.hw_device.stop_control()

    async def temperature_limits(self) -> TempRange:
        """Return a dict with `min` and `max` temperature in Celsius."""
        return self._limits
