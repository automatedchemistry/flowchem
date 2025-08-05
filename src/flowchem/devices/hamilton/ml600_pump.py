"""ML600 component relative to pumping."""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from loguru import logger

from flowchem import ureg
from flowchem.components.pumps.syringe_pump import SyringePump

if TYPE_CHECKING:
    from .ml600 import ML600


class ML600Pump(SyringePump):
    pump_code: str
    hw_device: ML600  # for typing's sake

    def __init__(self, name: str, hw_device: ML600, pump_code: str = "") -> None:
        """
        Initialize an ML600Pump object.

        Parameters:
        -----------
        name : str
            The name of the pump.
        hw_device : ML600
            The hardware device instance associated with this component.
        pump_code : str, optional
            Identifier for the pump (default is "", which denotes a single syringe pump).
            "" for single syringe pump. B or C  for dual syringe pump.
        """
        super().__init__(name, hw_device)
        self.pump_code = pump_code
        # self.add_api_route("/pump", self.get_monitor_position, methods=["GET"])

    @staticmethod
    def is_withdrawing_capable() -> bool:
        """
        Indicate that the ML600 pump can perform withdrawal operations.

        Returns:
        --------
        bool
            True, since ML600 supports withdrawal.
        """
        return True

    async def is_pumping(self) -> bool:
        """Check if pump is moving.
        false means pump is not moving and buffer is empty. """
        # true might mean pump is moving, buffer still contain command or both
        return await self.hw_device.get_pump_status(self.pump_code)

    async def stop(self) -> bool:
        """
        Stop the pump's operation.

        Returns:
        --------
        bool
            True if the pump successfully stops, False otherwise.
        """
        await self.hw_device.stop(self.pump_code)
        # todo: sometime it take more then two seconds.
        await asyncio.sleep(1)
        if not await self.hw_device.get_pump_status(self.pump_code):
            return True
        else:
            logger.warning("the first check show false. try again.")
            await asyncio.sleep(1)
            return not await self.hw_device.get_pump_status(self.pump_code)

    async def infuse(self, rate: str = "", volume: str = "") -> bool:
        """
        Start an infusion with the given rate and volume.

        If no rate is specified, the default (1 ml/min) is used, can be set on per-pump basis via `default_infuse_rate`

        If no volume is specified, the max possible volume is infused.

        Parameters:
        -----------
        rate : str, optional
            The infusion rate (default is the device's configured default).
        volume : str, optional
            The volume to infuse (default is the maximum possible volume).

        Returns:
        --------
        bool
            True if the pump starts infusing successfully, False otherwise.

        Raises:
        -------
        DeviceError
            If the target volume to infuse exceeds the current syringe volume.
        """
        if await self.is_pumping():
            await self.stop()
        if not rate:
            rate = self.hw_device.config.get("default_infuse_rate")  # type: ignore
            logger.warning(f"the flow rate is not provided. set to the default {rate}")
        if not volume:
            target_vol = ureg.Quantity("0 ml")
            logger.warning("the volume to infuse is not provided. set to 0 ml")
        else:
            current_volume = await self.hw_device.get_current_volume(self.pump_code)
            target_vol = current_volume - ureg.Quantity(volume)
            if target_vol < 0:
                logger.error(
                    f"Cannot infuse target volume {volume}! "
                    f"Only {current_volume} in the syringe!",
                )
                return False

        await self.hw_device.set_to_volume(target_vol, ureg.Quantity(rate), self.pump_code)
        logger.info(f"infusing is run. it will take {ureg.Quantity(volume) / ureg.Quantity(rate)} to finish.")
        return await self.hw_device.get_pump_status(self.pump_code)

    async def withdraw(self, rate: str = "1 ml/min", volume: str | None = None) -> bool:
        """
        Start a withdrawal with the given rate and volume.

        The default can be set on per-pump basis via `default_withdraw_rate`.

        Parameters:
        -----------
        rate : str, optional
            The withdrawal rate (default is "1 ml/min").
        volume : str, optional
            The volume to withdraw (default is the maximum possible volume).

        Returns:
        --------
        bool
            True if the pump starts withdrawing successfully, False otherwise.

        Raises:
        -------
        DeviceError
            If the target volume to withdraw exceeds the syringe capacity.
        """
        if await self.is_pumping():
            await self.stop()
        if not rate:
            rate = self.hw_device.config["default_withdraw_rate"]
            logger.warning(f"the flow rate is not provided. set to the default {rate}")
        if volume is None:
            target_vol = self.hw_device.syringe_volume
            logger.warning(f"the volume to withdraw is not provided. set to {self.hw_device.syringe_volume}")
        else:
            current_volume = await self.hw_device.get_current_volume(self.pump_code)
            target_vol = current_volume + ureg.Quantity(volume)
            if target_vol > self.hw_device.syringe_volume:
                logger.error(
                    f"Cannot withdraw target volume {volume}! "
                    f"Max volume left is {self.hw_device.syringe_volume - current_volume}!",
                )
                return False

        await self.hw_device.set_to_volume(target_vol, ureg.Quantity(rate), self.pump_code)
        logger.info(f"withdrawing is run. it will take {ureg.Quantity(volume) / ureg.Quantity(rate)} to finish.")
        return await self.hw_device.get_pump_status(self.pump_code)
