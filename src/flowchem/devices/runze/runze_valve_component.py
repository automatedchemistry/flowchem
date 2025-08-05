"""Runze valve component."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .runze_valve import RunzeValve
from flowchem.components.valves.distribution_valves import (
    SixPortDistributionValve,
    EightPortDistributionValve,
    TenPortDistributionValve,
    TwelvePortDistributionValve,
    SixteenPortDistributionValve,
)


class Runze6PortDistributionValve(SixPortDistributionValve):
    """RunzeValve of type SIX_PORT_SIX_POSITION."""

    hw_device: RunzeValve

    def __init__(self, name: str, hw_device: RunzeValve) -> None:
        super().__init__(name, hw_device)
        self.add_api_route("/monitor_position", self.get_monitor_position, methods=["GET"])
        self.add_api_route("/monitor_position", self.set_monitor_position, methods=["PUT"])

    def _change_connections(self, raw_position: str | int, reverse: bool = False):
        """
        Change the valve connections based on the internal valve logic position numbering.

        The `raw_position` refers to the internal valve logic numbering of positions (not to be confused with actual port numbers).

        Args:
            raw_position (int or str): The raw position to switch to, according to valve logic.
            reverse (bool): If True, reverse the mapping.

        Notes:
            The motor rotates using an internal code disc and automatically selects
            the optimal path. (Ref. Manual)

        Returns:
            int: The mapped position, specific to the valve and corresponding to the manufacturer implementation and commands.
        """
        if reverse:
            return int(raw_position) - 1
        else:
            return int(raw_position) + 1

    async def get_monitor_position(self) -> str:
        """Get current valve position."""
        return await self.hw_device.get_raw_position()

    async def set_monitor_position(self, position: str) -> bool:
        """Move valve to position."""
        return await self.hw_device.set_raw_position(position=position)


class Runze8PortDistributionValve(EightPortDistributionValve):
    """RunzeValve of type Eight_Port_Distribution."""

    hw_device: RunzeValve

    def __init__(self, name: str, hw_device: RunzeValve) -> None:
        super().__init__(name, hw_device)
        self.add_api_route("/monitor_position", self.get_monitor_position, methods=["GET"])
        self.add_api_route("/monitor_position", self.set_monitor_position, methods=["PUT"])

    def _change_connections(self, raw_position: str | int, reverse: bool = False):
        """
        Change the valve connections based on the internal valve logic position numbering.

        The `raw_position` refers to the internal valve logic numbering of positions (not to be confused with actual port numbers).

        Args:
            raw_position (int or str): The raw position to switch to, according to valve logic.
            reverse (bool): If True, reverse the mapping.

        Notes:
            The motor rotates using an internal code disc and automatically selects
            the optimal path. (Ref. Manual)

        Returns:
            int: The mapped position, specific to the valve and corresponding to the manufacturer implementation and commands.
        """
        if reverse:
            return int(raw_position) - 1
        else:
            return int(raw_position) + 1

    async def get_monitor_position(self) -> str:
        """Get current valve position."""
        return await self.hw_device.get_raw_position()

    async def set_monitor_position(self, position: str) -> bool:
        """Move valve to position."""
        return await self.hw_device.set_raw_position(position=position)


class Runze10PortDistributionValve(TenPortDistributionValve):
    """RunzeValve of type Ten_Port_Distribution."""

    hw_device: RunzeValve

    def __init__(self, name: str, hw_device: RunzeValve) -> None:
        super().__init__(name, hw_device)
        self.add_api_route("/monitor_position", self.get_monitor_position, methods=["GET"])
        self.add_api_route("/monitor_position", self.set_monitor_position, methods=["PUT"])

    def _change_connections(self, raw_position: str | int, reverse: bool = False):
        """
        Change the valve connections based on the internal valve logic position numbering.

        The `raw_position` refers to the internal valve logic numbering of positions (not to be confused with actual port numbers).

        Args:
            raw_position (int or str): The raw position to switch to, according to valve logic.
            reverse (bool): If True, reverse the mapping.

        Notes:
            The motor rotates using an internal code disc and automatically selects
            the optimal path. (Ref. Manual)

        Returns:
            int: The mapped position, specific to the valve and corresponding to the manufacturer implementation and commands.
        """
        if reverse:
            return int(raw_position) - 1
        else:
            return int(raw_position) + 1

    async def get_monitor_position(self) -> str:
        """Get current valve position."""
        return await self.hw_device.get_raw_position()

    async def set_monitor_position(self, position: str) -> bool:
        """Move valve to position."""
        return await self.hw_device.set_raw_position(position=position)


class Runze12PortDistributionValve(TwelvePortDistributionValve):
    """RunzeValve of type Twelve_Port_Distribution."""

    hw_device: RunzeValve

    def __init__(self, name: str, hw_device: RunzeValve) -> None:
        super().__init__(name, hw_device)
        self.add_api_route("/monitor_position", self.get_monitor_position, methods=["GET"])
        self.add_api_route("/monitor_position", self.set_monitor_position, methods=["PUT"])

    def _change_connections(self, raw_position: str | int, reverse: bool = False):
        """
        Change the valve connections based on the internal valve logic position numbering.

        The `raw_position` refers to the internal valve logic numbering of positions (not to be confused with actual port numbers).

        Args:
            raw_position (int or str): The raw position to switch to, according to valve logic.
            reverse (bool): If True, reverse the mapping.

        Notes:
            The motor rotates using an internal code disc and automatically selects
            the optimal path. (Ref. Manual)

        Returns:
            int: The mapped position, specific to the valve and corresponding to the manufacturer implementation and commands.
        """
        if reverse:
            return int(raw_position) - 1
        else:
            return int(raw_position) + 1

    async def get_monitor_position(self) -> str:
        """Get current valve position."""
        return await self.hw_device.get_raw_position()

    async def set_monitor_position(self, position: str) -> bool:
        """Move valve to position."""
        return await self.hw_device.set_raw_position(position=position)


class Runze16PortDistributionValve(SixteenPortDistributionValve):
    """RunzeValve of type Sixteen_Port_Distribution"""

    hw_device: RunzeValve

    def __init__(self, name: str, hw_device: RunzeValve) -> None:
        super().__init__(name, hw_device)
        self.add_api_route("/monitor_position", self.get_monitor_position, methods=["GET"])
        self.add_api_route("/monitor_position", self.set_monitor_position, methods=["PUT"])

    def _change_connections(self, raw_position: str | int, reverse: bool = False):
        """
        Change the valve connections based on the internal valve logic position numbering.

        The `raw_position` refers to the internal valve logic numbering of positions (not to be confused with actual port numbers).

        Args:
            raw_position (int or str): The raw position to switch to, according to valve logic.
            reverse (bool): If True, reverse the mapping.

        Notes:
            The motor rotates using an internal code disc and automatically selects
            the optimal path. (Ref. Manual)

        Returns:
            int: The mapped position, specific to the valve and corresponding to the manufacturer implementation and commands.
        """
        if reverse:
            return int(raw_position) - 1
        else:
            return int(raw_position) + 1

    async def get_monitor_position(self) -> str:
        """Get current valve position."""
        return await self.hw_device.get_raw_position()

    async def set_monitor_position(self, position: str) -> bool:
        """Move valve to position."""
        return await self.hw_device.set_raw_position(position=position)
