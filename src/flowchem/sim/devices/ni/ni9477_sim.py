"""Simulated NI-9477 digital output module."""

from __future__ import annotations

from flowchem.devices.ni.ni9477 import NI9477


class SimulatedNI9477Task:
    """Small in-memory replacement for an NI-DAQmx digital output task."""

    def __init__(self) -> None:
        self.writes: list[list[bool]] = []
        self.closed = False

    def write(self, states: list[bool], auto_start: bool = True) -> int:
        self.writes.append(list(states))
        return len(states)

    def close(self) -> None:
        self.closed = True


class NI9477Sim(NI9477):
    """Simulated NI-9477 device using the real Flowchem relay component logic."""

    sim_task: SimulatedNI9477Task

    @classmethod
    def from_config(
        cls,
        module: str | None = None,
        name: str = "",
        reset_outputs_on_initialize: bool = True,
    ) -> "NI9477Sim":
        sim_task = SimulatedNI9477Task()
        instance = cls(
            module=module or "SimNI9477Mod1",
            task=sim_task,
            name=name or "sim-ni",
            reset_outputs_on_initialize=reset_outputs_on_initialize,
        )
        instance.sim_task = sim_task
        return instance
