"""Simulated NI USB-TC01 thermocouple temperature sensor."""

from __future__ import annotations

from flowchem.devices.ni.ni_usbtc01 import NIUSBTC01


class SimulatedTC01Task:
    """In-memory replacement for an NI-DAQmx thermocouple task."""

    def __init__(self, temperature: float = 25.0) -> None:
        self.temperature = temperature
        self.closed = False

    def read(self) -> float:
        return self.temperature

    def close(self) -> None:
        self.closed = True


class NIUSBTC01Sim(NIUSBTC01):
    """Simulated NI USB-TC01 device."""

    sim_task: SimulatedTC01Task

    @classmethod
    def from_config(
        cls,
        module: str | None = None,
        thermocouple_type: str = "K",
        name: str = "",
    ) -> "NIUSBTC01Sim":
        sim_task = SimulatedTC01Task()
        instance = cls(
            module=module or "SimUSBTC01Dev1",
            task=sim_task,
            thermocouple_type=thermocouple_type.upper(),
            name=name or "sim-ni-tc01",
        )
        instance.sim_task = sim_task
        return instance
