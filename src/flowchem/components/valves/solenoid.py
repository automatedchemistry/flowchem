from __future__ import annotations

from flowchem.components.flowchem_component import FlowchemComponent
from flowchem.devices.flowchem_device import FlowchemDevice


class SolenoidValve(FlowchemComponent):
    """
    A generic solenoid valve component in the FlowChem framework.

    This class provides a simple interface to control a solenoid valve
    via HTTP API routes. It inherits from `FlowchemComponent` and
    links to a specific hardware device (`FlowchemDevice`).

    API routes exposed:
        - PUT `/open`:  Energizes the solenoid valve (opens the flow path).
        - PUT `/close`: De-energizes the solenoid valve (closes the flow path).
        - GET `/status`: Returns the current state of the valve (open/closed).

    Parameters
    ----------
    name : str
        Identifier name for the solenoid valve component.
    hw_device : FlowchemDevice
        The hardware device instance that controls the valve.
    """

    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:

        super().__init__(name, hw_device)
        self.add_api_route("/open", self.open, methods=["PUT"])
        self.add_api_route("/close", self.close, methods=["PUT"])
        self.add_api_route("/status", self.status, methods=["GET"])

    async def open(self):
        """
        Open the solenoid valve.

        This method energizes the solenoid, switching the valve to the
        "open" state, allowing flow through the channel.
        """
        ...

    async def close(self):
        """
        Close the solenoid valve.

        This method de-energizes the solenoid, switching the valve to
        the "closed" state, stopping flow through the channel.
        """
        ...

    async def status(self) -> bool:
        """
        Get the current valve status.

        Returns
        -------
        bool
            `True` if the valve is open, `False` if closed.
        """
        return True


class SolenoidValve2way(SolenoidValve):
    """
    A 2-way solenoid valve.

    This specialized class inherits from `SolenoidValve` and represents
    a standard 2-way configuration (one inlet, one outlet).
    """
    ...