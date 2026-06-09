"""Simulated NI-DAQmx analog I/O device."""

from __future__ import annotations

from collections.abc import Sequence

from flowchem.devices.ni.nidaq_analog_io import NIDAQAnalogIO


class SimulatedNIDAQAnalogInputTask:
    """In-memory replacement for an NI-DAQmx analog input task."""

    def __init__(self, values: Sequence[float]) -> None:
        self.values = list(values)
        self.closed = False

    def read(self) -> float | list[float]:
        if len(self.values) == 1:
            return self.values[0]
        return self.values.copy()

    def close(self) -> None:
        self.closed = True


class SimulatedNIDAQAnalogOutputTask:
    """In-memory replacement for an NI-DAQmx analog output task."""

    def __init__(self) -> None:
        self.writes: list[float | list[float]] = []
        self.closed = False

    def write(self, values: float | list[float], auto_start: bool = True) -> int:
        stored = list(values) if isinstance(values, list) else values
        self.writes.append(stored)
        return len(values) if isinstance(values, list) else 1

    def close(self) -> None:
        self.closed = True


class NIDAQAnalogIOSim(NIDAQAnalogIO):
    """Simulated generic NI analog I/O device."""

    sim_adc_task: SimulatedNIDAQAnalogInputTask | None
    sim_dac_task: SimulatedNIDAQAnalogOutputTask | None

    @classmethod
    def from_config(
        cls,
        module: str | None = None,
        adc_channels: Sequence[str] | None = None,
        dac_channels: Sequence[str] | None = None,
        adc_range: Sequence[str] | None = None,
        dac_range: Sequence[str] | None = None,
        terminal_config: str | None = "DEFAULT",
        name: str = "",
    ) -> "NIDAQAnalogIOSim":
        module_name = module or "SimNIDAQDev1"
        adc_channel_names = list(adc_channels or [f"{module_name}/ai0", f"{module_name}/ai1"])
        dac_channel_names = list(dac_channels or [f"{module_name}/ao0", f"{module_name}/ao1"])
        adc_task = SimulatedNIDAQAnalogInputTask([0.0] * len(adc_channel_names))
        dac_task = SimulatedNIDAQAnalogOutputTask()
        instance = cls(
            module=module_name,
            adc_channel_names=adc_channel_names,
            dac_channel_names=dac_channel_names,
            adc_task=adc_task,
            dac_task=dac_task,
            name=name or "sim-nidaq-analog",
        )
        instance.sim_adc_task = adc_task
        instance.sim_dac_task = dac_task
        return instance
