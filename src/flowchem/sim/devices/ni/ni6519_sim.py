"""Simulated NI-6519 digital I/O device."""

from __future__ import annotations

from flowchem.devices.ni.ni6519 import NI6519


class SimulatedNI6519InputTask:
    """Small in-memory replacement for an NI-DAQmx digital input task."""

    def __init__(self) -> None:
        self.values = [False] * 16
        self.closed = False

    def read(self) -> list[bool]:
        return self.values.copy()

    def close(self) -> None:
        self.closed = True


class SimulatedNI6519OutputTask:
    """Small in-memory replacement for an NI-DAQmx digital output task."""

    def __init__(self) -> None:
        self.writes: list[list[bool]] = []
        self.closed = False

    def write(self, states: list[bool], auto_start: bool = True) -> int:
        self.writes.append(list(states))
        return len(states)

    def close(self) -> None:
        self.closed = True


class NI6519Sim(NI6519):
    """Simulated NI-6519 device using the real Flowchem component logic."""

    sim_input_task: SimulatedNI6519InputTask
    sim_output_task: SimulatedNI6519OutputTask

    @classmethod
    def from_config(
        cls,
        module: str | None = None,
        name: str = "",
        reset_outputs_on_initialize: bool = True,
    ) -> "NI6519Sim":
        input_task = SimulatedNI6519InputTask()
        output_task = SimulatedNI6519OutputTask()
        instance = cls(
            module=module or "SimNI6519Dev1",
            input_task=input_task,
            output_task=output_task,
            name=name or "sim-ni6519",
            reset_outputs_on_initialize=reset_outputs_on_initialize,
        )
        instance.sim_input_task = input_task
        instance.sim_output_task = output_task
        return instance
