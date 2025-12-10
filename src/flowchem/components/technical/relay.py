from __future__ import annotations

from flowchem.components.technical.power import PowerSwitch
from flowchem.devices.flowchem_device import FlowchemDevice


class Relay(PowerSwitch):
    """
    Relay-based digital switch component.

    The `Relay` class represents a controllable digital on/off switch channel, typically
    implemented as a hardware relay or solid-state switch. It can be toggled between
    ON and OFF states using the Flowchem API.

    Each instance corresponds to a specific relay channel within a physical or virtual
    relay device.

    Ontology:
        - **Subclass of**: ``saref:Switch`` — A device capable of switching something on or off.
          (https://w3id.org/saref#Switch)
        - **Performs function**: ``saref:OnOffFunction`` or ``saref:OpenCloseFunction``

    Attributes:
        INSTANCES (dict[str, Relay]): Registry of all Relay instances, keyed by
            ``"<device_name>/<relay_name>"`` for connection tracking.
    """

    INSTANCES: dict[str, "Relay"] = {}

    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        """
        Initialize a Relay component.

        Args:
            name (str): Human-readable identifier for this relay channel.
            hw_device (FlowchemDevice): The underlying Flowchem device representing the
                physical or simulated hardware interface.

        Notes:
            - The Relay is modeled as a ``saref:Switch`` performing an ``OnOffFunction``.
            - Each instance is automatically registered in ``Relay.INSTANCES`` for
              device-to-component mapping.
        """
        super().__init__(name, hw_device)

        self.add_api_route("/is-on", self.power_off, methods=["GET"])

        # Ontology alignment
        self.component_info.owl_subclass_of.append("https://w3id.org/saref#Switch")

        # Register instance globally for device-component tracking
        self.INSTANCES[self.hw_device.name + "/" + self.name] = self

    async def power_on(self, **kwargs) -> bool:  # type:ignore[override]
        """
        Switch the relay channel ON.

        This asynchronous method should send the appropriate ON command to the hardware.
        It activates the relay, closing the circuit and allowing current flow.

        Returns:
            bool: True if the relay was successfully switched ON, False otherwise.

        Raises:
            NotImplementedError: If the method is not overridden by a subclass.
        """
        raise NotImplementedError

    async def power_off(self, **kwargs) -> bool:  # type:ignore[override]
        """
        Switch the relay channel OFF.

        This asynchronous method should send the appropriate OFF command to the hardware.
        It deactivates the relay, opening the circuit and stopping current flow.

        Returns:
            bool: True if the relay was successfully switched OFF, False otherwise.

        Raises:
            NotImplementedError: If the method is not overridden by a subclass.
        """
        raise NotImplementedError

    async def is_on(self, **kwargs) -> bool:
        """
        Check whether the relay is currently ON.

        This asynchronous method queries the current state of the relay channel
        to determine if it is active (ON) or inactive (OFF).

        Returns:
            bool: True if the relay is ON, False if it is OFF.

        Raises:
            NotImplementedError: If the method is not overridden by a subclass.
        """
        raise NotImplementedError


