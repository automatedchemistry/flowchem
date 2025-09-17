"""CVC3000 Pressure Contol component."""
from __future__ import annotations

from typing import TYPE_CHECKING

from flowchem.components.technical.pressure import PressureControl
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.vacuubrand.constants import ProcessStatus, PumpState

if TYPE_CHECKING:
    from flowchem.devices.vacuubrand.cvc3000 import CVC3000


class CVC3000PressureControl(PressureControl):
    """
    Control component for managing pressure in the Vacuubrand CVC3000 vacuum system.

    This class provides methods to set and get pressure, check if the target pressure has been reached,
    and control the power state of the pressure control system.

    Attributes:
    -----------
    hw_device : CVC3000
        The hardware device instance of the CVC3000 vacuum controller.

    Methods:
    --------
    set_pressure(pressure: str) -> bool:
        Set the target pressure using a string representation - unit have to be provided.
    get_pressure() -> float:
        Retrieve the current pressure from the device in mbar.
    is_target_reached() -> bool:
        Check if the target pressure has been reached.
    power_on() -> bool:
        Turn on the pressure control.
    power_off() -> bool:
        Turn off the pressure control.
    """

    hw_device: CVC3000  # for typing's sake

    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        """
        Initialize the CVC3000PressureControl component.

        Parameters:
        -----------
        name : str
            The name assigned to this pressure control component.
        hw_device : FlowchemDevice
            The hardware device instance associated with this pressure control component.
        """
        super().__init__(name, hw_device)

        self.add_api_route(
            "/status",
            self.hw_device.status,
            response_model=ProcessStatus,
            methods=["PUT"],
        )

    async def set_pressure(self, pressure: str):
        """
        Set the target pressure on the CVC3000 device.

        Parameters:
        -----------
        pressure : str
            The target pressure to be set, expressed in a string format (e.g., mbar).
            For example: "500 mbar"

        Returns:
        --------
        bool
            Returns True if the operation was successful.
        """
        set_p = await super().set_pressure(pressure)
        return await self.hw_device.set_pressure(set_p)

    async def get_pressure(self) -> float:
        """
        Retrieve the current pressure from the CVC3000 device.

        Returns:
        --------
        float
            The current pressure in mbar.
        """
        return await self.hw_device.get_pressure()

    async def is_target_reached(self) -> bool:
        """
        Check if the target pressure has been reached.

        Returns:
        --------
        bool
            Returns True if the target pressure has been reached, False otherwise.
        """
        status = await self.hw_device.status()
        return status.state == PumpState.VACUUM_REACHED

    async def power_on(self) -> str:
        """
        Turn on the pressure control.

        Returns:
        --------
        str
            Returns binary string if the command to start the pressure control was successful.
        """
        return await self.hw_device._send_command_and_read_reply("START")

    async def power_off(self):
        """
        Turn off the pressure control.

        Returns:
        --------
        str
            Returns binary string if the command to stop the pressure control was successful.
        """
        return await self.hw_device._send_command_and_read_reply("STOP")
