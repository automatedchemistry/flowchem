from __future__ import annotations

from flowchem.components.technical.power import PowerSwitch
from flowchem.devices.flowchem_device import FlowchemDevice


class Relay(PowerSwitch):
    """
    Relay-based digital switch component.

    This class represents a relay box channel (digital on/off switch) that can be
    controlled through the Flowchem API. Each channel can be toggled between ON
    and OFF states, similar to how a hardware relay or solid-state switch behaves.

    Ontology:
        - Subclass of ``saref:Switch`` —
          A device that can switch something on or off.
          (https://w3id.org/saref#Switch)
        - Performs the function ``saref:OnOffFunction`` or ``saref:OpenCloseFunction``.
    """

    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        """
        Initialize a Relay component.

        Args:
            name: Human-readable identifier for this relay.
            hw_device: The underlying FlowchemDevice representing the hardware.

        Notes:
            - Ontology alignment: modeled as a ``saref:Switch``.
        """
        super().__init__(name, hw_device)

        # Ontology: A device of category Switch performing OnOffFunction/OpenCloseFunction.
        self.component_info.owl_subclass_of.append(
            "https://w3id.org/saref#Switch",
        )

    async def power_on(self, channel: str) -> bool:  # type:ignore[override]
        """
        Switch a relay channel ON.

        Args:
            channel: Identifier of the relay channel to be switched.

        Returns:
            True if the channel was successfully switched on, False otherwise

        Ontology:
            This method corresponds to a ``saref:OnCommand`` in the
            context of a ``saref:OnOffFunction``.
        """
        return True

    async def power_off(self, channel: str) -> bool:  # type:ignore[override]
        """
        Switch a relay channel OFF.

        Args:
            channel: Identifier of the relay channel to be switched.

        Returns:
            True if the channel was successfully switched off, False otherwise

        Ontology:
            This method corresponds to a ``saref:OffCommand`` in the
            context of a ``saref:OnOffFunction``.
        """
        return True
