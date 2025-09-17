"""ML600 component relative to valve switching."""
from __future__ import annotations

from typing import TYPE_CHECKING

from flowchem.components.valves.distribution_valves import ThreePortFourPositionValve, FourPortFivePositionValve

if TYPE_CHECKING:
    from .ml600 import ML600


class ML600LeftValve(FourPortFivePositionValve):
    """
    Represents the left valve of the ML600 pump with specific translation for raw positions.

    This valve has 8 possible positions each separated by 45 degrees, but only a few are functional.

    # 0 degree syr-left,
    # 45 right-front
    # 90 nothing
    # 135 front-syr
    # 180
    # 225 left front
    # 270 syr-right
    # 315
    # 360

    Attributes:
    -----------
    hw_device : ML600
        The hardware device instance associated with this valve.
    identifier : str
        The identifier for this valve, set to "B".

    Methods:
    --------
    _change_connections(raw_position: int, reverse: bool = False) -> int:
        Translate the raw position to the corresponding degree or reverse.
    """
    hw_device: ML600  # for typing's sake
    identifier = "B"


    def _change_connections(self, raw_position: int | str, reverse: bool = False) -> str:
        """
        Translate the raw position to the corresponding degree for the valve or reverse.

        Parameters:
        -----------
        raw_position : str
            The raw position value to be translated.
        reverse : bool, optional
            If True, performs the reverse translation (default is False).

        Returns:
        --------
        str
            The translated position in degrees.
        """
        if not reverse:
            translated = int(raw_position) * 45
        else:
            translated = round(int(raw_position) / 45)
        return str(translated)


class ML600RightValve(ThreePortFourPositionValve):
    """
    Represents the right valve of the ML600 pump with specific translation for raw positions.

    This valve has 4 possible positions each separated by 90 degrees.

    Attributes:
    -----------
    hw_device : ML600
        The hardware device instance associated with this valve.
    identifier : str
        The identifier for this valve, set to "C".

    Methods:
    --------
    _change_connections(raw_position: int, reverse: bool = False) -> int:
        Translate the raw position to the corresponding degree or reverse.
    """
    hw_device: ML600  # for typing's sake
    identifier = "C"

    def _change_connections(self, raw_position: int | str, reverse: bool = False) -> str:
        """
        Translate the raw position to the corresponding degree for the valve or reverse.

        Parameters:
        -----------
        raw_position : str
            The raw position value to be translated.
        reverse : bool, optional
            If True, performs the reverse translation (default is False).

        Returns:
        --------
        str
            The translated position in degrees.
        """
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
