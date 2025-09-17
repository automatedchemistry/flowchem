"""Pressure control."""
from __future__ import annotations

from typing import TYPE_CHECKING

import pint
from loguru import logger

from flowchem import ureg
from flowchem.components.flowchem_component import FlowchemComponent

if TYPE_CHECKING:
    from flowchem.devices.flowchem_device import FlowchemDevice


class PressureControl(FlowchemComponent):
    """
    A generic pressure controller for managing and monitoring pressure.

    This component provides an interface to set and get pressure values, check if the target pressure has been reached,
    and control the power state of the pressure system.

    Attributes:
    -----------
    hw_device : FlowchemDevice
        The hardware device instance associated with this pressure control component.

    Methods:
    --------
    set_pressure(pressure: str) -> pint.Quantity:
        Set the target pressure using a string representation.
    get_pressure() -> float:
        Retrieve the current pressure from the device.
    is_target_reached() -> bool:
        Check if the target pressure has been reached.
    power_on() -> bool:
        Turn on the pressure control.
    power_off() -> bool:
        Turn off the pressure control.
    """

    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        """
        Initialize the PressureControl component.

        Parameters:
        -----------
        name : str
            The name assigned to this pressure control component.
        hw_device : FlowchemDevice
            The hardware device instance associated with this pressure control component.
        """
        super().__init__(name, hw_device)

        self.add_api_route("/pressure", self.set_pressure, methods=["PUT"])
        self.add_api_route("/pressure", self.get_pressure, methods=["GET"])

        self.add_api_route("/power-on", self.power_on, methods=["PUT"])
        self.add_api_route("/power-off", self.power_off, methods=["PUT"])

        self.add_api_route("/target-reached", self.is_target_reached, methods=["GET"])

    async def set_pressure(self, pressure: str) -> pint.Quantity:
        """
        Set the target pressure using a string representation.

        This method interprets the provided string to set the pressure. If no units are specified,
        'mbar' is assumed as the default unit.

        Parameters:
        -----------
        pressure : str
            The target pressure to be set, expressed in a string format.

        Returns:
        --------
        pint.Quantity
            The pressure value as a `pint.Quantity` object with units of 'mbar'.
        """
        # Add units (mbar) if none
        try:
            float(pressure)
        except ValueError:
            pass
        else:
            logger.warning("No units provided to set_pressure, assuming mbar.")
            pressure = pressure + "mbar"
        return ureg.Quantity(pressure)

    async def get_pressure(self) -> float:  # type: ignore
        """
        Retrieve the current pressure from the device.

        This method should be overridden in a subclass to interact with the specific hardware.

        Returns:
        --------
        float
            The current pressure.
        """
        ...

    async def is_target_reached(self) -> bool:  # type: ignore
        """
        Check if the target pressure has been reached.

        This method should be overridden in a subclass to provide the actual implementation
        for checking the pressure status.

        Returns:
        --------
        bool
            Returns True if the target pressure has been reached, False otherwise.
        """
        ...

    async def power_on(self):
        """
        Turn on the pressure control.

        This method should be implemented in a subclass to send the appropriate command
        to the hardware to activate the pressure control.

        Returns:
        --------
        str
            Returns binary string if the operation was successful.
        """
        ...

    async def power_off(self):
        """
        Turn off the pressure control.

        This method should be implemented in a subclass to send the appropriate command
        to the hardware to deactivate the pressure control.

        Returns:
        --------
        str
            Returns binary string if the operation was successful.
        """
        ...
