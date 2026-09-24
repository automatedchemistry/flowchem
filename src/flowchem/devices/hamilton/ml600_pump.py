"""ML600 component relative to pumping."""

from __future__ import annotations
import asyncio
from typing import TYPE_CHECKING, cast

from loguru import logger
import pint

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
        if self.hw_device.dual_syringe:
            self.add_api_route(
                "/set_to_volume_dual_syringes",
                self.set_to_volume_dual_syringes,
                methods=["PUT"],
            )
        self.add_api_route(
            "/get_current_volume", self.get_current_volume, methods=["GET"]
        )
        self.add_api_route(
            "/initialize_syringe", self.initialize_syringe, methods=["PUT"]
        )
        self.add_api_route("/wait_until_idle", self.wait_until_idle, methods=["GET"])

        self.pump_code = pump_code
        # self.add_api_route("/pump", self.get_monitor_position, methods=["GET"])

        # Signed ml/min from the last infuse()/withdraw() issued via this driver.
        # Used by get_flowrate(from_hardware=False), see there for why this exists.
        self._last_signed_rate: float = 0.0

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
        false means pump is not moving and buffer is empty."""
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
        self._last_signed_rate = 0.0
        # todo: sometime it take more then two seconds.
        await asyncio.sleep(1)
        if not await self.hw_device.get_pump_status(self.pump_code):
            return True
        else:
            logger.warning("the first check show false. try again.")
            await asyncio.sleep(1)
            return not await self.hw_device.get_pump_status(self.pump_code)

    async def get_flowrate(
        self, from_hardware: bool = False, sample_interval: str = "0.2 s"
    ) -> float:
        """Return the pump's current flow rate in ml/min (+infusing / -withdrawing).

        Hamilton's Protocol1/RNO+ command set has no live-speed register for the ML600:
        the only speed-related query (YQS) reports the configured default speed, not the
        speed of an in-progress move, and there is no motor tachometer feedback. So there
        are two ways to answer "what's the flow rate right now", selected by `from_hardware`:

        - False (default, "soft" tracking): report the rate/direction from the last
          infuse()/withdraw() call issued through this driver, 0 once stop() was called
          or the pump reports idle. Instant and stable, but not verified against the
          pump itself - it will be wrong if the syringe was driven by another controller,
          if the move already completed on its own (target volume reached), or after a stall.
        - True (hardware sampling): sample the real syringe position (YQP) twice,
          `sample_interval` apart, and derive ml/min (and sign) from the actual volume
          change. This is grounded in hardware, but takes ~`sample_interval` seconds per
          call and is noisier at low flow rates or short intervals.
        """
        if not from_hardware:
            return self._last_signed_rate if await self.is_pumping() else 0.0

        interval: pint.Quantity = ureg.Quantity(sample_interval)
        volume_before = await self.hw_device.get_current_volume(self.pump_code)
        await asyncio.sleep(interval.m_as("s"))
        volume_after = await self.hw_device.get_current_volume(self.pump_code)

        # Syringe volume decreases while infusing (dispensing) and increases while
        # withdrawing (drawing in), so this difference is already correctly signed.
        delta_ml = (volume_before - volume_after).m_as("ml")
        return delta_ml / interval.m_as("min")

    async def infuse(self, rate: str = "1 ml/min", volume: str = "") -> bool:
        """Start infusion with given rate and volume (both optional).

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
        effective_volume: pint.Quantity
        if not volume:
            target_vol: pint.Quantity = ureg.Quantity("0 ml")
            effective_volume = await self.hw_device.get_current_volume(self.pump_code)
            logger.warning("the volume to infuse is not provided. set to 0 ml")
        else:
            current_volume = await self.hw_device.get_current_volume(self.pump_code)
            effective_volume = ureg.Quantity(volume)
            target_vol = current_volume - ureg.Quantity(volume)
            if target_vol < 0:
                logger.error(
                    f"Cannot infuse target volume {volume}! "
                    f"Only {current_volume} in the syringe!",
                )
                return False

        await self.hw_device.set_to_volume(
            target_vol, ureg.Quantity(rate), self.pump_code
        )
        self._last_signed_rate = ureg.Quantity(rate).m_as("ml/min")
        logger.info(
            f"infusing is run. it will take {effective_volume / ureg.Quantity(rate)} to finish."
        )
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
            rate = cast(str, self.hw_device.config["default_withdraw_rate"])
            logger.warning(f"the flow rate is not provided. set to the default {rate}")
        syringe_volume = self.hw_device.syringe_volume(self.pump_code)
        if volume is None:
            target_vol = syringe_volume
            logger.warning(
                f"the volume to withdraw is not provided. set to {syringe_volume}"
            )
        else:
            current_volume = await self.hw_device.get_current_volume(self.pump_code)
            target_vol = current_volume + ureg.Quantity(volume)
            if target_vol > syringe_volume:
                logger.error(
                    f"Cannot withdraw target volume {volume}! "
                    f"Max volume left is {syringe_volume - current_volume}!",
                )
                return False

        await self.hw_device.set_to_volume(
            target_vol, ureg.Quantity(rate), self.pump_code
        )
        self._last_signed_rate = -ureg.Quantity(rate).m_as("ml/min")
        logger.info(
            "withdrawing is run. it will take "
            f"{ureg.Quantity(volume if volume else syringe_volume) / ureg.Quantity(rate)} to finish."
        )
        return await self.hw_device.get_pump_status(self.pump_code)

    async def set_to_volume(self, volume: str, rate: str = "1 ml/min") -> bool:
        target_volume: pint.Quantity = ureg.Quantity(volume)
        target_rate: pint.Quantity = ureg.Quantity(rate)
        await self.hw_device.set_to_volume(target_volume, target_rate, self.pump_code)
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
        speed = self.hw_device._flowrate_to_seconds_per_stroke(
            ureg.Quantity(rate), self.pump_code
        )
        return await self.hw_device.initialize_syringe(
            speed=ureg.Quantity(speed), pump=self.pump_code
        )

    async def wait_until_idle(self) -> bool:
        """Waits pump to be idle."""
        logger.debug("wait until pump idle")
        return await self.hw_device.wait_until_idle(pump=self.pump_code)

    async def is_idle(self) -> bool:
        """Check whether the syringe has finished its current move."""
        return await self.hw_device.is_idle(self.pump_code)

    async def set_to_volume_dual_syringes(
        self, target_volume: str, rate_left: str, rate_right: str, connection: str = ""
    ):
        """
        Executes a synchronized filling of both syringes.

        This function was created specifically for the platform,
        ensuring both syringes operate in perfect synchrony. Valve angles must
        be explicitly set to control flow direction on each side.
        Parameters:
        target_volume (ureg.Quantity): Volume to fill.
        rate (ureg.Quantity): Filling rate.
        valve_angles (dict): Dictionary with 'left' and 'right' keys specifying valve angle positions.
        """

        if connection == "":
            connection = "[[null,0],[2,3]]"
        valve_angles = {"left": connection, "right": connection}
        logger.debug(f"Setting volume of both syringes to {target_volume} ml")
        return await self.hw_device.set_to_volume_dual_syringes(
            target_volume=ureg(target_volume),
            rate_left=ureg(rate_left),
            rate_right=ureg(rate_right),
            valve_angles=valve_angles,
        )
