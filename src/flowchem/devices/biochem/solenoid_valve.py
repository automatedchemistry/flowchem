from __future__ import annotations
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.components.device_info import DeviceInfo
from flowchem.utils.people import samuel_saraiva
from flowchem.components.valves.solenoid import SolenoidValve, SolenoidValve2Way

from flowchem.components.technical.relay import Relay

from loguru import logger
import asyncio

class BioChemSolenoidValve(FlowchemDevice):
    """
    Flowchem device for controlling a single Bio-Chem solenoid valve via a relay component.

    The `BioChemSolenoidValve` interfaces with any Flowchem device that exposes a
    `Relay` component — either a single-channel or multi-channel relay controller.
    It waits for the corresponding relay instance (specified by `support_platform`)
    to become available and then registers a `SolenoidValve` component providing
    standardized `/open`, `/close`, and `/status` HTTP routes.

    If the relay device supports multiple channels, the user must specify the
    `channel` index used to drive this valve. For single-channel relays, the
    `channel` argument can be omitted.

    The valve can operate in *normally open* (NO) or *normally closed* (NC) mode:
      - **Normally open** (default): Flow path open when unpowered.
      - **Normally closed**: Flow path closed when unpowered.

    Typical usage
    -------------
    1. Ensure a Flowchem device containing a `Relay` component is initialized
       and available in ``Relay.INSTANCES`` under the given `support_platform`
       identifier (formatted as ``<device_name>/<relay_name>``).
    2. Initialize the valve device:
       ``await valve.initialize()``
    3. Operate the valve:
       ``await valve.open()`` or ``await valve.close()``
    4. Query valve state:
       ``await valve.is_open()``

    Parameters
    ----------
    name : str
        Unique identifier for this valve device within Flowchem.
    support_platform : str
        Identifier of the relay platform controlling the valve, formatted as
        ``<device_name>/<relay_name>``. Must correspond to a registered entry in
        ``Relay.INSTANCES``.
    channel : int, optional
        Relay channel index (1–32) if the relay supports multiple channels.
        Leave unset for single-channel relays.
    normally_open : bool, default True
        Defines the electrical/flow logic of the valve. If True, the valve is
        open by default (no power); if False, it is closed by default.

    Attributes
    ----------
    device_info : DeviceInfo
        Metadata for device traceability and identification.
    _io : Relay
        The bound relay instance controlling the valve channel.
    """

    def __init__(
            self,
            name: str,
            support_platform: str, # device_name/relay_name ex: mpibox/relay-A
            channel: int | None = None,
            normally_open: bool = True
    ):

        super().__init__(name)

        self.support_platform = support_platform

        self.channel = channel

        self.normally_open = normally_open

        self._io: Relay

        self.device_info = DeviceInfo(
            authors=[samuel_saraiva],
            manufacturer="Bio-Chem",
            model="Series of isolation valve",
        )

    async def initialize(self):
        """
        Bind the solenoid valve to the configured relay support platform.

        This method polls ``Relay.INSTANCES`` for the configured `support_platform` name.
        It checks every 0.5 seconds for up to ~3 seconds (6 attempts). Once the relay
        instance is found, the valve component is registered and becomes operational.

        Raises
        ------
        Exception
            If no matching relay instance is found within the retry window.
        """
        n = 0
        while self.support_platform not in Relay.INSTANCES:
            await asyncio.sleep(0.5)
            n += 1
            if n > 6:
                raise Exception(
                    f"The relay support_platform '{self.support_platform}' was not declared or initialized. "
                    "The valve cannot be initialized without a support_platform "
                    f"(Please add '{self.support_platform}' to the configuration file!)."
                )

        self._io = Relay.INSTANCES[self.support_platform]
        # Register the standard SolenoidValve component/API on this device
        self.components.append(SolenoidValve("valve", self))
        conf_valve = "normally open" if self.normally_open else "normally closed"
        logger.info(f"Connected to BioChemSolenoidValve {conf_valve} on '{self.support_platform}' channel {self.channel}!")

    async def open(self):
        """
        Open the solenoid valve.

        For *normally open* valves, opening the valve requires no power
        (relay OFF). For *normally closed* valves, opening requires power
        (relay ON).

        Notes
        -----
        - The relay channel index is specified by `self.channel`.
        - Behavior automatically inverts depending on the `normally_open` flag.
        - This method delegates to the underlying relay’s ``power_on`` or ``power_off``.
        """
        if self.normally_open:
            return await self._io.power_off(channel=self.channel)
        else:
            return await self._io.power_on(channel=self.channel)

    async def close(self):
        """
        Close the solenoid valve.

        For *normally open* valves, closing the valve energizes the relay
        (relay ON). For *normally closed* valves, closing requires no power
        (relay OFF).

        Notes
        -----
        - The relay channel index is specified by `self.channel`.
        - Behavior automatically inverts depending on the `normally_open` flag.
        - This method delegates to the underlying relay’s ``power_on`` or ``power_off``.
        """
        if self.normally_open:
            return await self._io.power_on(channel=self.channel)
        else:
            return await self._io.power_off(channel=self.channel)

    async def is_open(self) -> bool:
        """
        Determine whether the valve is currently open.

        This method queries the relay state using ``await self._io.is_on()`` and
        infers the flow condition based on the `normally_open` configuration.

        Returns
        -------
        bool
            True if the valve flow path is open, False otherwise.

        Notes
        -----
        - This method interprets the relay’s ON/OFF state according to the valve logic:
          for a *normally open* valve, an ON relay means *closed*; for a *normally closed*
          valve, an ON relay means *open*.
        """
        status = await self._io.is_on()
        if self.normally_open:
            return not status
        else:
            return status


class BioChemSolenoid2WayValve(BioChemSolenoidValve):

    async def initialize(self):
        """
        Bind the solenoid valve to the configured relay support platform.

        This method polls ``Relay.INSTANCES`` for the configured `support_platform` name.
        It checks every 0.5 seconds for up to ~3 seconds (6 attempts). Once the relay
        instance is found, the valve component is registered and becomes operational.

        Raises
        ------
        Exception
            If no matching relay instance is found within the retry window.
        """
        n = 0
        while self.support_platform not in Relay.INSTANCES:
            await asyncio.sleep(0.5)
            n += 1
            if n > 6:
                raise Exception(
                    f"The relay support_platform '{self.support_platform}' was not declared or initialized. "
                    "The valve cannot be initialized without a support_platform "
                    f"(Please add '{self.support_platform}' to the configuration file!)."
                )

        self._io = Relay.INSTANCES[self.support_platform]
        # Register the standard SolenoidValve component/API on this device
        self.components.append(SolenoidValve2Way("valve", self))
        conf_valve = "normally open" if self.normally_open else "normally closed"
        logger.info(f"Connected to BioChemSolenoidValve {conf_valve} on '{self.support_platform}' channel {self.channel}!")