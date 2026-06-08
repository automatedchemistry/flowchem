"""Tests for ViciValveSim and SimulatedViciValcoValveIO."""

import pytest
from flowchem.sim.devices.vicivalco.vici_sim import (
    ViciValveSim,
    SimulatedViciValcoValveIO,
)


@pytest.fixture
async def vici() -> ViciValveSim:
    device = ViciValveSim.from_config(address=0, name="test-vici")
    await device.initialize()
    return device


@pytest.fixture
async def valve_component(vici):
    return vici.components[0]


class TestSimulatedViciValcoValveIO:

    async def test_initial_position_is_A(self):
        io = SimulatedViciValcoValveIO()
        assert io._sim_position == "A"

    async def test_learn_positions_returns_empty(self):
        from flowchem.devices.vicivalco.vici_valve import ViciCommand

        io = SimulatedViciValcoValveIO()
        reply = await io.write_and_read_reply(
            ViciCommand(valve_id=0, command="LRN", reply_lines=0)
        )
        assert reply == ""

    async def test_home_resets_to_A(self):
        from flowchem.devices.vicivalco.vici_valve import ViciCommand

        io = SimulatedViciValcoValveIO()
        io._sim_position = "B"
        await io.write_and_read_reply(
            ViciCommand(valve_id=0, command="HM", reply_lines=0)
        )
        assert io._sim_position == "A"

    async def test_cp_returns_position(self):
        from flowchem.devices.vicivalco.vici_valve import ViciCommand

        io = SimulatedViciValcoValveIO()
        io._sim_position = "B"
        reply = await io.write_and_read_reply(
            ViciCommand(valve_id=0, command="CP", reply_lines=0)
        )
        assert "B" in reply

    async def test_version_returned(self):
        from flowchem.devices.vicivalco.vici_valve import ViciCommand

        io = SimulatedViciValcoValveIO()
        reply = await io.write_and_read_reply(
            ViciCommand(valve_id=0, command="VR", reply_lines=0)
        )
        assert "Firmware" in reply or len(reply) > 0

    async def test_go_sets_position(self):
        from flowchem.devices.vicivalco.vici_valve import ViciCommand

        io = SimulatedViciValcoValveIO()
        await io.write_and_read_reply(
            ViciCommand(valve_id=0, command="GO", value="2", reply_lines=0)
        )
        assert io._sim_position == "2"

    async def test_timed_toggle_changes_position(self):
        from flowchem.devices.vicivalco.vici_valve import ViciCommand

        io = SimulatedViciValcoValveIO()
        io._sim_position = "A"
        await io.write_and_read_reply(
            ViciCommand(valve_id=0, command="TT", reply_lines=0)
        )
        assert io._sim_position == "B"
        await io.write_and_read_reply(
            ViciCommand(valve_id=0, command="TT", reply_lines=0)
        )
        assert io._sim_position == "A"


class TestViciValveSim:

    async def test_initializes_one_component(self, vici):
        assert len(vici.components) == 1

    async def test_firmware_version_set(self, vici):
        assert len(vici.device_info.version) > 0

    async def test_get_raw_position_initial(self, vici):
        pos = await vici.get_raw_position()
        assert len(pos) > 0

    async def test_set_raw_position(self, vici):
        await vici.set_raw_position("B")
        assert vici.valve_io._sim_position == "B"

    async def test_get_position_after_set(self, vici):
        await vici.set_raw_position("2")
        pos = await vici.get_raw_position()
        assert "2" in pos

    async def test_timed_toggle(self, vici):
        initial = vici.valve_io._sim_position
        await vici.timed_toggle("500 ms")
        assert vici.valve_io._sim_position != initial

    async def test_valve_component_connections(self, valve_component):
        from flowchem.components.valves.valve import ValveInfo

        info = valve_component.connections()
        assert isinstance(info, ValveInfo)

    async def test_valve_component_get_position(self, valve_component):
        result = await valve_component.get_position()
        assert result is not None
