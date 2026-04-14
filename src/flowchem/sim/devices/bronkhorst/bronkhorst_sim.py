"""Simulated Bronkhorst EL-FLOW MFC and EPC."""

from __future__ import annotations

from loguru import logger

from flowchem.devices.bronkhorst.el_flow import MFC, EPC


class _FakeProparInstrument:
    """Minimal fake of propar.instrument used by Bronkhorst devices."""

    def __init__(self):
        self.setpoint: int = 0
        self.measure: int = 0
        self.id: str = "SIM-BRONKHORST"


class MFCSim(MFC):
    """
    Simulated Bronkhorst EL-FLOW mass flow controller.

    State
    -----
    el_flow.setpoint  : int   setpoint in propar units (0-32000)
    el_flow.measure   : int   measured flow in propar units
    max_flow          : float max flow in ml/min
    """

    def __init__(self, port="SIM", name="", channel=1, address=0x80, max_flow=9.0):
        from flowchem.devices.flowchem_device import FlowchemDevice

        FlowchemDevice.__init__(self, name)
        self.port = port
        self.channel = channel
        self.address = address
        self.max_flow = max_flow
        self.device_info.model = "EL-FLOW"
        self.device_info.authors = []
        # Inject fake propar instrument
        self.el_flow = _FakeProparInstrument()
        self.id = self.el_flow.id
        logger.debug(f"[SIM] MFC '{name}' initialized (max_flow={max_flow} ml/min)")

    @classmethod
    def from_config(cls, **config) -> "MFCSim":
        config.pop("port", None)
        return cls(
            name=config.pop("name", "sim-mfc"),
            max_flow=float(config.pop("max_flow", 9.0)),
            channel=int(config.pop("channel", 1)),
            address=int(config.pop("address", 0x80)),
        )

    # Override set/get to keep measure in sync with setpoint
    async def set_flow_setpoint(self, flowrate: str):
        await super().set_flow_setpoint(flowrate)
        # Simulate that the measured flow matches the setpoint instantly
        self.el_flow.measure = self.el_flow.setpoint


class EPCSim(EPC):
    """
    Simulated Bronkhorst EL-PRESS electronic pressure controller.

    State
    -----
    el_press.setpoint  : int   setpoint in propar units (0-32000)
    el_press.measure   : int   measured pressure in propar units
    max_pressure       : float max pressure in bar
    """

    def __init__(self, port="SIM", name="", channel=1, address=0x80, max_pressure=10.0):
        from flowchem.devices.flowchem_device import FlowchemDevice

        FlowchemDevice.__init__(self, name)
        self.port = port
        self.channel = channel
        self.address = address
        self.max_pressure = max_pressure
        self.device_info.authors = []
        self.device_info.manufacturer = "Bronkhorst"
        # Inject fake propar instrument
        self.el_press = _FakeProparInstrument()
        self.id = self.el_press.id
        logger.debug(
            f"[SIM] EPC '{name}' initialized (max_pressure={max_pressure} bar)"
        )

    @classmethod
    def from_config(cls, **config) -> "EPCSim":
        config.pop("port", None)
        return cls(
            name=config.pop("name", "sim-epc"),
            max_pressure=float(config.pop("max_pressure", 10.0)),
            channel=int(config.pop("channel", 1)),
            address=int(config.pop("address", 0x80)),
        )

    async def set_pressure(self, pressure: str):
        await super().set_pressure(pressure)
        self.el_press.measure = self.el_press.setpoint
