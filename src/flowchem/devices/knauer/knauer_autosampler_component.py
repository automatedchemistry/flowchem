# ruff: noqa: F403, F405
from __future__ import annotations
from flowchem import ureg
from typing import TYPE_CHECKING, Optional
from loguru import logger


if TYPE_CHECKING:
    from .knauer_autosampler import KnauerAutosampler

from flowchem.components.meta_components.gantry3D import gantry3D
from flowchem.components.pumps.syringe_pump import SyringePump
from flowchem.components.valves.distribution_valves import FourPortDistributionValve
from flowchem.components.valves.injection_valves import SixPortTwoPositionValve

try:
    from NDA_knauer_AS.knauer_AS import *

    HAS_AS_COMMANDS = True
except ImportError:
    HAS_AS_COMMANDS = False


class AutosamplerGantry3D(gantry3D):
    """
    Control a Knauer Autosampler component .

    Attributes:
        hw_device (KnauerAutosampler): The hardware device for the Knauer CNC component.
    """

    tray_config = {
        "x": {"mode": "discrete", "positions": [1, 2, 3, 4, 5, 6, 7, 8]},
        "y": {"mode": "discrete", "positions": ["a", "b", "c", "d", "e", "f"]},
        "z": {"mode": "discrete", "positions": ["UP", "DOWN"]}
    }

    hw_device: KnauerAutosampler  # for typing's sake

    def __init__(self, name: str, hw_device: KnauerAutosampler) -> None:
        """Initialize component."""
        super().__init__(name, hw_device, axes_config=self.tray_config)
        self.add_api_route("/reset_errors", self.reset_errors, methods=["PUT"])
        self.add_api_route("/needle_position", self.set_needle_position, methods=["PUT"])
        self.add_api_route("/set_xy_position", self.set_xy_position, methods=["PUT"])
        self.add_api_route("/connect_to_position", self.connect_to_position, methods=["PUT"])

    async def set_needle_position(self, position: str = "") -> bool:
        """
        Move the needle to one of the predefined positions.

        Argument:
            position (str):
                        WASH
                        WASTE
                        EXCHANGE
                        TRANSPORT
        """
        await self.set_z_position("UP")
        await self.hw_device._move_needle_horizontal(needle_position=position)
        logger.info(f"Needle moved succesfully to position: {position}")
        return True

    async def connect_to_position(self, row: int, column: str, tray: str = "") -> bool:
        """
        Move the 3D gantry to the specified (x, y) coordinate of a specific plate and connects to it.

        plate (str):
                    LEFT_PLATE
                    RIGHT_PLATE

        column: ["a", "b", "c", "d", "e", "f"].
        row: [1, 2, 3, 4, 5, 6, 7, 8]
        """
        await self.set_z_position("UP")
        await self.set_xy_position(tray=tray,row=row,column=column)
        await self.set_z_position("DOWN")
        logger.info(f"Needle connected successfully to row: {row}, column: {column} on tray: {tray}")
        return True

    async def set_xy_position(self, row: int, column: str, tray: str = "") -> bool:
        """
        Move the 3D gantry to the specified (x, y) coordinate of a specific plate.

        plate (str):
                    LEFT_PLATE
                    RIGHT_PLATE

        column: ["a", "b", "c", "d", "e", "f"].
        row: [1, 2, 3, 4, 5, 6, 7, 8]
        """

        await super().set_x_position(position=row)
        await super().set_y_position(position=column)
        column_num = ord(column.upper()) - 64 # change column to int

        if await self.is_needle_running():
            logger.warning("Needle already moving!")

        #traytype = self.hw_device.tray_type.upper()
        await self.hw_device._move_needle_vertical("UP")
        await self.hw_device._move_tray(tray, row)
        success = await self.hw_device._move_needle_horizontal("PLATE", plate=tray, well=column_num)
        if success:
            logger.info(f"Needle moved successfully to row: {row}, column: {column} on tray: {tray}")
            return True
        else:
            return False

    async def set_z_position(self, position: int | float | str) -> bool:
        """
        Move the 3D gantry along the Z axis.

        direction (str):
            DOWN
            UP
        """
        await super().set_z_position(position=position)
        if await self.is_needle_running():
            logger.warning("Needle already moving!")
        if not isinstance(position, str):
            raise TypeError
        success = await self.hw_device._move_needle_vertical(move_to=position)
        if success:
            logger.info(f"Needle moved successfully to {position} direction.")
            return True
        else:
            return False

    async def reset_errors(self) -> bool:
        """Resets AS error"""
        errors = await self.hw_device.get_errors()
        if errors:
            logger.info(f"Error: {errors} was present")
            await self.hw_device.reset_errors()
            logger.info("Errors reset")
            return True
        else:
            return False

    async def is_needle_running(self) -> bool:
        """"Checks if Auto-sampler is running"""
        if await self.hw_device.get_status() == "NEEDLE_RUNNING":
            return True
        else:
            return False


