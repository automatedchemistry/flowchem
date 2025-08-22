from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from flowchem import ureg
from flowchem.components.technical.pressure import PressureControl
from flowchem.components.sensors.body_position_seneor import BodySensor

if TYPE_CHECKING:
    from .vbfr_compression_controller import VBFReactor


class VbfrPressureControl(PressureControl):
    hw_device: VBFReactor

    def __init__(self, name: str, hw_device: VBFReactor) -> None:
        super().__init__(name, hw_device)
        self.add_api_route("/deadband", self.set_deadband, methods=["PUT"])
        self.add_api_route("/deadband", self.get_deadband, methods=["GET"])
        self.add_api_route("/calibration", self.calibration, methods=["PUT"])

    async def set_pressure(self, pressure: str) -> bool:
        """Set pressure differnence (in bar)"""
        try:
            digit_p = float(pressure)
            logger.warning("only digit was provided. Assume the unit is in bar")
            set_p = digit_p * ureg.bar
        except:
            set_p = ureg.parse_expression(pressure)

        await self.hw_device.set_pressure_difference(set_p.to("bar").magnitude)
        return True

    async def get_pressure(self) -> float:
        """Get current pressure difference (in mbar)"""
        return await self.hw_device.get_current_pressure_difference()

    async def get_target_pressure(self) -> float:
        return await self.hw_device.get_target_pressure_difference()

    async def set_deadband(self, up: int = None, down: int = None) -> bool:
        """Set up & down acceptable offset (in mbar) from required pressure difference."""
        await self.hw_device.set_deadband(up, down)
        return True

    async def get_deadband(self):
        """Get set pressure deadband (in mbar)"""
        return await self.hw_device.get_deadband()

    async def calibration(self) -> bool:
        """Set current position to zero"""
        return await self.hw_device.calibrate_pressure()

    async def power_on(self):
        return await self.hw_device.power_on()

    async def power_off(self):
        return await self.hw_device.power_off()


class VbfrBodySensor(BodySensor):
    hw_device: VBFReactor

    def __init__(self, name: str, hw_device: VBFReactor) -> None:
        super().__init__(name, hw_device)
        self.add_api_route("/position", self.get_position, methods=["GET"])
        self.add_api_route("/position_limits", self.get_position_limit, methods=["GET"])
        self.add_api_route("/position_limits", self.set_position_limit, methods=["PUT"])
        self.add_api_route("/calibration", self.calibration, methods=["PUT"])

    async def get_position(self) -> float:
        """Read body position ((in mm)."""
        return await self.hw_device.get_position()

    async def get_position_limit(self):
        """Get working range (in mm)"""
        return await self.hw_device.get_position_limit()

    async def set_position_limit(self, upper: float = None, lower: float = None) -> bool:
        """set working range (in mm)"""
        await self.hw_device.set_position_limit(upper, lower)
        return True

    async def calibration(self) -> bool:
        """Set current position to zero"""
        return await self.hw_device.calibrate_position()

    async def power_on(self):
        """start compress the reactor by set pressure"""
        return await self.hw_device.power_on()
    async def power_off(self):
        """stop compress the reactor by set pressure"""
        return await self.hw_device.power_off()