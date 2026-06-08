"""Flowchem component for NI-9477 digital outputs."""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from flowchem.components.technical.MultiChannels import MultiChannelRelay

if TYPE_CHECKING:
    from .ni9477 import NI9477


class NI9477Relay(MultiChannelRelay):
    """Relay-style interface for the 32 digital output lines of an NI-9477."""

    def __init__(self, name: str, hw_device: "NI9477") -> None:
        super().__init__(name=name, hw_device=hw_device)
        self.hw_device: NI9477
        self.add_api_route(
            "/channel_set_point",
            self.read_channel_set_point,
            methods=["GET"],
        )

    async def power_on(self, channel: str | int = "1") -> bool:  # type: ignore[override]
        """Activate one NI-9477 output channel."""
        try:
            return await self.hw_device.set_channel(channel=channel, active=True)
        except ValueError as error:
            logger.error(str(error))
            return False

    async def power_off(self, channel: str | int = "1") -> bool:  # type: ignore[override]
        """Deactivate one NI-9477 output channel."""
        try:
            return await self.hw_device.set_channel(channel=channel, active=False)
        except ValueError as error:
            logger.error(str(error))
            return False

    async def is_on(self, channel: str | int = "1") -> bool:  # type: ignore[override]
        """Return whether one NI-9477 output channel is active."""
        return bool(await self.read_channel_set_point(channel=channel))

    async def switch_multiple_channel(self, values: str) -> bool:
        """Set all NI-9477 output states from a compact string.

        The string may contain up to 32 digits. ``0`` means OFF; any non-zero
        digit means ON. Shorter strings are padded with OFF values.
        """
        try:
            states = self._parse_values(values)
        except ValueError as error:
            logger.error(str(error))
            return False
        return await self.hw_device.set_channels(states)

    async def read_channel_set_point(self, channel: str | int = "1") -> int | None:
        """Return 1 when the channel is active, 0 when inactive."""
        try:
            return int(self.hw_device.get_channel_state(channel=channel))
        except ValueError as error:
            logger.error(str(error))
            return None

    async def read_channels_set_point(self) -> list[int]:
        """Return the cached active state for all 32 channels."""
        return [int(state) for state in self.hw_device.get_channel_states()]

    @staticmethod
    def _parse_values(values: str) -> list[bool]:
        if len(values) > 32:
            raise ValueError("NI9477 has 32 output channels; at most 32 values can be provided.")
        if any(not character.isdigit() for character in values):
            raise ValueError("NI9477 channel values must be digits, where 0 is OFF and non-zero is ON.")
        states = [character != "0" for character in values]
        return states + [False] * (32 - len(states))
