"""Knauer valve control."""

import warnings
from enum import Enum
from loguru import logger

from flowchem.components.flowchem_component import FlowchemComponent
from flowchem.components.device_info import DeviceInfo
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.knauer._common import KnauerEthernetDevice
from flowchem.devices.knauer.knauer_valve_component import (
    Knauer6PortDistributionValve,
    Knauer12PortDistributionValve,
    Knauer16PortDistributionValve,
    KnauerInjectionValve,
)
from flowchem.utils.exceptions import DeviceError
from flowchem.utils.people import dario, jakob, wei_hsin


class KnauerValveHeads(Enum):
    """Four different valve types can be used. 6port2position injection valve, and 6, 12, 16 multi-position valves."""

    SIX_PORT_TWO_POSITION = "LI"
    SIX_PORT_SIX_POSITION = "6"
    TWELVE_PORT_TWELVE_POSITION = "12"
    SIXTEEN_PORT_SIXTEEN_POSITION = "16"


class KnauerValve(KnauerEthernetDevice, FlowchemDevice):
    """Control Knauer multi position valves.

    Valve type can be 6, 12, 16, or it can be 6 ports, two positions, which will be simply 2 (two states)
    in this case, the response for T is LI. Load and inject can be switched by sending L or I.
    Switching will always be performed by following parent valve type switching commands, so specifying which port
    should be connected
    Regarding initial valve state: If it matters, users want to determine initial state, which then also can happen
    explicit after initialisation and therefore is not deemed critical
    EN: https://www.knauer.net/Dokumente/valves/azura/manuals/v6860_azura_v_2.1s_user-manual_en.pdf
    DE: https://www.knauer.net/Dokumente/valves/azura/manuals/v6860_azura_v_2.1s_benutzerhandbuch_de.pdf
    DIP switch for valve selection
    """

    def __init__(self, ip_address=None, mac_address=None, **kwargs) -> None:
        super().__init__(ip_address, mac_address, **kwargs)
        self.eol = b"\r\n"
        self.device_info = DeviceInfo(
            authors=[dario, jakob, wei_hsin],
            manufacturer="Knauer",
            model="Valve",
        )

    async def initialize(self):
        """Initialize connection."""
        # The connection is established in KnauerEthernetDevice.initialize()
        await super().initialize()

        # Detect valve type
        self.device_info.additional_info["valve-type"] = await self.get_valve_type()

        # Set components
        valve_component: FlowchemComponent
        match self.device_info.additional_info["valve-type"]:
            case KnauerValveHeads.SIX_PORT_TWO_POSITION:
                valve_component = KnauerInjectionValve("injection-valve", self)
            case KnauerValveHeads.SIX_PORT_SIX_POSITION:
                valve_component = Knauer6PortDistributionValve(
                    "distribution-valve", self
                )
            case KnauerValveHeads.TWELVE_PORT_TWELVE_POSITION:
                valve_component = Knauer12PortDistributionValve(
                    "distribution-valve", self
                )
            case KnauerValveHeads.SIXTEEN_PORT_SIXTEEN_POSITION:
                valve_component = Knauer16PortDistributionValve(
                    "distribution-valve", self
                )
            case _:
                raise RuntimeError("Unknown valve type")
        self.components.append(valve_component)

    @staticmethod
    def handle_errors(reply: str):
        """Return True if there are errors, False otherwise. Warns for errors."""
        if not reply.startswith("E"):
            return

        if "E0" in reply:
            DeviceError(
                "The valve refused to switch.\n"
                "Replace the rotor seals of the valve or replace the motor drive unit.",
            )
        elif "E1" in reply:
            DeviceError(
                "Skipped switch: motor current too high!\n"
                "Replace the rotor seals of the valve.",
            )
        elif "E2" in reply:
            DeviceError(
                "Change from one valve position to the next takes too long.\n"
                "Replace the rotor seals of the valve.",
            )
        elif "E3" in reply:
            DeviceError(
                "Switch position of DIP 3 and 4 are not correct.\n"
                "Correct DIP switch 3 and 4.",
            )
        elif "E4" in reply:
            DeviceError(
                "Valve homing position not recognized.\n" "Adjust sensor board.",
            )
        elif "E5" in reply:
            DeviceError(
                "Switch position of DIP 1 and 2 are not correct.\n"
                "Correct DIP switch 1 and 2.",
            )
        elif "E6" in reply:
            DeviceError("Memory error.\n" "Power-cycle valve!")
        else:
            DeviceError("Unspecified error detected!")

    async def _transmit_and_parse_reply(self, message: str | int) -> str:
        """Send command, receive reply and parse it.

        Args:
        ----
            message (str): command to be sent

        Returns:
        -------
            str: reply
        """
        reply = await self._send_and_receive(str(message))
        self.handle_errors(reply)

        if reply == "?":
            # retry once before failing. This happens often on pos commands!
            reply = await self._send_and_receive(str(message))
            if reply == "?":
                warnings.warn(f"Command failed: {message}")
                logger.warning(f"Command failed: {message}")
                return ""

        return reply

    async def get_valve_type(self):
        """Get valve type, if returned value is not supported throws an error.

        Note that this method is called during initialize(), therefore it is in line
        with the general philosophy of the module to 'fail early' upon init and avoiding
        raising exception after that.
        """
        reply = await self._transmit_and_parse_reply("T")
        assert reply.startswith("VALVE ")
        reply = reply[6:]

        try:
            headtype = KnauerValveHeads(reply)
        except ValueError as value_error:
            raise DeviceError(
                "The valve type returned is not recognized.\n"
                "Are you sure the address provided is correct?\n"
                "Only multi-pos 6, 12, 16 and 2-pos 6 port valves are supported!"
            ) from value_error

        logger.info(f"Valve connected, type: {headtype}.")
        return headtype

    async def get_raw_position(self) -> str:
        """Return current valve position, following valve nomenclature."""
        return await self._transmit_and_parse_reply("P")

    async def set_raw_position(self, position: str) -> bool:
        """Set valve position, following valve nomenclature."""
        return await self._transmit_and_parse_reply(position) != ""


if __name__ == "__main__":
    import asyncio

    v = KnauerValve(ip_address="192.168.1.176")

    async def main(valve):
        """Test function."""
        await valve.initialize()
        await valve.set_raw_position("I")
        print(await valve.get_raw_position())
        await valve.set_raw_position("L")
        print(await valve.get_raw_position())

    asyncio.run(main(v))
