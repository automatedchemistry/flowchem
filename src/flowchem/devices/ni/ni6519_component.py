"""Flowchem components for NI-6519 digital I/O."""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from flowchem.components.flowchem_component import FlowchemComponent
from flowchem.components.technical.MultiChannels import MultiChannelRelay

if TYPE_CHECKING:
    from .ni6519 import NI6519


class NI6519Relay(MultiChannelRelay):
    """Relay-style interface for the 16 sinking outputs of an NI-6519."""

    def __init__(self, name: str, hw_device: "NI6519") -> None:
        super().__init__(name=name, hw_device=hw_device)
        self.hw_device: NI6519
        self.add_api_route(
            "/channel_set_point",
            self.read_channel_set_point,
            methods=["GET"],
        )

    async def power_on(self, channel: str | int = "1") -> bool:  # type: ignore[override]
        """Activate one NI-6519 output channel."""
        try:
            return await self.hw_device.set_output_channel(channel=channel, active=True)
        except ValueError as error:
            logger.error(str(error))
            return False

    async def power_off(self, channel: str | int = "1") -> bool:  # type: ignore[override]
        """Deactivate one NI-6519 output channel."""
        try:
            return await self.hw_device.set_output_channel(
                channel=channel, active=False
            )
        except ValueError as error:
            logger.error(str(error))
            return False

    async def is_on(self, channel: str | int = "1") -> bool:  # type: ignore[override]
        """Return whether one NI-6519 output channel is active."""
        return bool(await self.read_channel_set_point(channel=channel))

    async def switch_multiple_channel(self, values: str) -> bool:
        """Set all NI-6519 output states from a compact string."""
        try:
            states = self._parse_values(values)
        except ValueError as error:
            logger.error(str(error))
            return False
        return await self.hw_device.set_output_channels(states)

    async def read_channel_set_point(self, channel: str | int = "1") -> int | None:
        """Return 1 when the output channel is active, 0 when inactive."""
        try:
            return int(self.hw_device.get_output_channel_state(channel=channel))
        except ValueError as error:
            logger.error(str(error))
            return None

    async def read_channels_set_point(self) -> list[int]:
        """Return cached active state for all 16 output channels."""
        return [int(state) for state in self.hw_device.get_output_channel_states()]

    @staticmethod
    def _parse_values(values: str) -> list[bool]:
        if len(values) > 16:
            raise ValueError(
                "NI6519 has 16 output channels; at most 16 values can be provided."
            )
        if any(not character.isdigit() for character in values):
            raise ValueError(
                "NI6519 channel values must be digits, where 0 is OFF and non-zero is ON."
            )
        states = [character != "0" for character in values]
        return states + [False] * (16 - len(states))


class NI6519DigitalInput(FlowchemComponent):
    """Read-only interface for the 16 digital inputs of an NI-6519."""

    def __init__(self, name: str, hw_device: "NI6519") -> None:
        super().__init__(name=name, hw_device=hw_device)
        self.hw_device: NI6519
        self.add_api_route("/read", self.read, methods=["GET"])
        self.add_api_route("/read_all", self.read_all, methods=["GET"])

    async def read(self, channel: str | int = "1") -> int | None:
        """Read one digital input channel, returning 1 for high and 0 for low."""
        try:
            return int(await self.hw_device.read_input_channel(channel))
        except ValueError as error:
            logger.error(str(error))
            return None

    async def read_all(self) -> list[int]:
        """Read all 16 digital input channels."""
        return [int(state) for state in await self.hw_device.read_input_channels()]
