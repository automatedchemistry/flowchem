"""
BioChem solenoid valve device backed by an MPIKG switch box.

This module exposes:
- Domain-specific exceptions (`SolenoidException`, `InvalidConfiguration`)
- `BioChemSolenoidValve`, a `FlowchemDevice` that controls a single solenoid
  channel on a `SwitchBoxMPIKG` I/O board and registers a `SolenoidValve`
  component API.

Typical usage
-------------
1) Ensure a `SwitchBoxMPIKG` instance is created and registered (via
   `SwitchBoxMPIKG.from_config(...)` or equivalent) so it appears in
   `SwitchBoxMPIKG.INSTANCES` under the given `support_platform` name.
2) Initialize the valve device (`await valve.initialize()`).
3) Switch the valve state with `await valve.change_status(True/False, ...)`.
4) Query valve status with `await valve.is_open()`.

Notes
-----
- The device supports "normally open" logic. When `normally_open=True`, a
  `value=True` command opens the flow path without pulling the coil (value=0),
  while `value=False` energizes the coil (value=2) to close it, optionally
  entering a low-power holding mode after `switch_to_low_after` seconds.
"""
from __future__ import annotations
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.components.device_info import DeviceInfo
from flowchem.utils.people import samuel_saraiva
from .solenoid_valve_component import BioChemSolenoidValveComponent

from flowchem.devices.custom.mpikg_switch_box import SwitchBoxMPIKG

from loguru import logger
import asyncio

class SolenoidException(Exception):
    """Base exception class for solenoid-related errors."""
    pass


class InvalidConfiguration(SolenoidException):
    """Raised when the target switch-box support_platform cannot be found or initialized."""
    pass


class BioChemSolenoidValve(FlowchemDevice):
    """
    Flowchem device that controls a single solenoid valve via an MPIKG switch box.

    This device:
      - waits for a `SwitchBoxMPIKG` instance with a matching `support_platform` name to be
        available,
      - registers a `SolenoidValve` component under the device (exposing the
        standard `/open`, `/close`, `/status` HTTP routes),
      - drives a single relay channel to set the valve state, optionally switching
        to a low-power holding mode.

    Parameters
    ----------
    name : str
        Device identifier within Flowchem.
    support : str
        Name of the `SwitchBoxMPIKG` instance to bind to (key in
        `SwitchBoxMPIKG.INSTANCES`).
    channel : int
        Relay channel index (1–32) on the switch box.
    normally_open : bool, default True
        Electrical/flow logic of the valve. If True, the valve is open by default
        (no power). If False, the valve is closed by default (no power).

    Attributes
    ----------
    device_info : DeviceInfo
        Metadata for traceability.
    _io : SwitchBoxMPIKG
        The bound I/O board instance once initialization completes.
    """

    def __init__(self, name: str, support_platform: str, channel: int, normally_open: bool = True):

        super().__init__(name)

        self.support_platform = support_platform

        self.channel = channel

        self.normally_open = normally_open

        self._io: SwitchBoxMPIKG

        self.device_info = DeviceInfo(
            authors=[samuel_saraiva],
            manufacturer="Bio-Chem",
            model="Series of isolation valve",
        )

    async def initialize(self):
        """
        Bind to the configured `SwitchBoxMPIKG` instance and register the valve component.

        The method polls `SwitchBoxMPIKG.INSTANCES` for the given `support_platform` name,
        sleeping 0.5 s between attempts. If the instance does not appear after a
        few seconds, an :class:`InvalidConfiguration` is raised.

        Raises
        ------
        InvalidConfiguration
            If no matching switch-box instance is found within the retry window.
        """

        n = 0
        while self.support_platform not in SwitchBoxMPIKG.INSTANCES:
            await asyncio.sleep(0.5)
            n += 1
            if n > 6:
                raise InvalidConfiguration(
                    f"The electronic relay support_platform '{self.support_platform}' was not declared or initialized. "
                    "The valve cannot be initialized without a support_platform "
                    "(Please add SwitchBoxMPIKG in the configuration file!)."
                )

        self._io = SwitchBoxMPIKG.INSTANCES[self.support_platform]
        # Register the standard SolenoidValve component/API on this device
        self.components.append(BioChemSolenoidValveComponent("valve", self))
        conf_valve = "normally open" if self.normally_open else "normally closed"
        logger.info(f"Connected to BioChemSolenoidValve {conf_valve} on '{self.support_platform}' channel {self.channel}!")

    async def open(self, switch_to_low_after=-1):
        """
        Open valve and optionally enter low-power mode.

        Parameters
        ----------
        switch_to_low_after : int | float, default -1
            Seconds after which the controller should reduce coil power to a
            low-power holding level. Use `-1` to keep full power (no low-power
            transition).

        Notes
        -----
        - When `normally_open` is True, opening the valve requires no power
          (relay value 0) and not energizes the coil.
        - When `normally_open` is False, the mapping is inverted.
        """
        if self.normally_open:
            return await self._io.set_relay_single_channel(
                channel=self.channel,
                value=0,
                switch_to_low_after=switch_to_low_after
            )
        else:
            return await self._io.set_relay_single_channel(
                channel=self.channel,
                value=2,
                switch_to_low_after=switch_to_low_after
            )

    async def close(self, switch_to_low_after=-1):
        """
        Close valve and optionally enter low-power mode.

        Parameters
        ----------
        switch_to_low_after : int | float, default -1
            Seconds after which the controller should reduce coil power to a
            low-power holding level. Use `-1` to keep full power (no low-power
            transition).

        Notes
        -----
        - When `normally_open` is True, close the valve requires power
          (relay value 2) and energizes the coil.
        - When `normally_open` is False, the mapping is inverted.
        """
        if self.normally_open:
            return await self._io.set_relay_single_channel(
                channel=self.channel,
                value=2,
                switch_to_low_after=switch_to_low_after
            )
        else:
            return await self._io.set_relay_single_channel(
                channel=self.channel,
                value=0,
                switch_to_low_after=switch_to_low_after
            )

    async def is_open(self) -> bool:
        """
        Read the current valve status from the switch box.

        Returns
        -------
        bool
            True if the relay channel is open, False otherwise.

        Notes
        -----
        The MPIKG board exposes channels grouped by ports (a, b, c, d) in blocks
        of 8. This method maps `self.channel` (1–32) to the appropriate port and
        index, then reads `get_relay_channels()` and returns whether the channel
        is active and according to valve set up infer if the valve is open or not.
        """
        status = await self._io.get_relay_channels()
        port, ch = "a", self.channel
        if 8 < self.channel <= 16:
            port, ch = "b", self.channel - 8
        elif 16 < self.channel <= 24:
            port, ch = "c", self.channel - 16
        elif 24 < self.channel <= 32:
            port, ch = "d", self.channel - 24
        return status[port][ch - 1] > 0 and not self.normally_open or status[port][ch - 1] == 0 and self.normally_open


if __name__ == "__main__":
    box = SwitchBoxMPIKG.from_config(port="COM8", name="box")
    valve = BioChemSolenoidValve(name="", support_platform="box", channel=1)
    async def main():
        """Test function."""
        await box.initialize()
        print(box.device_info.version)
        await valve.initialize()
        await valve.open(switch_to_low_after=1)
        await asyncio.sleep(1)
        result = await valve.is_open()
        print(result)

    asyncio.run(main())
