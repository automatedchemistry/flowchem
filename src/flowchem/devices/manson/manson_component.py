from __future__ import annotations

from typing import TYPE_CHECKING

from flowchem.components.technical.power import PowerControl

if TYPE_CHECKING:
    from flowchem.devices import MansonPowerSupply


class MansonPowerControl(PowerControl):
    hw_device: MansonPowerSupply  # for typing's sake

    async def set_current(self, current: str):
        """Set the target current using a "magnitude and unit" format string.

        Args:
            current (str): The desired current as a string in "magnitude and unit" format (e.g., '5 A', '500 mA').

        Returns:
            Awaitable: Result of the set_current operation from the hardware device.
        """
        return await self.hw_device.set_current(current)

    async def get_current(self) -> float:
        """Retrieve the current output in Amperes.

        Returns:
            float: The current output in Amperes.
        """
        return await self.hw_device.get_output_current()

    async def set_voltage(self, voltage: str):
        """Set the target voltage using a "magnitude and unit" format string.

        Args:
            voltage (str): The desired voltage as a string in "magnitude and unit" format (e.g., '12 V', '3.3 V').

        Returns:
            Awaitable: Result of the set_voltage operation from the hardware device.
        """
        return await self.hw_device.set_voltage(voltage)

    async def get_voltage(self) -> float:
        """Retrieve the current output voltage in Volts.

        Returns:
            float: The current output voltage in Volts.
        """
        return await self.hw_device.get_output_voltage()

    async def power_on(self):
        """Turn on the power supply output.

        Returns:
            Awaitable: Result of the power on operation from the hardware device.
        """
        return await self.hw_device.output_on()

    async def power_off(self):
        """Turn off the power supply output.

        Returns:
            Awaitable: Result of the power off operation from the hardware device.
        """
        return await self.hw_device.output_off()
