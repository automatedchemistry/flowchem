"""Tests for BioChemSolenoidValveSim."""

import pytest
from flowchem.sim.devices.biochem.solenoid_sim import (
    BioChemSolenoidValveSim,
    BioChemSolenoid2WayValveSim,
    _SimulatedRelay,
)


@pytest.fixture
async def solenoid_no() -> BioChemSolenoidValveSim:
    """Normally open solenoid valve."""
    device = BioChemSolenoidValveSim.from_config(
        name="test-solenoid-no",
        support_platform="test-box/relay-A",
        normally_open=True,
    )
    await device.initialize()
    return device


@pytest.fixture
async def solenoid_nc() -> BioChemSolenoidValveSim:
    """Normally closed solenoid valve."""
    device = BioChemSolenoidValveSim.from_config(
        name="test-solenoid-nc",
        support_platform="test-box-nc/relay-B",
        normally_open=False,
    )
    await device.initialize()
    return device


@pytest.fixture
async def solenoid_2way() -> BioChemSolenoid2WayValveSim:
    device = BioChemSolenoid2WayValveSim.from_config(
        name="test-solenoid-2way",
        support_platform="test-box-2w/relay-C",
        normally_open=True,
    )
    await device.initialize()
    return device


@pytest.fixture
def valve_component_no(solenoid_no):
    return solenoid_no.components[0]


@pytest.fixture
def valve_component_nc(solenoid_nc):
    return solenoid_nc.components[0]


class TestSimulatedRelay:

    async def test_initial_state_off(self):
        from flowchem.devices.flowchem_device import FlowchemDevice
        from flowchem.components.device_info import DeviceInfo

        stub = FlowchemDevice.__new__(FlowchemDevice)
        stub.name = "stub"
        stub.device_info = DeviceInfo()
        stub.components = []
        relay = _SimulatedRelay("test-relay", stub)
        assert await relay.is_on() is False

    async def test_power_on(self):
        from flowchem.devices.flowchem_device import FlowchemDevice
        from flowchem.components.device_info import DeviceInfo

        stub = FlowchemDevice.__new__(FlowchemDevice)
        stub.name = "stub"
        stub.device_info = DeviceInfo()
        stub.components = []
        relay = _SimulatedRelay("test-relay", stub)
        result = await relay.power_on()
        assert result is True
        assert await relay.is_on() is True

    async def test_power_off(self):
        from flowchem.devices.flowchem_device import FlowchemDevice
        from flowchem.components.device_info import DeviceInfo

        stub = FlowchemDevice.__new__(FlowchemDevice)
        stub.name = "stub"
        stub.device_info = DeviceInfo()
        stub.components = []
        relay = _SimulatedRelay("test-relay", stub)
        await relay.power_on()
        result = await relay.power_off()
        assert result is True
        assert await relay.is_on() is False


class TestBioChemSolenoidValveSim:

    async def test_initializes_one_component(self, solenoid_no):
        assert len(solenoid_no.components) == 1

    async def test_relay_registered(self, solenoid_no):
        from flowchem.components.technical.relay import Relay

        assert solenoid_no.support_platform in Relay.INSTANCES

    # Normally open: open = relay OFF, close = relay ON
    async def test_normally_open_is_open_initially(self, solenoid_no):
        assert await solenoid_no.is_open() is True

    async def test_normally_open_close(self, solenoid_no):
        await solenoid_no.close()
        assert await solenoid_no.is_open() is False

    async def test_normally_open_reopen(self, solenoid_no):
        await solenoid_no.close()
        await solenoid_no.open()
        assert await solenoid_no.is_open() is True

    # Normally closed: open = relay ON, close = relay OFF
    async def test_normally_closed_is_closed_initially(self, solenoid_nc):
        assert await solenoid_nc.is_open() is False

    async def test_normally_closed_open(self, solenoid_nc):
        await solenoid_nc.open()
        assert await solenoid_nc.is_open() is True

    async def test_normally_closed_reclose(self, solenoid_nc):
        await solenoid_nc.open()
        await solenoid_nc.close()
        assert await solenoid_nc.is_open() is False

    # Component API (SolenoidValve routes)
    async def test_component_open(self, valve_component_no, solenoid_no):
        await valve_component_no.open()
        assert await solenoid_no.is_open() is True

    async def test_component_close(self, valve_component_no, solenoid_no):
        await valve_component_no.close()
        assert await solenoid_no.is_open() is False

    async def test_component_status(self, valve_component_no):
        status = await valve_component_no.get_status()
        assert isinstance(status, bool)


class TestBioChemSolenoid2WayValveSim:

    async def test_initializes_one_component(self, solenoid_2way):
        assert len(solenoid_2way.components) == 1

    async def test_open_and_close(self, solenoid_2way):
        await solenoid_2way.open()
        assert await solenoid_2way.is_open() is True
        await solenoid_2way.close()
        assert await solenoid_2way.is_open() is False
