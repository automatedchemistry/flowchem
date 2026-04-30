"""Mass Flow Control."""

from __future__ import annotations

from typing import TYPE_CHECKING

from flowchem.components.flowchem_component import FlowchemComponent

if TYPE_CHECKING:
    from flowchem.devices.flowchem_device import FlowchemDevice


class MassFlowController(FlowchemComponent):
    """A generic mass flow controller."""

    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        """
        Constructs the MassFlowController component.

        Parameters:
        -----------
        name : str
            The name of the MassFlowController component.
        hw_device : FlowchemDevice
            The hardware device (MassFlowController) this component interfaces with.
        """
        super().__init__(name, hw_device)

        self.add_api_route("/set-flow-rate", self.set_flow_setpoint, methods=["PUT"])
        self.add_api_route("/get-flow-rate", self.get_flow_setpoint, methods=["GET"])
        self.add_api_route("/stop", self.stop, methods=["PUT"])

    async def set_flow_setpoint(self, flowrate: str = "0 ml/min") -> bool:
        """Set the mass flow controller setpoint (in ml/min)."""
        raise NotImplementedError("Subclasses must override this method.")

    async def get_flow_setpoint(self) -> float:
        """Get current mass flow controller setpoint (in ml/min)."""
        raise NotImplementedError("Subclasses must override this method.")

    async def stop(self) -> bool:
        """Stop the mass flow controller by setting the flow rate to 0 ml/min."""
        raise NotImplementedError("Subclasses must override this method.")
