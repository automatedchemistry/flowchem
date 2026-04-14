"""Vici valve component."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .vici_valve import ViciValve
from flowchem.components.valves.injection_valves import SixPortTwoPositionValve


class ViciInjectionValve(SixPortTwoPositionValve):
    hw_device: ViciValve  # for typing's sake

    def __init__(self, name: str, hw_device: ViciValve) -> None:
        super().__init__(name, hw_device)
        self.add_api_route("/timed_toggle", self.timed_toggle, methods=["PUT"])

    # todo this needs to be adapted to new code
    def _change_connections(
        self, raw_position: int | str, reverse: bool = False
    ) -> str:
        if reverse:
            translated = {"A": "0", "B": "1"}.get(str(raw_position).upper())
        else:
            translated = {"0": "A", "1": "B"}.get(str(raw_position))
        if translated is None:
            translated = str(raw_position)
        return translated

    async def timed_toggle(self, injection_time: str) -> bool:

        await self.hw_device.timed_toggle(injection_time=injection_time)
        return True
