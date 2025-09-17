from __future__ import annotations

from typing import TYPE_CHECKING

from flowchem import ureg
from flowchem.components.flowchem_component import FlowchemComponent
from flowchem.components.sensors.pressure_sensor import PressureSensor
from flowchem.devices.flowchem_device import FlowchemDevice

if TYPE_CHECKING:
    from .el_flow import EPC, MFC


class EPCComponent(PressureSensor):
    """
    A class to represent a component that interfaces with an Electronic Pressure Controller (EPC) device.

    Attributes:
    -----------
    hw_device : EPC
        The hardware device (EPC) this component interfaces with.

    Methods:
    --------
    set_pressure_setpoint(pressure: str) -> bool:
        Set the controlled pressure to the instrument; default unit is bar.
    get_pressure() -> float:
        Get the current system pressure in bar.
    stop() -> bool:
        Stop the pressure controller by setting pressure to 0 bar.
    read_pressure(units: str = "bar"):
        Read the current pressure from the sensor and return it in the specified units.
    """
    hw_device: EPC  # just for typing

    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        """
        Constructs all the necessary attributes for the EPCComponent object.

        Parameters:
        -----------
        name : str
            The name of the EPC component.
        hw_device : FlowchemDevice
            The hardware device (EPC) this component interfaces with.
        """
        super().__init__(name, hw_device)
        self.add_api_route("/get-pressure", self.get_pressure, methods=["GET"])
        self.add_api_route("/set-pressure", self.set_pressure_setpoint, methods=["PUT"])
        self.add_api_route("/stop", self.stop, methods=["PUT"])

    async def set_pressure_setpoint(self, pressure: str) -> bool:
        """
        Set the controlled pressure on the instrument. The default unit is bar.
        The unit is handled through the `ureg` package to convert it to the unit configured on the device.
        To standardize units, it is recommended that the user works with the bar unit.

        Parameters:
        -----------
        pressure : str
            The desired pressure to set.

        Returns:
        --------
        bool
            True if the pressure setpoint was set successfully.
        """
        await self.hw_device.set_pressure(pressure)
        return True

    async def get_pressure(self) -> float:
        """
        Get the current system pressure in bar.

        Returns:
        --------
        float
            The current pressure in bar.
        """
        return await self.hw_device.get_pressure()

    async def stop(self) -> bool:
        """
        Stop the pressure controller by setting pressure to 0 bar.

        Returns:
        --------
        bool
            True if the pressure controller was stopped successfully.
        """
        await self.hw_device.set_pressure("0 bar")
        return True

    async def read_pressure(self, units: str = "bar"):
        """
        Read the current pressure from the sensor and return it in the specified units.

        Parameters:
        -----------
        units : str, optional
            The units in which to return the pressure (default is bar).

        Returns:
        --------
        float
            The current pressure in the specified units.
        """
        p = await self.hw_device.get_pressure()
        return p * ureg(units)  # <Quantity(4.56, 'bar')>


class MFCComponent(FlowchemComponent):
    """
    A class to represent a Mass Flow Controller (MFC) component.

    Attributes:
    -----------
    hw_device : MFC
        The hardware device (MFC) this component interfaces with.

    Methods:
    --------
    set_flow_setpoint(flowrate: str) -> bool:
        Set the flow rate to the instrument; default unit is ml/min.
    get_flow_setpoint() -> float:
        Get the current flow rate in ml/min.
    stop() -> bool:
        Stop the mass flow controller.
    """
    hw_device: MFC  # just for typing

    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        """
        Constructs all the necessary attributes for the MFCComponent object.

        Parameters:
        -----------
        name : str
            The name of the MFC component.
        hw_device : FlowchemDevice
            The hardware device (MFC) this component interfaces with.
        """
        super().__init__(name, hw_device)
        self.add_api_route("/get-flow-rate", self.get_flow_setpoint, methods=["GET"])
        self.add_api_route("/set-flow-rate", self.set_flow_setpoint, methods=["PUT"])
        self.add_api_route("/stop", self.stop, methods=["PUT"])

    async def set_flow_setpoint(self, flowrate: str) -> bool:
        """
        Set the flow rate to the instrument; default unit is ml/min.

        Parameters:
        -----------
        flowrate : str
            The desired flow rate to set.

        Returns:
        --------
        bool
            True if the flow rate setpoint was set successfully.
        """
        await self.hw_device.set_flow_setpoint(flowrate)
        return True

    async def get_flow_setpoint(self) -> float:
        """
        Get the current flow rate in ml/min.

        Returns:
        --------
        float
            The current flow rate in ml/min.
        """
        return await self.hw_device.get_flow_setpoint()

    async def stop(self) -> bool:
        """
        Stop the mass flow controller.

        Returns:
        --------
        bool
            True if the mass flow controller was stopped successfully.
        """
        await self.hw_device.set_flow_setpoint("0 ml/min")
        return True
