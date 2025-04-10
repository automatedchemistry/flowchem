"""ML600 component relative to valve switching."""
from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from flowchem.components.valves.valve import Valve
from flowchem.components.valves.distribution_valves import TwoPortDistributionValve
from flowchem.utils.exceptions import DeviceError

if TYPE_CHECKING:
    from .ml600 import ML600


# class ML600Valve(TwoPortDistributionValve):
#     hw_device: ML600  # for typing's sake
#
#     position_mapping = {
#         "input": "1",  # 9 is default inlet, i.e. 1
#         "output": "3",  # 10 is default outlet, i.e. 3
#     }
#
#     async def set_position(self, position: str) -> bool:
#         """Set pump to position."""
#         await super().set_position(position)  # Validation of the position exist
#         return await self.hw_device.set_valve_position(
#             target_position=ML600Valve.position_mapping[position],
#             wait_for_movement_end=True,
#         )
#
#     async def get_position(self) -> str:
#         """Get current pump position."""
#         pos = await self.hw_device.get_valve_position()
#         reverse_position_mapping = {
#             v: k for k, v in ML600Valve.position_mapping.items()
#         }
#         try:
#             return reverse_position_mapping[pos]
#         except KeyError:
#             logger.error(f"Unknown valve position returned {pos}")
#             return ""

class ML600LeftValve(Valve):
    hw_device: ML600  # for typing's sake
    identifier = "B"

    angle_mapping_name = {0: "syr-left", 45: "right-front",
                          135: "syr-front", 225: "left-front",
                          270: "syr-right"}

    def __init__(self, name: str, hw_device: ML600) -> None:
        # position_dict = {str(k + 1): [tuple(v.split("-"))] for k, v in enumerate(self.angle_mapping_name.values())}
        positions = {
            "1": [("pump", "1")],  # left
            "2": [("pump", "2")],  # front
            "3": [("pump", "3")],  # right
            "4": [("1", "2")],
            "5": [("3", "2")]
        }
        super().__init__(name, hw_device, positions, ports=["pump", "1", "2", "3"])

    def _calibrate_angle(self, angle: int) -> int:
        """Calibrate the angle to the nearest 90°."""
        # the request angle is often off by 1°; 45° is used to calibrate the angle
        return round(angle / 45) * 45 if angle is not self.angle_mapping_name.keys() else angle

    async def get_position(self) -> str:  # type: ignore
        """Get the current position of the valve."""
        degree = int(await self.hw_device.get_valve_angle(valve_code=self.identifier))
        calib_angle = self._calibrate_angle(degree)
        return self.angle_mapping_name[calib_angle]

    async def set_position(self, position: str) -> bool:
        """Set the valve to the specified position."""
        # assert position in self._positions
        reverse_angle_mapping = {
            v: k for k, v in self.angle_mapping_name.items()
        }
        await self.hw_device.set_valve_angle(
            target_angle=reverse_angle_mapping[position],
            valve_code=self.identifier,
            wait_for_movement_end=True,
        )
        c_position = await self.get_position()
        if c_position == position:
            return True

        logger.warning(f"ask to switch to {position}. but still at {c_position}. try 2nd time")
        return await self.set_position(position)


class ML600RightValve(Valve):
    hw_device: ML600  # for typing's sake
    identifier = "C"
    angle_mapping_name = {0: "syr-left-front",
                          90: "syr-right&left-front",
                          180: "syr-left&right-front",
                          270: "syr-right-front"}

    def __init__(self, name: str, hw_device: ML600) -> None:
        # fixme : v.split("&") -> ['syr-right', 'left-front']
        # position_dict = {str(k + 1): [tuple(v.split("-"))] for k, v in enumerate(self.angle_mapping_name.values())}
        positions = {
            "1": [("pump", "1&2")],  # syr-left-front
            "2": [("pump", "3"), ("1", "2")],  # syr-right&left-front
            "3": [("pump", "1"), ("3", "2")],  # syr-left&right-front
            "4": [("pump", "3&2")]  # syr-right-front
        }
        super().__init__(name, hw_device, positions, ports=["pump", "1", "2", "3"])

    def _calibrate_angle(self, angle: int) -> int:
        """Calibrate the angle to the nearest 90°."""
        # the request angle is often off by 1°; 45° is used to calibrate the angle
        return round(angle / 45) * 45 if angle is not self.angle_mapping_name.keys() else angle

    async def get_position(self) -> str:  # type: ignore
        """Get the current position of the valve."""
        degree = await self.hw_device.get_valve_angle(valve_code=self.identifier)
        calib_angle = self._calibrate_angle(degree)
        return self.angle_mapping_name[calib_angle]

    async def set_position(self, position: str) -> bool:
        """Set the valve to the specified position."""
        # assert position in self._positions
        reverse_angle_mapping = {
            v: k for k, v in self.angle_mapping_name.items()
        }
        trying = 1
        while trying < 5:
            trying += 1
            await self.hw_device.set_valve_angle(
                target_angle=reverse_angle_mapping[position],
                valve_code=self.identifier,
                wait_for_movement_end=True,
            )
            c_position = await self.get_position()
            if c_position == position:
                return True
            logger.warning(f"ask to switch to {position}. but still at {c_position}. try {trying} time")

        logger.error(f"fail {trying} time.")
        raise DeviceError(f"ask to switch to {position}. but still at {c_position}.")

