"""Azura compact pump component."""
from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from flowchem import ureg

if TYPE_CHECKING:
    from .azura_compact import AzuraCompact
from flowchem.components.pumps.hplc_pump import HPLCPump


def isfloat(rate: str) -> bool:
    try:
        float(rate)
        return True
    except ValueError:
        return False


class AzuraCompactPump(HPLCPump):
    """
    Azura Compact Pump component for interfacing with the AzuraCompact hardware.

    This class inherits from HPLCPump and provides specific implementations
    for controlling the Azura Compact pump device. It allows for starting,
    stopping, and querying the pump's status.

    Attributes:
        hw_device (AzuraCompact): An instance of the AzuraCompact hardware device.

    Methods:
        infuse(rate: str = "", volume: str = "") -> bool:
            Starts the infusion process with a specified flow rate. The volume parameter is ignored.
            If the rate is numeric without units, it assumes "ml/min" as the default unit.

        stop() -> None:
            Stops the infusion process.

        is_pumping() -> bool:
            Checks whether the pump is currently running.

    Parameters:
        name (str): The name of the pump.
        hw_device (AzuraCompact): An instance of the AzuraCompact hardware device.
    """

    hw_device: AzuraCompact  # for typing's sake

    def __init__(self, name: str, hw_device: AzuraCompact) -> None:
        """Initialize the AzuraCompactPump component.

        Args:
            name (str): The name of the pump.
            hw_device (AzuraCompact): An instance of the AzuraCompact hardware device.
        """
        super().__init__(name, hw_device)

    async def infuse(self, rate: str = "", volume: str = "") -> bool:
        """Start infusion with the specified flow rate.

        Args:
            rate (str): The desired flow rate, which can include units (e.g., "10 ml/min").
                        If the rate is a numeric value, it assumes "ml/min" as the unit.
            volume (str): The desired volume for infusion. This parameter is currently ignored
                          by the Azura Compact pump.

        Returns:
            bool: True if the infusion command was successfully sent, False otherwise.
        """
        if volume:
            logger.warning(f"Volume parameter ignored: not supported by {self.name}!")

        if isfloat(rate):
            rate = "0 ml/min"
        if rate.isnumeric():
            rate += " ml/min"
            logger.warning("Units missing, assuming ml/min!")

        parsed_rate = ureg.Quantity(rate)

        await self.hw_device.set_flow_rate(rate=parsed_rate)
        return await self.hw_device.infuse()

    async def stop(self):
        """Stop the pumping process.

        Stops the pump if it is currently running.
        """
        await self.hw_device.stop()

    async def is_pumping(self) -> bool:
        """Check if the pump is currently running.

        Returns:
            bool: True if the pump is running, False otherwise.
        """
        return self.hw_device.is_running()
