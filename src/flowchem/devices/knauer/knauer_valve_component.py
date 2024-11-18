"""Knauer valve component."""
from __future__ import annotations

from typing import TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from .knauer_valve import KnauerValve
from flowchem.components.valves.distribution_valves import (
    SixPortDistributionValve,
    SixteenPortDistributionValve,
    TwelvePortDistributionValve,
)
from flowchem.components.valves.injection_valves import SixPortTwoPositionValve


class KnauerInjectionValve(SixPortTwoPositionValve):
    hw_device: KnauerValve  # for typing's sake

    def __init__(self, name: str, hw_device: KnauerValve) -> None:
        """Create a ValveControl object."""
        super().__init__(name, hw_device)

        self.add_api_route("/monitor_position", self.get_monitor_position, methods=["GET"])
        self.add_api_route("/monitor_position", self.set_monitor_position, methods=["PUT"])

    class LoadInject(Enum):
        LOAD = "L"
        INJECT = "I"

    def _change_connections(self, raw_position: str | int, reverse: bool = False):
        position_mapping = {0: "L", 1: "I"}
        if reverse:
            return str([key for key, value in position_mapping.items() if value == raw_position][0])
        else:
            if type(raw_position) == int:
                return position_mapping[raw_position]
            else:
                raise TypeError

    async def get_monitor_position(self) -> str:
        """Get current valve position."""
        pos = self.LoadInject(await self.hw_device.get_raw_position())
        return pos.name

    async def set_monitor_position(self, position: str):
        """Move valve to position."""
        try:
            return await self.hw_device.set_raw_position(self.LoadInject[position.upper()].value)
        except KeyError as e:
            raise Exception(f"Please give allowed positions {[pos.name for pos in self.LoadInject]}") from e


class Knauer6PortDistributionValve(SixPortDistributionValve):
    """KnauerValve of type SIX_PORT_SIX_POSITION."""

    hw_device: KnauerValve  # for typing's sake

    def __init__(self, name: str, hw_device: KnauerValve) -> None:
        """Create a ValveControl object."""
        super().__init__(name, hw_device)

        self.add_api_route("/monitor_position", self.get_monitor_position, methods=["GET"])
        self.add_api_route("/monitor_position", self.set_monitor_position, methods=["PUT"])

    def _change_connections(self, raw_position: int, reverse: bool = False):
        if reverse:
            return raw_position - 1
        else:
            return raw_position + 1

    async def get_monitor_position(self) -> str:
        return await self.hw_device.get_raw_position()

    async def set_monitor_position(self, position: str):
        return await self.hw_device.set_raw_position(position)


class Knauer12PortDistributionValve(TwelvePortDistributionValve):
    """KnauerValve of type SIX_PORT_SIX_POSITION."""

    hw_device: KnauerValve  # for typing's sake

    def __init__(self, name: str, hw_device: KnauerValve) -> None:
        """Create a ValveControl object."""
        super().__init__(name, hw_device)

        self.add_api_route("/monitor_position", self.get_monitor_position, methods=["GET"])
        self.add_api_route("/monitor_position", self.set_monitor_position, methods=["PUT"])

    def _change_connections(self, raw_position: int, reverse: bool = False):
        if reverse:
            return raw_position - 1
        else:
            return raw_position + 1

    async def get_monitor_position(self) -> str:
        return await self.hw_device.get_raw_position()

    async def set_monitor_position(self, position: str):
        return await self.hw_device.set_raw_position(position)


class Knauer16PortDistributionValve(SixteenPortDistributionValve):
    """KnauerValve of type SIX_PORT_SIX_POSITION."""

    hw_device: KnauerValve  # for typing's sake

    def __init__(self, name: str, hw_device: KnauerValve) -> None:
        """Create a ValveControl object."""
        super().__init__(name, hw_device)

        self.add_api_route("/monitor_position", self.get_monitor_position, methods=["GET"])
        self.add_api_route("/monitor_position", self.set_monitor_position, methods=["PUT"])

    def _change_connections(self, raw_position: int, reverse: bool = False):
        if reverse:
            return raw_position - 1
        else:
            return raw_position + 1

    async def get_monitor_position(self) -> str:
        return await self.hw_device.get_raw_position()

    async def set_monitor_position(self, position: str):
        return await self.hw_device.set_raw_position(position)
