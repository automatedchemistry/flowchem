"""Flowchem component for a TMCM-1111 linear fraction collector."""

from __future__ import annotations

from typing import TYPE_CHECKING

from flowchem.components.flowchem_component import FlowchemComponent

if TYPE_CHECKING:
    from .tmcm1111 import TMCM1111


class TMCM1111FractionCollector(FlowchemComponent):
    """Named-position interface for a single-axis TMCM-1111 fraction collector."""

    hw_device: TMCM1111

    def __init__(self, name: str, hw_device: "TMCM1111") -> None:
        super().__init__(name=name, hw_device=hw_device)
        self.add_api_route("/position", self.get_position, methods=["GET"])
        self.add_api_route("/position", self.set_position, methods=["PUT"])
        self.add_api_route(
            "/available_positions",
            self.available_positions,
            methods=["GET"],
        )
        self.add_api_route("/home", self.home, methods=["PUT"])
        self.add_api_route("/stop", self.stop, methods=["PUT"])
        self.add_api_route("/limits", self.limits, methods=["GET"])
        self.add_api_route("/target-reached", self.target_reached, methods=["GET"])

    async def set_position(self, position: str) -> bool:
        """Move to a named fraction position or a raw microstep position."""
        return await self.hw_device.move_to_position(position)

    async def get_position(self) -> str | int:
        """Return the current named position when exactly known, otherwise raw microsteps."""
        return await self.hw_device.get_position()

    async def available_positions(self) -> dict[str, int]:
        """Return configured named positions in raw microsteps."""
        return self.hw_device.available_positions()

    async def home(self, wait: bool = True, timeout: float = 60) -> bool:
        """Run the configured TMCM reference search."""
        return await self.hw_device.home(wait=wait, timeout=timeout)

    async def stop(self) -> bool:
        """Stop motor motion."""
        return await self.hw_device.stop()

    async def limits(self) -> dict[str, bool]:
        """Return home, left, and right limit switch states."""
        return await self.hw_device.get_limits()

    async def target_reached(self) -> bool:
        """Return whether the target position has been reached."""
        return await self.hw_device.is_target_reached()
