"""Simulated Bio-Chem solenoid valve."""

from __future__ import annotations

from loguru import logger

from flowchem.devices.biochem.solenoid_valve import (
    BioChemSolenoidValve,
    BioChemSolenoid2WayValve,
)
from flowchem.components.technical.relay import Relay


class _SimulatedRelay(Relay):
    """
    A minimal in-memory Relay used by BioChemSolenoidValveSim.

    It does not connect to any hardware — power_on/off simply toggle state.
    """

    def __init__(self, name: str, hw_device):
        super().__init__(name, hw_device)
        self._sim_on: bool = False

    async def power_on(self, **kwargs) -> bool:
        self._sim_on = True
        logger.debug(f"[SIM] Relay '{self.name}' ON")
        return True

    async def power_off(self, **kwargs) -> bool:
        self._sim_on = False
        logger.debug(f"[SIM] Relay '{self.name}' OFF")
        return True

    async def is_on(self, **kwargs) -> bool:
        return self._sim_on


class BioChemSolenoidValveSim(BioChemSolenoidValve):
    """
    Simulated Bio-Chem solenoid valve.

    Instead of waiting for a real Relay.INSTANCES entry, this sim creates
    its own in-memory relay and registers it immediately.

    TOML usage
    ----------
        [device.my-solenoid]
        type = "BioChemSolenoidValve"   # replaced by flowchem-sim
        support_platform = "sim-mpibox/relay-A"
        normally_open = true
    """

    @classmethod
    def from_config(cls, **config) -> "BioChemSolenoidValveSim":
        name = config.pop("name", "sim-solenoid")
        support_platform = config.pop("support_platform", f"{name}/relay-A")
        normally_open = bool(config.pop("normally_open", True))
        channel = config.pop("channel", None)
        return cls(
            name=name,
            support_platform=support_platform,
            channel=channel,
            normally_open=normally_open,
        )

    async def initialize(self):
        """Register a synthetic in-memory relay and skip polling."""
        from flowchem.devices.flowchem_device import FlowchemDevice
        from flowchem.components.device_info import DeviceInfo

        # Create a throwaway hw_device just to satisfy Relay's constructor.
        _stub_hw = FlowchemDevice.__new__(FlowchemDevice)
        _stub_hw.name = self.support_platform.split("/")[0]
        _stub_hw.device_info = DeviceInfo()
        _stub_hw.components = []

        sim_relay = _SimulatedRelay(
            name=self.support_platform.split("/")[-1],
            hw_device=_stub_hw,
        )
        # Register so BioChemSolenoidValve.initialize() can find it.
        Relay.INSTANCES[self.support_platform] = sim_relay

        # Now run the real initialize() which binds self._io and adds the component.
        await super().initialize()
        logger.info(f"[SIM] BioChemSolenoidValve '{self.name}' initialized.")


class BioChemSolenoid2WayValveSim(BioChemSolenoid2WayValve):
    """Simulated 2-way variant — same approach as BioChemSolenoidValveSim."""

    @classmethod
    def from_config(cls, **config) -> "BioChemSolenoid2WayValveSim":
        name = config.pop("name", "sim-solenoid-2way")
        support_platform = config.pop("support_platform", f"{name}/relay-A")
        normally_open = bool(config.pop("normally_open", True))
        channel = config.pop("channel", None)
        return cls(
            name=name,
            support_platform=support_platform,
            channel=channel,
            normally_open=normally_open,
        )

    async def initialize(self):
        from flowchem.devices.flowchem_device import FlowchemDevice
        from flowchem.components.device_info import DeviceInfo

        _stub_hw = FlowchemDevice.__new__(FlowchemDevice)
        _stub_hw.name = self.support_platform.split("/")[0]
        _stub_hw.device_info = DeviceInfo()
        _stub_hw.components = []

        sim_relay = _SimulatedRelay(
            name=self.support_platform.split("/")[-1],
            hw_device=_stub_hw,
        )
        Relay.INSTANCES[self.support_platform] = sim_relay
        await super().initialize()
        logger.info(f"[SIM] BioChemSolenoid2WayValve '{self.name}' initialized.")
