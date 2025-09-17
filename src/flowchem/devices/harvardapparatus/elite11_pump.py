"""Elite11 pump component."""
from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from .elite11 import Elite11
from flowchem.components.pumps.syringe_pump import SyringePump


class Elite11PumpOnly(SyringePump):
    """
    Elite11 pump component without withdraw option.

    Attributes:
        hw_device (Elite11): The hardware device controlling the pump.
    """
    hw_device: Elite11  # for typing's sake

    @staticmethod
    def is_withdrawing_capable():
        """
        Check if the pump is capable of withdrawing.

        Returns:
            bool: False, as this pump is not capable of withdrawing.
        """
        return False

    async def is_pumping(self) -> bool:
        """
        Check if the pump is currently moving.

        Returns:
            bool: True if the pump is moving, False otherwise.
        """
        return await self.hw_device.is_moving()

    async def stop(self):
        """Stop pump."""
        await self.hw_device.stop()

    async def infuse(self, rate: str = "", volume: str = "0 ml") -> bool:
        """
        Infuse at the specified rate and volume.

        Args:
            rate (str): The flow rate for infusion. If not specified, the previous rate will be used.
            volume (str): The target volume for infusion. Defaults to "0 ml".

        Returns:
            bool: True if infusion starts successfully, False otherwise.
        """
        if await self.is_pumping():
            logger.warning("Pump already moving! change to different flow rate!!!")

        if rate:  # Else previous rate will be used
            await self.hw_device.set_flow_rate(rate)

        if volume:
            await self.hw_device.set_target_volume(volume)

        return await self.hw_device.infuse()


class Elite11PumpWithdraw(Elite11PumpOnly):
    """
    Elite11 pump component with withdraw option.

    Attributes:
        hw_device (Elite11): The hardware device controlling the pump.
    """
    @staticmethod
    def is_withdrawing_capable():
        """
        Check if the pump is capable of withdrawing.

        Returns:
            bool: True, as this pump is capable of withdrawing.
        """
        return True

    async def withdraw(self, rate: str = "1 ml/min", volume: str | None = None) -> bool:
        """
        Withdraw at the specified rate and volume.

        Args:
            rate (str): The flow rate for withdrawing. Defaults to "1 ml/min".
            volume (str | None): The target volume for withdrawing. If not specified, the previous volume will be used.

        Returns:
            bool: True if withdrawal starts successfully, False otherwise.
        """
        if await self.is_pumping():
            logger.warning("Pump already moving!")

        if rate:  # Else previous rate will be used
            await self.hw_device.set_withdrawing_flow_rate(rate)

        if volume:  # FIXME check if target volume also works for withdrawing!
            await self.hw_device.set_target_volume(volume)

        return await self.hw_device.withdraw()
