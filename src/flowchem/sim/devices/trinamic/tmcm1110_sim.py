"""Simulated TMCM-1110 fraction collector."""

from __future__ import annotations

from flowchem.devices.trinamic.tmcl import TMCLRequest
from flowchem.devices.trinamic.tmcm1110 import TMCM1110
from flowchem.sim.devices.trinamic.tmcm1111_sim import SimulatedTMCM1111IO


class SimulatedTMCM1110IO(SimulatedTMCM1111IO):
    """In-memory TMCL transport for the TMCM-1110 driver.

    The MST/MVP/SAP/GAP/RFS dispatch logic is TMCL-generic (not tied to
    TMC4361 vs TMC429 specifics), so this reuses the TMCM-1111 simulated
    transport and only overrides the get-firmware-version reply.
    """

    async def request_raw(self, request: TMCLRequest, read_length: int) -> bytes:
        """Return a plausible get-firmware-version string reply for a TMCM-1110."""
        self.requests.append(request)
        return b"1110V113"


class TMCM1110Sim(TMCM1110):
    """Simulated TMCM-1110 using the real component and device logic."""

    sim_io: SimulatedTMCM1110IO

    @classmethod
    def from_config(
        cls,
        port: str = "SIM",
        positions: dict[str, int] | None = None,
        address: int = 1,
        name: str = "",
        home_position: str = "",
        home_on_initialize: bool = False,
        reference_search_mode: int | None = None,
        reference_search_speed: int | None = None,
        reference_switch_speed: int | None = None,
        **serial_kwargs,
    ) -> "TMCM1110Sim":
        sim_io = SimulatedTMCM1110IO()
        configured_positions = (
            {"waste": 0, "vial_1": 12000} if positions is None else positions
        )
        instance = cls(
            tmcm_io=sim_io,
            positions=configured_positions,
            address=address,
            name=name or "sim-tmcm1110",
            home_position=home_position,
            home_on_initialize=home_on_initialize,
            reference_search_mode=reference_search_mode,
            reference_search_speed=reference_search_speed,
            reference_switch_speed=reference_switch_speed,
        )
        instance.sim_io = sim_io
        return instance
