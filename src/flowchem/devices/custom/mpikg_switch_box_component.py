"""Component of the Electronic Box Control MPIKG."""

from __future__ import annotations

from typing import TYPE_CHECKING, Union

from flowchem.components.technical.box import ElectronicBox

if TYPE_CHECKING:
    from .mpikg_switch_box import SwicthBoxMPIKG

Channel = Union[int, str]
DigitalValue = Union[int, bool]

# Threshold for interpreting an integer value as "True" / high
DIGITAL_ON_THRESHOLD = 2000


class SwicthBoxMPIKGComponent(ElectronicBox):
    """A generic electronic box with input/output channels.

    Subclasses should override the low-level methods to interact with real hardware.
    """
    async def read_channel(self, channel: Channel) -> int:
        """Read an electronic signal from a channel.

        Args:
            channel: Channel identifier (int or numeric string).

        Returns:
            Raw integer value from the hardware.

        Raises:
            ValueError: If the channel is not a valid integer or conversion fails.
            Exception: Propagates hardware access exceptions with context.
        """
        actual_channel = 0
        if isinstance(channel, str):
            if channel.isdigit():
                actual_channel = int(channel)
            else:
                raise ValueError(f"Channel must be an integer or digit string, got {channel!r}")
        return await self.hw_device.get_channel(channel=channel)

    async def set_channel(self, channel: Channel, value: DigitalValue) -> bool:
        """Set a digital state on a channel.

        Args:
            channel: Channel identifier (int or numeric string).
            value: Either bool or integer; integers > DIGITAL_ON_THRESHOLD are considered True.

        Returns:
            True if the operation succeeded.

        Raises:
            ValueError: If channel is invalid or value type unsupported.
            Exception: Propagates hardware access exceptions with context.
        """
        actual_channel = 0
        if isinstance(channel, str):
            if channel.isdigit():
                actual_channel = int(channel)
            else:
                raise ValueError(f"Channel must be an integer or digit string, got {channel!r}")
        actual_value = False
        if isinstance(value, int):
            actual_value = value > DIGITAL_ON_THRESHOLD
        return await self.hw_device.set_channel(channel=actual_channel, value=actual_value)