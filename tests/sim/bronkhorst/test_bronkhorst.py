"""Tests for MFCSim and EPCSim (Bronkhorst)."""

import pytest
from flowchem.sim.devices.bronkhorst.bronkhorst_sim import EPCSim, MFCSim


@pytest.fixture
async def mfc() -> MFCSim:
    device = MFCSim.from_config(name="test-mfc", max_flow=9.0)
    await device.initialize()
    return device


@pytest.fixture
async def epc() -> EPCSim:
    device = EPCSim.from_config(name="test-epc", max_pressure=10.0)
    await device.initialize()
    return device


@pytest.fixture
async def mfc_component(mfc):
    return mfc.components[0]


@pytest.fixture
async def epc_component(epc):
    return epc.components[0]


class TestMFCSim:

    async def test_initializes_one_component(self, mfc):
        assert len(mfc.components) == 1

    async def test_initial_setpoint_zero(self, mfc):
        assert mfc.el_flow.setpoint == 0

    async def test_set_flow_setpoint_updates_state(self, mfc):
        await mfc.set_flow_setpoint("4.5 ml/min")
        # 4.5 ml/min / 9 ml/min * 32000 = 16000
        assert abs(mfc.el_flow.setpoint - 16000) < 10

    async def test_measure_follows_setpoint(self, mfc):
        await mfc.set_flow_setpoint("9 ml/min")
        assert mfc.el_flow.measure == mfc.el_flow.setpoint

    async def test_get_flow_setpoint(self, mfc):
        await mfc.set_flow_setpoint("4.5 ml/min")
        flow = await mfc.get_flow_setpoint()
        assert abs(flow - 4.5) < 0.05

    async def test_set_flow_to_zero(self, mfc):
        await mfc.set_flow_setpoint("0 ml/min")
        assert mfc.el_flow.setpoint == 0

    async def test_get_flow_percentage(self, mfc):
        await mfc.set_flow_setpoint("4.5 ml/min")
        pct = await mfc.get_flow_percentage()
        assert abs(pct - 50.0) < 1.0

    async def test_component_set_flow(self, mfc_component):
        await mfc_component.set_flow_rate("2 ml/min")
        flow = await mfc_component.get_flow_rate()
        assert abs(flow - 2.0) < 0.05

    async def test_device_id(self, mfc):
        assert mfc.id == "SIM-BRONKHORST"


class TestEPCSim:

    async def test_initializes_one_component(self, epc):
        assert len(epc.components) == 1

    async def test_initial_setpoint_zero(self, epc):
        assert epc.el_press.setpoint == 0

    async def test_set_pressure_updates_state(self, epc):
        await epc.set_pressure("5 bar")
        # 5 bar / 10 bar * 32000 = 16000
        assert abs(epc.el_press.setpoint - 16000) < 10

    async def test_measure_follows_setpoint(self, epc):
        await epc.set_pressure("5 bar")
        assert epc.el_press.measure == epc.el_press.setpoint

    async def test_get_pressure(self, epc):
        await epc.set_pressure("5 bar")
        p = await epc.get_pressure()
        assert abs(p - 5.0) < 0.05

    async def test_set_pressure_to_zero(self, epc):
        await epc.set_pressure("0 bar")
        assert epc.el_press.setpoint == 0

    async def test_get_pressure_percentage(self, epc):
        await epc.set_pressure("5 bar")
        pct = await epc.get_pressure_percentage()
        assert abs(pct - 50.0) < 1.0

    async def test_component_set_pressure(self, epc_component):
        await epc_component.set_pressure("3 bar")
        p = await epc_component.get_pressure()
        assert abs(p - 3.0) < 0.05

    async def test_device_id(self, epc):
        assert epc.id == "SIM-BRONKHORST"
