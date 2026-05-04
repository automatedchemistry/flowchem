"""Tests for SwitchBoxMPIKGSim and PeltierCoolerSim."""

import pytest
from flowchem.sim.devices.custom.switchbox_sim import (
    SwitchBoxMPIKGSim,
    SimulatedSwitchBoxIO,
)
from flowchem.sim.devices.custom.peltier_sim import PeltierCoolerSim, SimulatedPeltierIO
from flowchem import ureg

# ---------------------------------------------------------------------------
# SwitchBox
# ---------------------------------------------------------------------------

"""
@pytest.fixture
async def switchbox() -> SwitchBoxMPIKGSim:
    device = SwitchBoxMPIKGSim.from_config(port="SIM", name="test-switchbox")
    await device.initialize()
    return device


@pytest.fixture
async def relay_a(switchbox):
    # relay-A is the first relay component
    return next(c for c in switchbox.components if c.name == "relay-A")


class TestSimulatedSwitchBoxIO:

    def test_initial_ports_are_zero(self):
        io = SimulatedSwitchBoxIO()
        for port in ("a", "b", "c", "d"):
            assert io._sim_ports[port] == 0

    def test_set_port_a(self):
        io = SimulatedSwitchBoxIO()
        reply = io._dispatch("set a:255")
        assert reply == "OK"
        assert io._sim_ports["a"] == 255

    def test_get_port_a(self):
        io = SimulatedSwitchBoxIO()
        io._sim_ports["a"] = 42
        reply = io._dispatch("get a")
        assert "42" in reply

    def test_get_all_ports(self):
        io = SimulatedSwitchBoxIO()
        io._sim_ports["a"] = 1
        io._sim_ports["b"] = 2
        reply = io._dispatch("get abcd")
        assert "a:1" in reply
        assert "b:2" in reply

    def test_set_dac_channel(self):
        io = SimulatedSwitchBoxIO()
        io._dispatch("set dac1:2048")
        assert io._sim_dac[1] == 2048

    def test_get_dac_channel(self):
        io = SimulatedSwitchBoxIO()
        io._sim_dac[1] = 2048
        reply = io._dispatch("get dac1")
        assert "dac1" in reply

    def test_get_version(self):
        io = SimulatedSwitchBoxIO()
        reply = io._dispatch("get ver")
        assert "SIM" in reply


class TestSwitchBoxMPIKGSim:

    async def test_initializes_six_components(self, switchbox):
        assert len(switchbox.components) == 6

    async def test_version_populated(self, switchbox):
        assert "SIM" in switchbox.device_info.version

    async def test_set_relay_port(self, switchbox):
        result = await switchbox.set_relay_port(
            values=[2, 0, 0, 0, 0, 0, 0, 0], port="a"
        )
        assert result is True

    async def test_get_relay_channels(self, switchbox):
        channels = await switchbox.get_relay_channels()
        assert set(channels.keys()) == {"a", "b", "c", "d"}

    async def test_set_relay_single_channel(self, switchbox):
        result = await switchbox.set_relay_single_channel(
            channel=1, value=2, port_identify="a"
        )
        assert result is True

    async def test_get_dac(self, switchbox):
        val = await switchbox.get_dac(channel=1)
        assert val is not None

    async def test_set_dac(self, switchbox):
        result = await switchbox.set_dac(ureg.Quantity("2.5 V"), channel=1)
        assert result is True

    async def test_relay_component_power_on(self, relay_a):
        await relay_a.power_on()

    async def test_relay_component_power_off(self, relay_a):
        await relay_a.power_off()

    async def test_relay_component_is_on(self, relay_a):
        result = await relay_a.is_on()
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# PeltierCooler
# ---------------------------------------------------------------------------


@pytest.fixture
async def peltier() -> PeltierCoolerSim:
    device = PeltierCoolerSim.from_config(port="SIM", address=0, name="test-peltier")
    await device.initialize()
    return device


@pytest.fixture
async def temp_ctrl(peltier):
    return peltier.components[0]


class TestSimulatedPeltierIO:

    async def test_get_temperature_initial(self):
        io = SimulatedPeltierIO()
        from flowchem.devices.custom.peltier_cooler import PeltierCommands

        cmd = PeltierCommands.GET_TEMPERATURE.to_peltier(address=0)
        reply = await io.write_and_read_reply(cmd)
        assert float(reply) == 25.0

    async def test_set_temperature_updates_state(self):
        io = SimulatedPeltierIO()
        from flowchem.devices.custom.peltier_cooler import PeltierCommands

        cmd = PeltierCommands.SET_TEMPERATURE.to_peltier(
            address=0, argument=1000
        )  # 10.00 °C
        await io.write_and_read_reply(cmd)
        assert abs(io._sim_temp_cur - 10.0) < 0.01

    async def test_switch_on_sets_enabled(self):
        io = SimulatedPeltierIO()
        from flowchem.devices.custom.peltier_cooler import PeltierCommands

        cmd = PeltierCommands.SWITCH_ON.to_peltier(address=0)
        reply = await io.write_and_read_reply(cmd)
        assert reply == "1"
        assert io._sim_enabled is True

    async def test_switch_off_clears_enabled(self):
        io = SimulatedPeltierIO()
        from flowchem.devices.custom.peltier_cooler import PeltierCommands

        io._sim_enabled = True
        cmd = PeltierCommands.SWITCH_OFF.to_peltier(address=0)
        reply = await io.write_and_read_reply(cmd)
        assert reply == "0"
        assert io._sim_enabled is False

    async def test_cooling_current_limit(self):
        io = SimulatedPeltierIO()
        from flowchem.devices.custom.peltier_cooler import PeltierCommands

        cmd = PeltierCommands.COOLING_CURRENT_LIMIT.to_peltier(
            address=0, argument=200
        )  # 2.0 A
        reply = await io.write_and_read_reply(cmd)
        assert abs(float(reply) - 2.0) < 0.01
        assert abs(io._sim_cool_limit - 2.0) < 0.01


class TestPeltierCoolerSim:

    async def test_initializes_one_component(self, peltier):
        assert len(peltier.components) == 1

    async def test_get_temperature_initial(self, peltier):
        temp = await peltier.get_temperature()
        assert abs(temp - 25.0) < 0.1

    async def test_set_temperature(self, peltier):
        await peltier.set_temperature(ureg.Quantity("-10 °C"))
        temp = await peltier.get_temperature()
        assert abs(temp - (-10.0)) < 0.1

    async def test_start_and_stop_control(self, peltier):
        await peltier.start_control()
        assert peltier.peltier_io._sim_enabled is True
        await peltier.stop_control()
        assert peltier.peltier_io._sim_enabled is False

    async def test_get_sink_temperature(self, peltier):
        temp = await peltier.get_sink_temperature()
        assert isinstance(temp, float)

    async def test_get_power(self, peltier):
        power = await peltier.get_power()
        assert isinstance(power, float)

    async def test_component_set_temperature(self, temp_ctrl):
        await temp_ctrl.set_temperature("5 degC")
        temp = await temp_ctrl.get_temperature()
        assert abs(temp - 5.0) < 0.1

    async def test_component_power_on_off(self, temp_ctrl):
        await temp_ctrl.power_on()
        await temp_ctrl.power_off()

    async def test_component_is_target_reached(self, temp_ctrl):
        await temp_ctrl.set_temperature("25 degC")
        reached = await temp_ctrl.is_target_reached()
        assert isinstance(reached, bool)
"""