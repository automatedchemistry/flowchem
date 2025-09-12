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
   `SwitchBoxMPIKG.INSTANCES` under the given `support` name.
2) Initialize the valve device (`await valve.initialize()`).
3) Switch the valve state with `await valve.change_status(True/False, ...)`.
4) Query valve status with `await valve.status()`.

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
from .solenoid_valve_component import SolenoidValveComponent

from flowchem.devices.custom.mpikg_switch_box import SwitchBoxMPIKG

from loguru import logger
import asyncio

class SolenoidException(Exception):
    """Base exception class for solenoid-related errors."""
    pass


class InvalidConfiguration(SolenoidException):
    """Raised when the target switch-box support cannot be found or initialized."""
    pass


class BioChemSolenoidValve(FlowchemDevice):
    """
    Flowchem device that controls a single solenoid valve via an MPIKG switch box.

    This device:
      - waits for a `SwitchBoxMPIKG` instance with a matching `support` name to be
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

    def __init__(self, name: str, support: str, channel: int, normally_open: bool = True):

        super().__init__(name)

        self.support = support

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

        The method polls `SwitchBoxMPIKG.INSTANCES` for the given `support` name,
        sleeping 0.5 s between attempts. If the instance does not appear after a
        few seconds, an :class:`InvalidConfiguration` is raised.

        Raises
        ------
        InvalidConfiguration
            If no matching switch-box instance is found within the retry window.
        """

        n = 0
        while self.support not in SwitchBoxMPIKG.INSTANCES:
            await asyncio.sleep(0.5)
            n += 1
            if n > 6:
                raise InvalidConfiguration(
                    f"The electronic relay support '{self.support}' was not declared or initialized. "
                    "The valve cannot be initialized without a support "
                    "(Please add SwitchBoxMPIKG in the configuration file!)."
                )

        self._io = SwitchBoxMPIKG.INSTANCES[self.support]
        # Register the standard SolenoidValve component/API on this device
        self.components.append(SolenoidValveComponent("valve", self))
        conf_valve = "normally open" if self.normally_open else "normally close"
        logger.info(f"Connected to BioChemSolenoidValve {conf_valve} on '{self.support}' channel {self.channel}!")

    async def change_status(self, value: bool, switch_to_low_after=-1):
        """
        Change the valve state and optionally enter low-power mode.

        Parameters
        ----------
        value : bool
            Target state in flow terms:
              - True  -> valve OPEN
              - False -> valve CLOSED
            (The underlying relay actuation depends on `normally_open`.)
        switch_to_low_after : int | float, default -1
            Seconds after which the controller should reduce coil power to a
            low-power holding level. Use `-1` to keep full power (no low-power
            transition).

        Returns
        -------
        Any
            The return value of `SwitchBoxMPIKG.set_relay_single_channel(...)`.

        Notes
        -----
        - When `normally_open` is True, opening the valve requires no power
          (relay value 0) and closing energizes the coil (relay value 2).
        - When `normally_open` is False, the mapping is inverted.
        """
        if (self.normally_open and value) or (not self.normally_open and not value):
            return await self._io.set_relay_single_channel(
                channel=self.channel,
                value=0,
            )
        else:
            return await self._io.set_relay_single_channel(
                channel=self.channel,
                value=2,
                switch_to_low_after=switch_to_low_after
            )

    async def status(self) -> bool:
        """
        Read the current valve status from the switch box.

        Returns
        -------
        bool
            True if the relay channel is energized (value > 0), False otherwise.
            Interpreting this as OPEN/CLOSED depends on `normally_open`.

        Notes
        -----
        The MPIKG board exposes channels grouped by ports (a, b, c, d) in blocks
        of 8. This method maps `self.channel` (1–32) to the appropriate port and
        index, then reads `get_relay_channels()` and returns whether the channel
        is active.
        """
        status = await self._io.get_relay_channels()
        port, ch = "a", self.channel
        if 8 < self.channel <= 16:
            port, ch = "b", self.channel - 8
        elif 16 < self.channel <= 24:
            port, ch = "c", self.channel - 16
        elif 24 < self.channel <= 32:
            port, ch = "d", self.channel - 24
        return status[port][ch - 1] > 0


if __name__ == "__main__":
    box = SwitchBoxMPIKG.from_config(port="COM8", name="box")
    valve = BioChemSolenoidValve(name="", support="box", channel=1)
    async def main():
        """Test function."""
        await box.initialize()
        print(box.device_info.version)
        await valve.initialize()
        await valve.change_status(True, switch_to_low_after=1)
        await asyncio.sleep(1)
        result = await valve.status()
        print(result)

    asyncio.run(main())
