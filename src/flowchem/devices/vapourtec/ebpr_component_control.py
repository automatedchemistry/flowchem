"""Control module for the Vapourtec eBPR."""

from __future__ import annotations

from typing import TYPE_CHECKING

from flowchem import ureg
from flowchem.components.technical.pressure import PressureControl

if TYPE_CHECKING:
    from .ebpr import EBPR


class EBPRPressureControl(PressureControl):
    """Control class for the Vapourtec eBPR back pressure regulator."""

    hw_device: EBPR

    async def set_pressure(self, pressure: str) -> bool:
        """Set the target pressure (default unit mbar if none given)."""
        set_p = await super().set_pressure(pressure)
        await self.hw_device.set_pressure(set_p.m_as("mbar"))
        return True

    async def get_pressure(self) -> float:
        """Get the current pressure in bar."""
        return await self.hw_device.get_pressure()

    async def is_target_reached(self) -> bool:
        """Check if the current pressure is within the eBPR's documented resolution of the set point."""
        status = await self.hw_device.get_status()
        current = ureg.Quantity(f"{status.pressure} bar")
        target = ureg.Quantity(f"{status.setpoint} mbar")
        # +/- 0.1 bar is the documented pressure resolution (eBPR manual, low-pressure spec).
        return abs(current - target) < ureg.Quantity("100 mbar")

    async def power_on(self):
        """Turn on pressure control."""
        await self.hw_device.power_on()

    async def power_off(self):
        """Turn off pressure control."""
        await self.hw_device.power_off()
