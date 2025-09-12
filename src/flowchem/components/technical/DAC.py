from __future__ import annotations

from flowchem.components.technical.power import PowerSwitch
from flowchem.devices.flowchem_device import FlowchemDevice


class DigitalAnalogSignal(PowerSwitch):
    """
    Digital-to-Analog Signal component.

    This class represents a device that converts a digital command into an
    analog output signal (e.g., voltage level, current, or other continuous
    value). It inherits from ``PowerSwitch`` to provide a standard interface
    within the Flowchem framework.

    Ontology:
        Subclass of ``sosa:Actuator`` —
        An actuator is a device that is used by, or implements, an Actuation
        (W3C SOSA/SSN Ontology: http://www.w3.org/ns/sosa/Actuator).
    """
    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        """
        Initialize a DigitalAnalogSignal component.

        Args:
            name: Human-readable identifier for this component.
            hw_device: The underlying hardware device this component controls.

        Notes:
            Registers an API route ``/channel`` for setting channel values.
        """
        super().__init__(name, hw_device)
        self.add_api_route("/channel", self.set_channel, methods=["PUT"])
        self.add_api_route("/channel", self.read_channel, methods=["GET"])

        # Ontology: Actuator - A device that is used by, or implements, an (Actuation).
        self.component_info.owl_subclass_of.append(
            "http://www.w3.org/ns/sosa/Actuator",
        )

    async def read_channel(self, channel: str) -> float:
        """
        Read the DAC output of a channel.

        Args:
            channel (str): DAC channel index.
        """
        return -1

    async def set_channel(self, channel: str, value: float) -> bool:
        """
        Set the analog output value of a channel.

        Args:
            channel: The identifier or name of the channel to control.
            value: The analog value to set (e.g., voltage in volts).

        Returns:
            True if the value was accepted and applied successfully.

        Ontology:
            This operation corresponds to a ``sosa:Actuation`` event, where
            the actuator modifies a property in the environment.
        """
        return True