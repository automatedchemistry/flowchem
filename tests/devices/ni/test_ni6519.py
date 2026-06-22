from __future__ import annotations

import importlib

import pytest

from flowchem.devices.list_known_device_type import autodiscover_device_classes
from flowchem.devices.ni.ni6519 import (
    NI6519,
    NI6519_INPUT_CHANNEL_COUNT,
    NI6519_OUTPUT_CHANNEL_COUNT,
)
from flowchem.components.technical.relay import Relay
from flowchem.utils.exceptions import InvalidConfigurationError


class FakeInputTask:
    def __init__(self) -> None:
        self.values = [False] * NI6519_INPUT_CHANNEL_COUNT
        self.closed = False

    def read(self) -> list[bool]:
        return self.values.copy()

    def close(self) -> None:
        self.closed = True


class FakeOutputTask:
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
    Relay.INSTANCES.pop("test-ni6519/relay", None)


@pytest.fixture
async def ni6519() -> NI6519:
    input_task = FakeInputTask()
    output_task = FakeOutputTask()
    device = NI6519(
        module="Dev1",
        input_task=input_task,
        output_task=output_task,
        name="test-ni6519",
        reset_outputs_on_initialize=False,
    )
    input_task.values[0] = True
    input_task.values[-1] = True
    await device.initialize()
    return device


def test_autodiscovery_works_without_nidaqmx_installed():
    assert "NI6519" in autodiscover_device_classes()


def test_from_config_without_nidaqmx_raises_helpful_error(monkeypatch):
    import flowchem.devices.ni._common as ni_common

    real_import_module = importlib.import_module

    def fake_import_module(name: str, *args, **kwargs):
        if name.startswith("nidaqmx"):
            raise ImportError
        return real_import_module(name, *args, **kwargs)

    monkeypatch.setattr(ni_common.importlib, "import_module", fake_import_module)

    with pytest.raises(InvalidConfigurationError, match="flowchem\\[ni\\]"):
        NI6519.from_config(module="Dev1")


async def test_initializes_relay_and_digital_input_components(ni6519):
    assert [component.name for component in ni6519.components] == [
        "relay",
        "digital-input",
    ]
    assert Relay.INSTANCES["test-ni6519/relay"] is ni6519.components[0]


async def test_fixed_factory_line_names():
    assert NI6519.default_input_line_names("Dev1") == [
        *(f"Dev1/port0/line{index}" for index in range(8)),
        *(f"Dev1/port1/line{index}" for index in range(8)),
    ]
    assert NI6519.default_output_line_names("Dev1") == [
        *(f"Dev1/port2/line{index}" for index in range(8)),
        *(f"Dev1/port3/line{index}" for index in range(8)),
    ]


async def test_relay_output_updates_single_channel(ni6519):
    relay = ni6519.components[0]

    assert await relay.power_on(channel=9) is True
    assert ni6519.get_output_channel_state(9) is True
    assert ni6519._output_task.writes[-1][8] is True

    assert await relay.power_off(channel="9") is True
    assert ni6519.get_output_channel_state("9") is False
    assert ni6519._output_task.writes[-1][8] is False


async def test_digital_input_reads_channels(ni6519):
    digital_input = ni6519.components[1]

    assert await digital_input.read(channel=1) == 1
    assert await digital_input.read(channel=16) == 1
    states = await digital_input.read_all()
    assert len(states) == NI6519_INPUT_CHANNEL_COUNT
    assert states[0] == 1
    assert states[-1] == 1


async def test_channel_validation(ni6519):
    relay = ni6519.components[0]
    digital_input = ni6519.components[1]

    assert await relay.power_on(channel=0) is False
    assert await relay.power_on(channel=NI6519_OUTPUT_CHANNEL_COUNT + 1) is False
    assert await digital_input.read(channel="bad") is None


async def test_switch_multiple_channel_parses_state_string(ni6519):
    relay = ni6519.components[0]

    assert await relay.switch_multiple_channel("102") is True
    assert ni6519.get_output_channel_states()[:4] == [True, False, True, False]
    assert len(ni6519.get_output_channel_states()) == NI6519_OUTPUT_CHANNEL_COUNT
