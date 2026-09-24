"""Tests for RunzeValveSim/SimulatedRunzeValveIO and RunzeSyringePumpSim/SimulatedRunzeSyringePumpIO."""

import pytest
from flowchem.sim.devices.runze.runze_sim import (
    RunzeSyringePumpSim,
    RunzeValveSim,
    SimulatedRunzeSyringePumpIO,
    SimulatedRunzeValveIO,
)
from flowchem.devices.runze.runze_valve import RunzeValveHeads, SV06Command


@pytest.fixture
async def runze_6() -> RunzeValveSim:
    device = RunzeValveSim.from_config(name="test-runze", num_ports=6)
    await device.initialize()
    return device


@pytest.fixture
async def runze_12() -> RunzeValveSim:
    device = RunzeValveSim.from_config(name="test-runze-12", num_ports=12)
    await device.initialize()
    return device


@pytest.fixture
async def valve_component(runze_6):
    return runze_6.components[0]


class TestSimulatedRunzeValveIO:

    async def test_initial_position_is_one(self):
        io = SimulatedRunzeValveIO(num_ports=6)
        status, params = await io.write_and_read_reply_async(
            __import__(
                "flowchem.devices.runze.runze_valve", fromlist=["SV06Command"]
            ).SV06Command(address=1, function_code="3e")
        )
        assert status == "00"
        assert int(params, 16) == 1

    async def test_set_valid_position(self):
        from flowchem.devices.runze.runze_valve import SV06Command

        io = SimulatedRunzeValveIO(num_ports=6)
        status, _ = await io.write_and_read_reply_async(
            SV06Command(address=1, function_code="44", parameter=4)
        )
        assert status == "00"
        assert io._sim_position == 4

    async def test_set_invalid_position_raises(self):
        from flowchem.devices.runze.runze_valve import SV06Command
        from flowchem.utils.exceptions import DeviceError

        io = SimulatedRunzeValveIO(num_ports=6)
        with pytest.raises(DeviceError):
            await io.write_and_read_reply_async(
                SV06Command(address=1, function_code="44", parameter=10)
            )

    async def test_set_invalid_position_no_raise(self):
        from flowchem.devices.runze.runze_valve import SV06Command

        io = SimulatedRunzeValveIO(num_ports=6)
        status, _ = await io.write_and_read_reply_async(
            SV06Command(address=1, function_code="44", parameter=10),
            raise_errors=False,
        )
        assert status == "02"


class TestRunzeValveSim:

    async def test_6port_valve_type(self, runze_6):
        assert (
            runze_6.device_info.additional_info["valve-type"]
            == RunzeValveHeads.SIX_PORT_SIX_POSITION
        )

    async def test_12port_valve_type(self, runze_12):
        assert (
            runze_12.device_info.additional_info["valve-type"]
            == RunzeValveHeads.TWELVE_PORT_TWELVE_POSITION
        )

    async def test_initializes_one_component(self, runze_6):
        assert len(runze_6.components) == 1

    async def test_get_raw_position_initial(self, runze_6):
        pos = await runze_6.get_raw_position()
        assert int(pos, 16) == 1

    async def test_set_raw_position(self, runze_6):
        result = await runze_6.set_raw_position("3")
        assert result is True
        assert runze_6.sim_io._sim_position == 3

    async def test_get_after_set(self, runze_6):
        await runze_6.set_raw_position("5")
        pos = await runze_6.get_raw_position()
        assert int(pos, 16) == 5

    async def test_valve_component_connections(self, valve_component):
        from flowchem.components.valves.valve import ValveInfo

        info = valve_component.connections()
        assert isinstance(info, ValveInfo)

    async def test_valve_component_get_position(self, valve_component):
        result = await valve_component.get_position()
        assert result is not None


@pytest.fixture
async def syringe_pump() -> RunzeSyringePumpSim:
    device = RunzeSyringePumpSim.from_config(
        name="test-runze-pump",
        syringe_volume="5 mL",
        total_steps=12000,
        num_ports=6,
    )
    await device.initialize()
    return device


