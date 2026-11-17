"""Tests for R2Sim."""

import json

import pytest
from flowchem.sim.devices.vapourtec.r2_sim import R2Sim


@pytest.fixture
async def r2() -> R2Sim:
    device = R2Sim.from_config(name="test-r2")
    await device.initialize()
    return device


def _component(device, name):
    return next(c for c in device.components if c.name == name)


@pytest.fixture
async def reactor(r2):
    return _component(r2, "reactor-1")


class TestR2Sim:

    async def test_is_idle_before_set_temperature(self, reactor):
        assert await reactor.is_idle() is True

    async def test_is_idle_after_set_temperature(self, reactor):
        await reactor.set_temperature("50 degC")
        assert await reactor.is_idle() is True

    async def test_reactor_reads_back_temperature_and_setpoint(self, reactor):
        await reactor.set_temperature("50 degC")
        assert await reactor.get_temperature() == 50.0
        assert await reactor.get_temperature_setpoint() == 50.0

    async def test_configured_max_temp_is_used(self):
        r2 = R2Sim.from_config(name="test-r2", max_temp=150)
        await r2.initialize()
        reactor = _component(r2, "reactor-1")

        await reactor.set_temperature("120 degC")

        assert await reactor.get_temperature() == 120.0

    @pytest.mark.parametrize("name", ["ReagentValve_A", "CollectionValve"])
    async def test_two_port_valve_monitor_position_round_trip(self, r2, name):
        valve = _component(r2, name)
        for position in ("Reagent", "Solvent"):
            await valve.set_monitor_position(position)
            assert await valve.get_monitor_position() == f"inlet is {position}"

    @pytest.mark.parametrize("name", ["InjectionValve_A", "InjectionValve_B"])
    async def test_injection_valve_monitor_position_round_trip(self, r2, name):
        valve = _component(r2, name)
        for position in ("inject", "load"):
            await valve.set_monitor_position(position)
            assert await valve.get_monitor_position() == f"position is {position}"

    @pytest.mark.parametrize("name", ["ReagentValve_B", "InjectionValve_A"])
    async def test_valve_position_round_trip(self, r2, name):
        valve = _component(r2, name)
        for connections in valve._positions.values():
            expected = [list(connection) for connection in connections]
            await valve.set_position(connect=json.dumps(expected))
            assert await valve.get_position() == expected

    async def test_valves_move_independently(self, r2):
        await _component(r2, "InjectionValve_A").set_monitor_position("inject")
        await _component(r2, "CollectionValve").set_monitor_position("Reagent")

        assert await _component(r2, "InjectionValve_B").get_monitor_position() == (
            "position is load"
        )
        assert await _component(r2, "ReagentValve_A").get_monitor_position() == (
            "inlet is Solvent"
        )

    async def test_intensity_reads_zero_before_it_is_set(self, r2):
        photo = _component(r2, "PhotoReactor")
        assert await photo.get_intensity() == 0

        await photo.set_intensity(80)
        assert await photo.get_intensity() == 80

    async def test_monitor_system_reports_run_state_and_valves(self, r2):
        sensor = _component(r2, "GSensor2")
        await _component(r2, "ReagentValve_A").set_monitor_position("Reagent")
        await _component(r2, "Power").power_on()

        state = await sensor.monitor_sys()

        assert state["RunState_code"] == "1"
        assert state["allValve"] == "00001"
