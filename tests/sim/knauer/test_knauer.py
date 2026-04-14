"""Tests for AzuraCompactSim and KnauerValveSim."""

import pytest
from flowchem.sim.devices.knauer.azura_compact_sim import AzuraCompactSim
from flowchem.sim.devices.knauer.knauer_valve_sim import KnauerValveSim

# ---------------------------------------------------------------------------
# AzuraCompact
# ---------------------------------------------------------------------------


@pytest.fixture
async def azura() -> AzuraCompactSim:
    device = AzuraCompactSim.from_config(name="test-azura")
    await device.initialize()
    return device


@pytest.fixture
async def azura_pump(azura):
    return azura.components[0]  # AzuraCompactPump


@pytest.fixture
async def azura_pressure(azura):
    return azura.components[1]  # AzuraCompactSensor


class TestAzuraCompactSim:

    async def test_initializes_two_components(self, azura):
        assert len(azura.components) == 2

    async def test_default_head_type(self, azura):
        head = await azura.get_headtype()
        from flowchem.devices.knauer.azura_compact import AzuraPumpHeads

        assert head == AzuraPumpHeads.FLOWRATE_TEN_ML

    async def test_set_and_get_flow_rate(self, azura):
        from flowchem import ureg

        await azura.set_flow_rate(ureg.Quantity("0.5 ml/min"))
        rate = await azura.get_flow_rate()
        assert abs(rate - 0.5) < 0.01

    async def test_infuse_starts_pump(self, azura):
        result = await azura.infuse()
        assert result is True
        assert azura.is_running() is True

    async def test_stop_stops_pump(self, azura):
        await azura.infuse()
        await azura.stop()
        assert azura.is_running() is False

    async def test_pump_infuse_via_component(self, azura_pump):
        result = await azura_pump.infuse(rate="0.2 ml/min")
        assert result is True

    async def test_pump_stop_via_component(self, azura_pump):
        await azura_pump.infuse(rate="0.2 ml/min")
        await azura_pump.stop()
        assert await azura_pump.is_pumping() is False

    async def test_read_pressure(self, azura):
        pressure = await azura.read_pressure()
        assert pressure.magnitude > 0

    async def test_read_errors_returns_list(self, azura):
        errors = await azura.read_errors()
        assert isinstance(errors, list)

    async def test_set_maximum_pressure(self, azura):
        await azura.set_maximum_pressure("30 bar")  # no error expected

    async def test_remote_control(self, azura):
        await azura.remote_control(True)  # no error expected

    async def test_sim_state_flow_updates(self, azura):
        from flowchem import ureg

        await azura.set_flow_rate(ureg.Quantity("2 ml/min"))
        assert azura._sim_flow == 2000  # µL/min


# ---------------------------------------------------------------------------
# KnauerValve
# ---------------------------------------------------------------------------


@pytest.fixture
async def knauer_valve_6() -> KnauerValveSim:
    device = KnauerValveSim.from_config(name="test-valve", valve_type="6")
    await device.initialize()
    return device


@pytest.fixture
async def knauer_valve_injection() -> KnauerValveSim:
    device = KnauerValveSim.from_config(name="test-valve-inj", valve_type="LI")
    await device.initialize()
    return device


@pytest.fixture
async def valve_component(knauer_valve_6):
    return knauer_valve_6.components[0]


class TestKnauerValveSim:

    async def test_initializes_one_component(self, knauer_valve_6):
        assert len(knauer_valve_6.components) == 1

    async def test_injection_valve_type(self, knauer_valve_injection):
        from flowchem.devices.knauer.knauer_valve import KnauerValveHeads

        vtype = knauer_valve_injection.device_info.additional_info["valve-type"]
        assert vtype == KnauerValveHeads.SIX_PORT_TWO_POSITION

    async def test_six_port_valve_type(self, knauer_valve_6):
        from flowchem.devices.knauer.knauer_valve import KnauerValveHeads

        vtype = knauer_valve_6.device_info.additional_info["valve-type"]
        assert vtype == KnauerValveHeads.SIX_PORT_SIX_POSITION

    async def test_get_raw_position_initial(self, knauer_valve_6):
        pos = await knauer_valve_6.get_raw_position()
        assert pos == "1"

    async def test_set_raw_position(self, knauer_valve_6):
        result = await knauer_valve_6.set_raw_position("3")
        assert result is True
        assert knauer_valve_6._sim_position == "3"

    async def test_get_after_set_position(self, knauer_valve_6):
        await knauer_valve_6.set_raw_position("4")
        pos = await knauer_valve_6.get_raw_position()
        assert pos == "4"

    async def test_valve_component_connections(self, valve_component):
        from flowchem.components.valves.valve import ValveInfo

        info = valve_component.connections()
        assert isinstance(info, ValveInfo)
        assert len(info.positions) > 0

    async def test_valve_component_get_position(self, valve_component):
        result = await valve_component.get_position()
        assert result is not None
