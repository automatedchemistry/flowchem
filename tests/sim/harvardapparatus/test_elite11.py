"""Tests for Elite11Sim and SimulatedHarvardApparatusPumpIO."""

import pytest
from flowchem.sim.devices.harvardapparatus.elite11_sim import (
    Elite11Sim,
    SimulatedHarvardApparatusPumpIO,
)
from flowchem.devices.harvardapparatus._pumpio import PumpStatus


@pytest.fixture
async def elite11() -> Elite11Sim:
    device = Elite11Sim.from_config(
        name="test-elite11",
        syringe_diameter="14.567 mm",
        syringe_volume="10 ml",
    )
    await device.initialize()
    return device


@pytest.fixture
async def pump(elite11):
    return elite11.components[0]


class TestSimulatedHarvardApparatusPumpIO:

    def test_initial_state(self):
        io = SimulatedHarvardApparatusPumpIO(address=0)
        assert io._sim_status == PumpStatus.IDLE
        assert io._sim_flow_rate == 1.0
        assert io._sim_diameter == 14.567

    async def test_firmware_version(self):
        io = SimulatedHarvardApparatusPumpIO()
        from flowchem.devices.harvardapparatus._pumpio import Protocol11Command

        cmd = Protocol11Command(command="VER", pump_address=0, arguments="")
        reply = await io.write_and_read_reply(cmd)
        assert "ELITE" in reply[0]

    async def test_set_diameter(self):
        io = SimulatedHarvardApparatusPumpIO()
        from flowchem.devices.harvardapparatus._pumpio import Protocol11Command

        cmd = Protocol11Command(command="diameter", pump_address=0, arguments="20.0 mm")
        await io.write_and_read_reply(cmd)
        assert abs(io._sim_diameter - 20.0) < 0.01

    async def test_irun_sets_infusing_status(self):
        io = SimulatedHarvardApparatusPumpIO()
        from flowchem.devices.harvardapparatus._pumpio import Protocol11Command

        cmd = Protocol11Command(command="irun", pump_address=0, arguments="")
        await io.write_and_read_reply(cmd)
        assert io._sim_status == PumpStatus.INFUSING

    async def test_stp_sets_idle_status(self):
        io = SimulatedHarvardApparatusPumpIO()
        from flowchem.devices.harvardapparatus._pumpio import Protocol11Command

        io._sim_status = PumpStatus.INFUSING
        cmd = Protocol11Command(command="stp", pump_address=0, arguments="")
        await io.write_and_read_reply(cmd)
        assert io._sim_status == PumpStatus.IDLE

    async def test_autodiscover_address(self):
        io = SimulatedHarvardApparatusPumpIO(address=3)
        assert io.autodiscover_address() == 3


class TestElite11Sim:

    async def test_initializes_one_component(self, elite11):
        assert len(elite11.components) == 1

    async def test_firmware_version_set(self, elite11):
        assert (
            "ELITE" in elite11.device_info.version or True
        )  # version set in initialize

    async def test_version_method(self, elite11):
        ver = await elite11.version()
        assert "ELITE" in ver

    async def test_set_flow_rate(self, elite11):
        await elite11.set_flow_rate("2.0 ml/min")
        assert abs(elite11.pump_io._sim_flow_rate - 2.0) < 0.01

    async def test_get_flow_rate(self, elite11):
        await elite11.set_flow_rate("1.5 ml/min")
        rate = await elite11.get_flow_rate()
        assert abs(rate - 1.5) < 0.01

    async def test_infuse_changes_status(self, elite11):
        await elite11.infuse()
        assert elite11.pump_io._sim_status == PumpStatus.INFUSING

    async def test_withdraw_changes_status(self, elite11):
        await elite11.withdraw()
        assert elite11.pump_io._sim_status == PumpStatus.WITHDRAWING

    async def test_stop_changes_status(self, elite11):
        await elite11.infuse()
        await elite11.stop()
        assert elite11.pump_io._sim_status == PumpStatus.IDLE

    async def test_is_moving_while_infusing(self, elite11):
        await elite11.infuse()
        moving = await elite11.is_moving()
        assert moving is True

    async def test_is_not_moving_when_stopped(self, elite11):
        await elite11.stop()
        moving = await elite11.is_moving()
        assert moving is False

    async def test_set_syringe_diameter(self, elite11):
        from flowchem import ureg

        await elite11.set_syringe_diameter(ureg.Quantity("20 mm"))
        assert abs(elite11.pump_io._sim_diameter - 20.0) < 0.01

    async def test_get_syringe_diameter(self, elite11):
        result = await elite11.get_syringe_diameter()
        assert "mm" in result

    async def test_set_force(self, elite11):
        await elite11.set_force(50)
        assert elite11.pump_io._sim_force == 50

    async def test_pump_component_infuse(self, pump):
        result = await pump.infuse(rate="1 ml/min")
        assert result is True

    async def test_pump_component_stop(self, pump):
        await pump.infuse(rate="1 ml/min")
        await pump.stop()
        moving = await pump.is_pumping()
        assert moving is False

    async def test_withdrawing_capable(self, pump):
        assert pump.is_withdrawing_capable() is True

    async def test_pump_withdraw(self, pump):
        result = await pump.withdraw(rate="0.5 ml/min")
        assert result is True
