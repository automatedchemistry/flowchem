"""Light control."""

from __future__ import annotations

from typing import TYPE_CHECKING

from flowchem.components.flowchem_component import FlowchemComponent

if TYPE_CHECKING:
    from flowchem.devices.flowchem_device import FlowchemDevice


class Photoreactor(FlowchemComponent):
    """A generic photoreactor."""

    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        super().__init__(name, hw_device)

        self.add_api_route("/intensity", self.set_intensity, methods=["PUT"])
        self.add_api_route("/intensity", self.get_intensity, methods=["GET"])

        self.add_api_route("/power-on", self.power_on, methods=["PUT"])
        self.add_api_route("/power-off", self.power_off, methods=["PUT"])

    async def set_intensity(self, percent: int):
        """Set light intensity (in percent)."""
        ...

    async def get_intensity(self) -> int:  # type: ignore
        """Get current light intensity (in percent)."""
        ...

    async def power_on(self):
        """Turn on light."""
        ...

    async def power_off(self):
        """Turn off light."""
        ...
