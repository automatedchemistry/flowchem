from __future__ import annotations

import importlib

import pytest

from flowchem.devices.list_known_device_type import autodiscover_device_classes
from flowchem.devices.ni.ni9477 import NI9477, NI9477_CHANNEL_COUNT
from flowchem.components.technical.relay import Relay
from flowchem.utils.exceptions import InvalidConfigurationError


class FakeTask:
    def __init__(self) -> None:
        self.writes: list[list[bool]] = []
        self.closed = False

    def write(self, states: list[bool], auto_start: bool = True) -> int:
        self.writes.append(list(states))
        return len(states)

    def close(self) -> None:
        self.closed = True


@pytest.fixture(autouse=True)
def cleanup_relay_registry():
    yield
    Relay.INSTANCES.pop("test-ni/relay", None)


@pytest.fixture
async def ni9477() -> NI9477:
    device = NI9477(
        module="cDAQ1Mod1",
        task=FakeTask(),
        name="test-ni",
        reset_outputs_on_initialize=False,
    )
    await device.initialize()
    return device


def test_autodiscovery_works_without_nidaqmx_installed():
    assert "NI9477" in autodiscover_device_classes()


def test_from_config_without_nidaqmx_raises_helpful_error(monkeypatch):
    import flowchem.devices.ni.ni9477 as ni9477_module

    real_import_module = importlib.import_module

    def fake_import_module(name: str, *args, **kwargs):
        if name.startswith("nidaqmx"):
            raise ImportError
        return real_import_module(name, *args, **kwargs)

    monkeypatch.setattr(ni9477_module.importlib, "import_module", fake_import_module)

    with pytest.raises(InvalidConfigurationError, match="flowchem\\[ni\\]"):
        NI9477.from_config(module="cDAQ1Mod1")


async def test_initializes_relay_component(ni9477):
    assert len(ni9477.components) == 1
    assert ni9477.components[0].name == "relay"
    assert Relay.INSTANCES["test-ni/relay"] is ni9477.components[0]


async def test_power_on_and_off_updates_single_channel(ni9477):
    relay = ni9477.components[0]

    assert await relay.power_on(channel=1) is True
    assert ni9477.get_channel_state(1) is True
    assert ni9477._task.writes[-1][0] is True

    assert await relay.power_off(channel="1") is True
    assert ni9477.get_channel_state("1") is False
    assert ni9477._task.writes[-1][0] is False


async def test_channel_validation(ni9477):
    relay = ni9477.components[0]

    assert await relay.power_on(channel=0) is False
    assert await relay.power_on(channel=NI9477_CHANNEL_COUNT + 1) is False
    assert await relay.read_channel_set_point(channel="not-a-channel") is None


async def test_switch_multiple_channel_parses_state_string(ni9477):
    relay = ni9477.components[0]

    assert await relay.switch_multiple_channel("102") is True
    assert ni9477.get_channel_states()[:4] == [True, False, True, False]
    assert len(ni9477.get_channel_states()) == NI9477_CHANNEL_COUNT


async def test_switch_multiple_channel_rejects_invalid_values(ni9477):
    relay = ni9477.components[0]

    assert await relay.switch_multiple_channel("1x0") is False
    assert await relay.switch_multiple_channel("1" * (NI9477_CHANNEL_COUNT + 1)) is False
