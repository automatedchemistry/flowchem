"""Simulated TMCM-1111 fraction collector."""

from __future__ import annotations

from flowchem.devices.trinamic.tmcm1111 import (
    AxisParameter,
    RFSType,
    TMCLCommandNumber,
    TMCLReply,
    TMCLRequest,
    TMCM1111,
)


class SimulatedTMCM1111IO:
    """In-memory TMCL transport for the TMCM-1111 driver."""

    def __init__(self) -> None:
        self.requests: list[TMCLRequest] = []
        self.axis_parameters: dict[int, int] = {
            int(AxisParameter.TARGET_POSITION): 0,
            int(AxisParameter.ACTUAL_POSITION): 0,
            int(AxisParameter.POSITION_REACHED): 1,
            int(AxisParameter.HOME_SWITCH_STATE): 0,
            int(AxisParameter.RIGHT_LIMIT_SWITCH_STATE): 0,
            int(AxisParameter.LEFT_LIMIT_SWITCH_STATE): 0,
        }
        self.reference_search_active = False
        self.closed = False

    async def write_and_read_reply(self, request: TMCLRequest) -> TMCLReply:
        self.requests.append(request)
        value = self._dispatch(request)
        return TMCLReply(
            host_address=2,
            target_address=request.address,
            status=100,
            command=request.command,
            value=value,
        )

    def _dispatch(self, request: TMCLRequest) -> int:
        command = TMCLCommandNumber(request.command)
        if command == TMCLCommandNumber.MVP:
            self.axis_parameters[int(AxisParameter.TARGET_POSITION)] = request.value
            self.axis_parameters[int(AxisParameter.ACTUAL_POSITION)] = request.value
            self.axis_parameters[int(AxisParameter.POSITION_REACHED)] = 1
            return 0
        if command == TMCLCommandNumber.MST:
            self.axis_parameters[int(AxisParameter.POSITION_REACHED)] = 1
            return 0
        if command == TMCLCommandNumber.SAP:
            self.axis_parameters[request.command_type] = request.value
            return 0
        if command == TMCLCommandNumber.GAP:
            return self.axis_parameters.get(request.command_type, 0)
        if command == TMCLCommandNumber.RFS:
            rfs_type = RFSType(request.command_type)
            if rfs_type == RFSType.START:
                self.reference_search_active = False
                self.axis_parameters[int(AxisParameter.TARGET_POSITION)] = 0
                self.axis_parameters[int(AxisParameter.ACTUAL_POSITION)] = 0
                self.axis_parameters[int(AxisParameter.POSITION_REACHED)] = 1
                return 0
            if rfs_type == RFSType.STOP:
                self.reference_search_active = False
                return 0
            if rfs_type == RFSType.STATUS:
                return int(self.reference_search_active)
        return 0

    def close(self) -> None:
        self.closed = True


class TMCM1111Sim(TMCM1111):
    """Simulated TMCM-1111 using the real component and device logic."""

    sim_io: SimulatedTMCM1111IO

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
    ) -> "TMCM1111Sim":
        sim_io = SimulatedTMCM1111IO()
        configured_positions = {"waste": 0, "vial_1": 12000} if positions is None else positions
        instance = cls(
            tmcm_io=sim_io,
            positions=configured_positions,
            address=address,
            name=name or "sim-tmcm1111",
            home_position=home_position,
            home_on_initialize=home_on_initialize,
            reference_search_mode=reference_search_mode,
            reference_search_speed=reference_search_speed,
            reference_switch_speed=reference_switch_speed,
        )
        instance.sim_io = sim_io
        return instance
