"""Base pump component."""

from flowchem.components.flowchem_component import FlowchemComponent
from flowchem.components.reachability import ReachabilityStatus
from flowchem.devices.flowchem_device import FlowchemDevice


class Pump(FlowchemComponent):
    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        """A generic pump."""
        super().__init__(name, hw_device)
        self.add_api_route("/infuse", self.infuse, methods=["PUT"])
        self.add_api_route("/stop", self.stop, methods=["PUT"])
        self.add_api_route("/is-pumping", self.is_pumping, methods=["GET"])
        if self.is_withdrawing_capable():
            self.add_api_route("/withdraw", self.withdraw, methods=["PUT"])
        self.component_info.type = "Pump"

    async def infuse(self, rate: str = "", volume: str = "") -> bool:
        """Start infusion."""
        raise NotImplementedError

    async def stop(self):
        """Stop pumping."""
        raise NotImplementedError

    async def is_pumping(self) -> bool:
        """Is pump running?"""
        raise NotImplementedError

    @staticmethod
    def is_withdrawing_capable() -> bool:
        """Can the pump reverse its normal flow direction?

        Returns False by default. Override in subclasses that support withdrawal.
        """
        return False

    async def withdraw(self, rate: str = "", volume: str = "") -> bool:
        """Pump in the opposite direction of infuse."""
        raise NotImplementedError

    async def is_reachable(self) -> ReachabilityStatus:
        """Return ONLINE if the pump responds to a status query.

        Delegates to is_pumping(), which every concrete pump overrides with
        a real hardware query. Any successful response confirms the device is alive.
        """
        try:
            await self.is_pumping()
            return ReachabilityStatus.ONLINE
        except Exception:
            return ReachabilityStatus.OFFLINE
