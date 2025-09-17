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
        self.add_api_route("/set_to_volume", self.set_to_volume, methods=["PUT"])
        self.add_api_route("/set_to_volume_dual_syringes", self.set_to_volume_dual_syringes, methods=["PUT"])
        self.add_api_route("/get_current_volume", self.get_current_volume, methods=["GET"])
        self.add_api_route("/initialize_syringe", self.initialize_syringe, methods=["PUT"])

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
        id_idle = await self.hw_device.is_idle(self.pump_code)
        return not id_idle

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
            logger.warning("The first check show false. Try again.")
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

    async def set_to_volume(self, volume: str, rate: str = "1 ml/min") -> bool:
        """
        Move the pump to an absolute target volume at a specified flow rate.

        This command sets the syringe pump to reach the given absolute volume
        (measured from the pump's zero reference) using the provided flow rate.
        Both `volume` and `rate` are parsed as physical quantities (e.g. "5 ml",
        "2.5 ml/min") and internally converted with Pint's unit registry.

        Args:
            volume (str): Absolute target volume to move the pump to. Must be a
                string that can be parsed into a Pint Quantity (e.g. "10 ml").
            rate (str, optional): Flow rate for the movement. Defaults to "1 ml/min".
                Must be a string that can be parsed into a Pint Quantity.

        Returns:
            bool: True if the pump reports a valid status after the move,
            False otherwise.
        """
        volume = ureg.Quantity(volume)
        rate = ureg.Quantity(rate)
        await self.hw_device.set_to_volume(volume, rate, self.pump_code)
        return await self.hw_device.get_pump_status(self.pump_code)

    async def get_current_volume(self) -> float:
        """Return current syringe volume in ml."""
        vol = await self.hw_device.get_current_volume(self.pump_code)
        return vol.m_as("ml")

    async def initialize_syringe(self, rate: str):
        """
        Initialize syringe on specified side only
        flowrate: ml/min
        """
        speed = self.hw_device._flowrate_to_seconds_per_stroke(ureg.Quantity(rate))
        return await self.hw_device.initialize_syringe(speed=ureg.Quantity(speed), pump=self.pump_code)

    async def set_to_volume_dual_syringes(self, target_volume: str, rate_left: str, rate_right: str) -> bool:
        """
        Executes a synchronized filling of both syringes.

        This function was created specifically for the platform,
        ensuring both syringes operate in perfect synchrony. Valve angles must
        be previously set to control flow direction on each side.
        Parameters:
        target_volume (ureg.Quantity): Volume to fill.
        rate (ureg.Quantity): Filling rate.
        """

        logger.debug(f"Setting volume of both syringes to {target_volume} ml")
        return await self.hw_device.set_to_volume_dual_syringes(
            target_volume=ureg(target_volume),
            rate_left=ureg(rate_left),
            rate_right=ureg(rate_right)
        )
