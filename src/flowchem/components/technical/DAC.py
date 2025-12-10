from __future__ import annotations

from flowchem.components.flowchem_component import FlowchemComponent
from flowchem.devices.flowchem_device import FlowchemDevice


class DigitalAnalogConverter(FlowchemComponent):
    """
    Digital-to-Analog Converter component.

    This class represents a device that converts a digital values into an
    analog output values (e.g., voltage level, current, or other continuous
    value). It inherits from ``PowerSwitch`` to provide a standard interface
    within the Flowchem framework.
    """
    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        """
        Initialize a DigitalAnalogConverter component.

        Args:
            name: Human-readable identifier for this component.
            hw_device: The underlying hardware device this component controls.

        Notes:
            Registers an API route ``/channel`` for setting channel values.
        """
        super().__init__(name, hw_device)
        self.add_api_route("/set", self.set, methods=["PUT"])
        self.add_api_route("/read", self.read, methods=["GET"])

    async def read(self) -> float:
        """
        Read the DAC output of a channel.
        """
        raise NotImplementedError

    async def set(self, value: str = "0 V") -> bool:
        """
        Set the analog output value of a channel.

        Args:
            value: The analog value to set (e.g., voltage in volts).

        Returns:
            True if the value was accepted and applied successfully.
        """
        raise NotImplementedError