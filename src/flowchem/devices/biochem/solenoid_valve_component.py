from __future__ import annotations

from flowchem.components.valves.solenoid import SolenoidValve
from flowchem.devices.flowchem_device import FlowchemDevice


class SolenoidValveComponent(SolenoidValve):
    """
    Extension of the SolenoidValve class with low-power mode support.

    This component adds functionality to switch the solenoid valve 
    into a low-power holding mode after a specified delay. 
    This feature helps prevent overheating of the solenoid coil 
    during long periods of continuous operation.

    API routes exposed (in addition to SolenoidValve):
        - PUT `/switch_to_low_power`: Schedule transition to low-power mode.
    """
    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        super().__init__(name, hw_device)

        self.add_api_route("/switch_to_low_power", self.switch_to_low_power, methods=["PUT"])

        self.low_power_after: float = -1  # -1 is off

    async def switch_to_low_power(self, after: float):
        """
        Schedule switching the valve to low-power mode.

        This reduces the risk of overheating by lowering
        the power supplied to the solenoid after the
        given delay (in seconds).

        Parameters
        ----------
        after : float
            Time in seconds after which the solenoid should enter
            low-power mode. Use `-1` to disable low-power switching.

        Returns
        -------
        None
        """
        self.low_power_after = after

    async def open(self):
        """
        Open the solenoid valve.

        This method energizes the solenoid, switching the valve to the
        "open" state, allowing flow through the channel.
        """
        return await self.hw_device.change_status(True, self.low_power_after)  # type:ignore[attr-defined]

    async def close(self):
        """
        Close the solenoid valve.

        This method de-energizes the solenoid, switching the valve to
        the "closed" state, stopping flow through the channel.
        """
        return await self.hw_device.change_status(False, self.low_power_after)  # type:ignore[attr-defined]

    async def status(self) -> bool:
        """
        Get the current valve status.

        Returns
        -------
        bool
            `True` if the valve is open, `False` if closed.
        """
        return await self.hw_device.status()  # type:ignore[attr-defined]