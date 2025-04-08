"""ML600 component relative to valve switching."""
from __future__ import annotations

from typing import TYPE_CHECKING

from flowchem.components.valves.distribution_valves import ThreePortFourPositionValve, FourPortFivePositionValve

if TYPE_CHECKING:
    from .ml600 import ML600


class ML600LeftValve(FourPortFivePositionValve):
    hw_device: ML600  # for typing's sake
    identifier: str

    def __init__(self, name: str, hw_device: ML600, identifier: str = "") -> None:
        super().__init__(name, hw_device)
        self.identifier = identifier
    # 0 degree syr-left,
    # 45 right-front
    # 90 nothing
    # 135 front-syr
    # 180
    # 225 left front
    # 270 syr-right
    # 315
    # 360

    def _change_connections(self, raw_position: str, reverse: bool = False) -> str:
        if not reverse:
            translated = int(raw_position) * 45
        else:
            translated = round(int(raw_position) / 45)
        return str(translated)

class ML600RightValve(ThreePortFourPositionValve):
    hw_device: ML600  # for typing's sake
    identifier: str

    def __init__(self, name: str, hw_device: ML600, identifier: str = "") -> None:
        super().__init__(name, hw_device)
        self.identifier = identifier

    def _change_connections(self, raw_position: str, reverse: bool = False) -> str:
        if not reverse:
            translated = (int(raw_position) + 2) * 90
            if translated >= 360:
                translated -= 360
        else:
            # round, the return is often off by 1°/the valve does not switch exactly
            # the slightly complicated logic here is because the degrees are differently defined in the abstract valve
            # and the physical ML600 valve, the offset in multiples of 90 degres is corrected here
            translated = round(int(raw_position) / 90)
            if translated < 2:
                translated += 2
            else:
                translated -= 2

        return str(translated)