class TestSimulatedRunzeSyringePumpIO:

    async def test_initial_plunger_position_is_zero(self):
        io = SimulatedRunzeSyringePumpIO(num_ports=6, total_steps=12000)
        status, params = await io.write_and_read_reply_async(
            SV06Command(address=1, function_code="66")
        )
        assert status == "00"
        assert int(params, 16) == 0

    async def test_aspirate_then_dispense_round_trip(self):
        io = SimulatedRunzeSyringePumpIO(num_ports=6, total_steps=12000)
        await io.write_and_read_reply_async(
            SV06Command(address=1, function_code="43", parameter=1000)
        )
        assert io._sim_plunger_position == 1000
        await io.write_and_read_reply_async(
            SV06Command(address=1, function_code="42", parameter=400)
        )
        assert io._sim_plunger_position == 600

    async def test_aspirate_clamped_to_total_steps(self):
        io = SimulatedRunzeSyringePumpIO(num_ports=6, total_steps=12000)
        await io.write_and_read_reply_async(
            SV06Command(address=1, function_code="43", parameter=20000)
        )
        assert io._sim_plunger_position == 12000

    async def test_home_resets_position(self):
        io = SimulatedRunzeSyringePumpIO(num_ports=6, total_steps=12000)
        await io.write_and_read_reply_async(
            SV06Command(address=1, function_code="43", parameter=1000)
        )
        status, _ = await io.write_and_read_reply_async(
            SV06Command(address=1, function_code="45")
        )
        assert status == "00"
        assert io._sim_plunger_position == 0

    async def test_status_is_always_idle(self):
        io = SimulatedRunzeSyringePumpIO(num_ports=6, total_steps=12000)
        status, _ = await io.write_and_read_reply_async(
            SV06Command(address=1, function_code="4a")
        )
        assert status == "00"

    async def test_set_valid_valve_position(self):
        io = SimulatedRunzeSyringePumpIO(num_ports=6, total_steps=12000)
        status, _ = await io.write_and_read_reply_async(
            SV06Command(address=1, function_code="44", parameter=4)
        )
        assert status == "00"
        assert io._sim_valve_position == 4

    async def test_set_invalid_valve_position_raises(self):
        from flowchem.utils.exceptions import DeviceError

        io = SimulatedRunzeSyringePumpIO(num_ports=6, total_steps=12000)
        with pytest.raises(DeviceError):
            await io.write_and_read_reply_async(
                SV06Command(address=1, function_code="44", parameter=10)
            )


class TestRunzeSyringePumpSim:

    async def test_initializes_pump_and_valve_components(self, syringe_pump):
        assert {c.name for c in syringe_pump.components} == {"pump", "valve"}

    async def test_valve_type_detected(self, syringe_pump):
        assert (
            syringe_pump.device_info.additional_info["valve-type"]
            == RunzeValveHeads.SIX_PORT_SIX_POSITION
        )

    async def test_aspirate_dispense_get_current_volume(self, syringe_pump):
        assert await syringe_pump.aspirate_steps(6000) is True
        volume = await syringe_pump.get_current_volume()
        assert volume.m_as("mL") == pytest.approx(2.5)

        assert await syringe_pump.dispense_steps(6000) is True
        volume = await syringe_pump.get_current_volume()
        assert volume.m_as("mL") == pytest.approx(0.0)

    async def test_home_resets_read_position(self, syringe_pump):
        await syringe_pump.aspirate_steps(3000)
        assert await syringe_pump.home() is True
        assert await syringe_pump.read_position() == 0

    async def test_set_and_get_raw_position_round_trip(self, syringe_pump):
        result = await syringe_pump.set_raw_position("3")
        assert result is True
        pos = await syringe_pump.get_raw_position()
        assert pos == "3"
