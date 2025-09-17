"""Power control, sets both voltage and current. (Could be split in two, unnecessary for now)."""
from __future__ import annotations

from flowchem.components.flowchem_component import FlowchemComponent
from flowchem.devices.flowchem_device import FlowchemDevice


class PowerSwitch(FlowchemComponent):
    """A generic power on/off switch."""

    def __init__(
        self,
        name: str,
        hw_device: FlowchemDevice,
    ) -> None:
        """Create a TemperatureControl object."""
        super().__init__(name, hw_device)

        self.add_api_route("/power-on", self.power_on, methods=["PUT"])
        self.add_api_route("/power-off", self.power_off, methods=["PUT"])

    async def power_on(self):
        """Turn power on."""
        ...

    async def power_off(self):
        """Turn off power."""
        ...


class PowerControl(PowerSwitch):
    """A generic power controller, adjusting voltage and/or current."""

    def __init__(
        self,
        name: str,
        hw_device: FlowchemDevice,
    ) -> None:
        """Create a PowerSwitch object."""
        super().__init__(name, hw_device)

        self.add_api_route("/power-on", self.power_on, methods=["PUT"])
        self.add_api_route("/power-off", self.power_off, methods=["PUT"])

        # Current
        self.add_api_route("/current", self.get_current, methods=["GET"])
        self.add_api_route("/current", self.set_current, methods=["PUT"])

        # Voltage
        self.add_api_route("/voltage", self.get_voltage, methods=["GET"])
        self.add_api_route("/voltage", self.set_voltage, methods=["PUT"])

    async def set_current(self, current: str):
        """Set the target current to the given string in "magnitude and unit" format."""
        ...

    async def get_current(self) -> float:  # type: ignore
        """Return current in Ampere."""
        ...

    async def set_voltage(self, voltage: str):
        """Set the target voltage to the given string in "magnitude and unit" format."""
        ...

    async def get_voltage(self) -> float:  # type: ignore
        """Return current in Volt."""
        ...