class AutosamplerPump(SyringePump):
    """
    Control a Knauer Auto-sampler component .

    Attributes:
        hw_device (KnauerAutosampler): The hardware device for the Knauer CNC component.
    """
    hw_device: KnauerAutosampler

    async def infuse(self, rate: Optional[str] = None, volume: Optional[str] = None) -> bool:
        """
        Dispense with built in syringe.
        Args:
            volume: volume to dispense in mL

        Returns: None
        """
        if volume is None:
            volume = "0 mL"
            logger.warning("the volume to infuse is not provided. set to 0 ml")
        parsed_volume = ureg.Quantity(volume)
        success = await self.hw_device.dispense(volume=parsed_volume.m_as("mL"))
        if success:
            logger.info(f"Syringe pump successfully infused {volume} ml")
            return True
        else:
            return False

    async def withdraw(self, rate: Optional[str] = None, volume: Optional[str] = None) -> bool:  # type: ignore
        """
        Aspirate with built-in syringe.
        Args:
            rate: Volume flow rate ml/min
            volume: volume to aspirate in mL

        Returns: None
        """
        if volume is None:
            volume = await self.hw_device.syringe_volume()
            logger.warning(f"the volume to withdraw is not provided. set to {self.hw_device.syringe_volume}")
        parsed_volume = ureg.Quantity(volume)
        success = await self.hw_device.aspirate(volume=parsed_volume.m_as("mL"))
        if success:
            logger.info(f"Syringe pump successfully withdrew {volume} ml")
            return True
        else:
            return False

    @staticmethod
    def is_withdrawing_capable() -> bool:  # type: ignore
        """Can the pump reverse its normal flow direction?"""
        return True

    async def is_pumping(self) -> bool:
        """"Checks if Syringe or syringe valve is running"""
        status = await self.hw_device.get_status()
        if status == "SYRINGE_OR_SYRINGE_VALVE_RUNNING":
            return True
        else:
            return False


class AutosamplerInjectionValve(SixPortTwoPositionValve):
    """
        Control a Knauer Autosampler 6-Port Distribution Valve.

        Attributes:
            hw_device (KnauerValve): The hardware device for the Knauer valve.
        """
    hw_device: KnauerAutosampler  # for typing's sake
    identifier = "injection_valve"

    def __init__(self, name: str, hw_device: KnauerAutosampler) -> None:
        super().__init__(name, hw_device)
        self.add_api_route("/monitor_position", self.get_monitor_position, methods=["GET"])
        self.add_api_route("/monitor_position", self.set_monitor_position, methods=["PUT"])

    def _change_connections(self, raw_position: str | int, reverse: bool = False):
        """
        Change connections based on the valve's raw position.

        Args:
            raw_position (str | int): The raw position of the valve.
            reverse (bool): Whether to reverse the mapping.

        Returns:
            str | int: The mapped position.
        """
        position_mapping = {0: "LOAD", 1: "INJECT"}
        if reverse:
            return str([key for key, value in position_mapping.items() if value == raw_position][0])
        else:
            if type(raw_position) is int:
                return position_mapping[raw_position]
            else:
                raise TypeError

    async def get_monitor_position(self) -> str:
        """
        Gets the current valve position.

        Returns:
            position (str):
                LOAD (position 0)
                INJECT (position 1)
        """
        position = await self.hw_device.injector_valve_position(port=None)
        if position:
            logger.info(f"Injection valve is in position: {position}")
        return position

    async def set_monitor_position(self, position: str):
        """
        Set the valve to a specified position.

        Args:
            position (str):
            LOAD (position 0)
            INJECT (position 1)
        """
        try:
            success = await self.hw_device.injector_valve_position(port=position)
            if success:
                logger.info(f"Injection valve moved successfully to position: {position}")
        except KeyError as e:
            raise Exception(f"Please give allowed positions {[pos.name for pos in InjectorValvePositions]}") from e  # type: ignore


class AutosamplerSyringeValve(FourPortDistributionValve):
    """
        Control a Knauer Autosampler 4-Port Distribution syringe Valve.

        Attributes:
            hw_device (KnauerAutosampler): The hardware device for the 4-Port Distribution syringe Valve.
        """

    hw_device: KnauerAutosampler  # for typing's sake
    identifier = "syringe_valve"

    def __init__(self, name: str, hw_device: KnauerAutosampler) -> None:
        super().__init__(name, hw_device)
        self.add_api_route("/monitor_position", self.get_monitor_position, methods=["GET"])
        self.add_api_route("/monitor_position", self.set_monitor_position, methods=["PUT"])

    def _change_connections(self, raw_position: str | int, reverse: bool = False):
        """
        Change connections based on the valve's raw position.

        Args:
            raw_position (int): The raw position of the valve.
            reverse (bool): Whether to reverse the mapping.

        Returns:
            int: The mapped position.
        """
        position_mapping = {0: "NEEDLE", 1: "WASH", 2: "WASH_PORT2", 3: "WASTE"}
        if reverse:
            return str([key for key, value in position_mapping.items() if value == raw_position][0])
        else:
            if type(raw_position) is int:
                return position_mapping[raw_position]
            else:
                raise TypeError

    async def get_monitor_position(self) -> str:
        """
        Gets the current valve position.

        Returns:
            position (str): The current position:
            NEEDLE (position 0).
            WASH (position 1).
            WASH_PORT2 (position 2).
            WASTE (position 3).
        """
        position = await self.hw_device.syringe_valve_position(port=None)
        if position:
            logger.info(f"Syringe valve is in position: {position}")
        return position

    async def set_monitor_position(self, position: str):
        """
        Set the valve to a specified position.

        Args:
            position (str): The desired position:
            NEEDLE (position 0).
            WASH (position 1).
            WASH_PORT2 (position 2).
            WASTE (position 3).
        """
        success = await self.hw_device.syringe_valve_position(port=position)
        if success:
            logger.info(f"Syringe valve moved successfully to position: {position}")
