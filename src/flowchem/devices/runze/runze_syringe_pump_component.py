"""Runze Smart SY-01 syringe pump component."""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from flowchem import ureg
from flowchem.components.pumps.syringe_pump import SyringePump

if TYPE_CHECKING:
    from .runze_syringe_pump import RunzeSyringePump

_RATE_NOT_CALIBRATED_WARNING = (
    "RunzeSyringePump does not yet have a calibrated rate->speed mapping "
    "for the vendor's dynamic-speed command (0x4b); rate is ignored and the "
    "pump runs at its default speed."
)


class RunzeSyringePumpComponent(SyringePump):
    """Aspirate/infuse control for a Runze Smart SY-01 syringe pump."""

    hw_device: RunzeSyringePump

    def __init__(self, name: str, hw_device: RunzeSyringePump) -> None:
        super().__init__(name, hw_device)
        self.add_api_route(
            "/get-current-volume", self.get_current_volume, methods=["GET"]
        )
        self.add_api_route("/infuse-all", self.infuse_all, methods=["PUT"])
        self.add_api_route("/withdraw-all", self.withdraw_all, methods=["PUT"])

    @staticmethod
    def is_withdrawing_capable() -> bool:
        return True

    async def get_current_volume(self) -> float:
        """Return the current syringe volume in ml."""
        volume = await self.hw_device.get_current_volume()
        return volume.m_as("ml")

    async def is_pumping(self) -> bool:
        """Is the plunger or the built-in valve currently moving?"""
        return await self.hw_device.is_moving()

    async def is_idle(self) -> bool:
        """Check whether the plunger has finished its current move."""
        return await self.hw_device.get_status() == "00"

    async def stop(self) -> bool:
        """Strong stop: halts both the plunger and the built-in valve."""
        return await self.hw_device.stop()

    async def infuse(self, rate: str = "", volume: str = "") -> bool:
        """Dispense `volume` (a relative move). If omitted, dispenses everything.

        Not gated on our own read of the current volume: the underlying 0x42
        command is hardware-bounded (the reset optocoupler stops the plunger
        early rather than overshooting), so an over-large request just dispenses
        as much as is physically there instead of being rejected up front.
        """
        if rate:
            logger.warning(_RATE_NOT_CALIBRATED_WARNING)

        if not volume:
            return await self.infuse_all()

        steps = self.hw_device.volume_to_steps(ureg.Quantity(volume))
        return await self.hw_device.dispense_steps(steps)

    async def withdraw(self, rate: str = "", volume: str = "") -> bool:
        """Aspirate `volume` (a relative move). If omitted, fills to capacity.

        Not gated on our own read of the current volume, for the same reason
        as `infuse`: 0x43 is hardware-bounded by the far limit switch.
        """
        if rate:
            logger.warning(_RATE_NOT_CALIBRATED_WARNING)

        if not volume:
            return await self.withdraw_all()

        steps = self.hw_device.volume_to_steps(ureg.Quantity(volume))
        return await self.hw_device.aspirate_steps(steps)

    async def infuse_all(self) -> bool:
        """Fully dispense: request the full stroke; the reset limit switch bounds it safely.

        Uses `dispense_steps(total_steps)` rather than the pump's `home()`
        (0x45): simpler (no extra 0x67 sync step needed afterward) and
        already confirmed working on real hardware.
        """
        return await self.hw_device.dispense_steps(self.hw_device.total_steps)

    async def withdraw_all(self) -> bool:
        """Fully aspirate: request the full stroke; the far limit switch bounds it safely."""
        return await self.hw_device.aspirate_steps(self.hw_device.total_steps)
