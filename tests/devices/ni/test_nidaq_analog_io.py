from __future__ import annotations

import types

import pytest

from flowchem.devices.ni.nidaq_analog_io import NIDAQAnalogIO
from flowchem.utils.exceptions import InvalidConfigurationError


class FakeAITask:
    def __init__(self, values: list[float]) -> None:
        self.values = values
        self.closed = False

    def read(self) -> list[float]:
        return self.values.copy()

    def close(self) -> None:
        self.closed = True


class FakeAOTask:
    def __init__(self) -> None:
        self.writes: list[float | list[float]] = []
        self.closed = False

    def write(self, values: float | list[float], auto_start: bool = True) -> int:
        self.writes.append(list(values) if isinstance(values, list) else values)
        return len(values) if isinstance(values, list) else 1

    def close(self) -> None:
        self.closed = True


@pytest.fixture
async def analog_io() -> NIDAQAnalogIO:
    device = NIDAQAnalogIO(
        module="Dev2",
        adc_channel_names=["Dev2/ai0", "Dev2/ai1"],
        dac_channel_names=["Dev2/ao0", "Dev2/ao1"],
        adc_task=FakeAITask([1.25, 2.5]),
        dac_task=FakeAOTask(),
        name="test-analog",
        dac_range=(0.0, 10.0),
    )
    await device.initialize()
    return device


async def test_initializes_adc_and_dac_components(analog_io):
    assert [component.name for component in analog_io.components] == ["adc", "dac"]


async def test_adc_read_and_read_all(analog_io):
    adc = analog_io.components[0]

    assert await adc.read(channel="1") == 1.25
    assert await adc.read_all() == {"ADC1": 1.25, "ADC2": 2.5}


async def test_dac_set_and_cached_read(analog_io):
    dac = analog_io.components[1]

    assert await dac.set(channel="2", value="2.5 V") is True
    assert await dac.read(channel="2") == 2.5
    assert analog_io._dac_task.writes[-1] == [0.0, 2.5]


async def test_dac_rejects_invalid_channel_and_units(analog_io):
    dac = analog_io.components[1]

    assert await dac.set(channel="3", value="2 V") is False
    assert await dac.set(channel="1", value="not-a-voltage") is False


async def test_dac_rejects_configured_range_violation(analog_io):
    dac = analog_io.components[1]

    assert await dac.set(channel="1", value="12 V") is False


def test_requires_at_least_one_analog_channel():
    with pytest.raises(InvalidConfigurationError, match="at least one ADC or DAC"):
        NIDAQAnalogIO(module="Dev2")


def test_from_config_uses_explicit_channels_without_ranges(monkeypatch):
    import flowchem.devices.ni._common as ni_common

    created_tasks: list[FakeDAQTask] = []

    class FakeDAQTask:
        def __init__(self) -> None:
            self.ai_channels = types.SimpleNamespace(add_ai_voltage_chan=self.add_ai_voltage_chan)
            self.ao_channels = types.SimpleNamespace(add_ao_voltage_chan=self.add_ao_voltage_chan)
            self.ai_args: tuple | None = None
            self.ai_kwargs: dict | None = None
            self.ao_args: tuple | None = None
            self.ao_kwargs: dict | None = None
            created_tasks.append(self)

        def add_ai_voltage_chan(self, *args, **kwargs) -> None:
            self.ai_args = args
            self.ai_kwargs = kwargs

        def add_ao_voltage_chan(self, *args, **kwargs) -> None:
            self.ao_args = args
            self.ao_kwargs = kwargs

        def read(self) -> float:
            return 0.0

        def write(self, values, auto_start: bool = True) -> int:
            return 1

        def close(self) -> None:
            pass

    fake_constants = types.SimpleNamespace(
        TerminalConfiguration=types.SimpleNamespace(DEFAULT="DEFAULT")
    )
    fake_nidaqmx = types.SimpleNamespace(Task=FakeDAQTask)
    fake_system = types.SimpleNamespace(local=lambda: types.SimpleNamespace(devices=[]))

    def fake_import_nidaqmx():
        return fake_nidaqmx, fake_system, fake_constants

    monkeypatch.setattr(ni_common, "import_nidaqmx", fake_import_nidaqmx)
    monkeypatch.setattr(
        "flowchem.devices.ni.nidaq_analog_io.import_nidaqmx",
        fake_import_nidaqmx,
    )

    device = NIDAQAnalogIO.from_config(
        adc_channels=["Dev2/ai0"],
        dac_channels=["Dev2/ao0"],
    )

    assert device.module == "Dev2"
    assert created_tasks[0].ai_args == ("Dev2/ai0",)
    assert "min_val" not in created_tasks[0].ai_kwargs
    assert created_tasks[1].ao_args == ("Dev2/ao0",)
    assert "max_val" not in created_tasks[1].ao_kwargs
