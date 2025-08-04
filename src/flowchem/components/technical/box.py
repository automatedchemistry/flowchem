"""Electronic Box Control."""

from __future__ import annotations

from typing import TYPE_CHECKING, Union

from flowchem.components.flowchem_component import FlowchemComponent

if TYPE_CHECKING:
    from flowchem.devices.flowchem_device import FlowchemDevice

Channel = Union[int, str]
DigitalValue = Union[int, bool]


class ElectronicBox(FlowchemComponent):
    """A generic electronic box with input/output channels.

    Subclasses should override the low-level methods to interact with real hardware.
    """

    def __init__(self, name: str, hw_device: "FlowchemDevice") -> None:
        super().__init__(name, hw_device)

        self.add_api_route("/channel", self.read_channel, methods=["GET"])
        self.add_api_route("/channel", self.set_channel, methods=["PUT"])


    async def read_channel(self, channel: Channel) -> int:
        """Read an electronic signal from a channel."""
        return 0

    async def set_channel(self, channel: Channel, value: DigitalValue) -> bool:
        """Set the digital state of a channel."""
        return True