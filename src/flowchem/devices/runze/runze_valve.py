"""Runze SV-06 multiposition distribution valve control."""

from loguru import logger

from flowchem.components.flowchem_component import FlowchemComponent
from flowchem.components.device_info import DeviceInfo
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.runze._common import (
    RunzeCommand as SV06Command,
    RunzeSerialIO as RunzeValveIO,
    RunzeValveHeads,
    detect_valve_type,
    get_shared_runze_io,
    send_and_await_completion,
)
from flowchem.devices.runze.runze_valve_component import (
    Runze6PortDistributionValve,
    Runze8PortDistributionValve,
    Runze10PortDistributionValve,
    Runze12PortDistributionValve,
    Runze16PortDistributionValve,
)
from flowchem.utils.people import miguel

__all__ = [
    "RunzeValve",
    "RunzeValveHeads",
    "RunzeValveIO",
    "SV06Command",
]


class RunzeValve(FlowchemDevice):
    """
    Control Runze multi position valves.
    """

    def __init__(
        self,
        valve_io: RunzeValveIO,
        name: str,
        address: int = 1,
    ) -> None:
        super().__init__(name)

        # Create communication
        self.valve_io = valve_io

        self.address = address

        self.device_info = DeviceInfo(
            authors=[miguel],
            manufacturer="Runze",
            model="SV-06",
        )

    async def initialize(self):
        await super().initialize()

        # Detect valve type
        self.device_info.additional_info["valve-type"] = await self.get_valve_type()

        # Set components
        valve_component: FlowchemComponent
        match self.device_info.additional_info["valve-type"]:
            case RunzeValveHeads.SIX_PORT_SIX_POSITION:
                valve_component = Runze6PortDistributionValve(
                    "distribution-valve", self
                )
            case RunzeValveHeads.EIGHT_PORT_EIGHT_POSITION:
                valve_component = Runze8PortDistributionValve(
                    "distribution-valve", self
                )
            case RunzeValveHeads.TEN_PORT_TEN_POSITION:
                valve_component = Runze10PortDistributionValve(
                    "distribution-valve", self
                )
            case RunzeValveHeads.TWELVE_PORT_TWELVE_POSITION:
                valve_component = Runze12PortDistributionValve(
                    "distribution-valve", self
                )
            case RunzeValveHeads.SIXTEEN_PORT_SIXTEEN_POSITION:
                valve_component = Runze16PortDistributionValve(
                    "distribution-valve", self
                )
            case _:
                raise RuntimeError("Unknown valve type")
        self.components.append(valve_component)

    async def get_valve_type(self):
        """Get valve type by testing possible port values."""  # There was no command for this
        return await detect_valve_type(self.set_raw_position)

    async def _send_command_and_read_reply(
        self,
        command: str,
        parameter: int = 0,
        raise_errors: bool = True,
        is_factory_command: bool = False,
    ):
        valve_command = SV06Command(
            function_code=command,
            address=self.address,
            parameter=parameter,
            is_factory_command=is_factory_command,
        )
        status, parameters = await self.valve_io.write_and_read_reply_async(
            valve_command, raise_errors
        )
        return status, parameters

    async def get_raw_position(self, raise_errors: bool = False) -> str:
        """Return current valve position, following valve nomenclature."""
        status, parameters = await self._send_command_and_read_reply(
            command="3e", raise_errors=raise_errors
        )
        if status == "00":
            position = str(int(parameters, 16))
            logger.info(f"Current valve position is: {position}")
            return position
        else:
            logger.warning(
                f"Something is not working in the valve. "
                f"Attempt to get raw position returned status: '{status}'."
            )
            return ""

    async def set_raw_position(self, position: str, raise_errors: bool = True) -> bool:
        """Set valve position, following valve nomenclature.

        Per the manual, 0x44 may reply immediately with status `fe`/`04`
        rather than waiting for the switch to complete -- completion is then
        confirmed by polling `get_status` (0x4a) until it reports `00`.
        """
        status, parameters = await send_and_await_completion(
            send_fn=lambda: self._send_command_and_read_reply(
                command="44", parameter=int(position), raise_errors=False
            ),
            poll_status_fn=self.get_status,
            raise_errors=raise_errors,
        )
        if status == "00":
            logger.info(f"Valve position set to: {parameters}")
            return True
        else:
            return False

    async def get_status(self) -> str:
        """Query motor status (0x4a): '00' idle/done, '04' busy, 'fe' task just accepted."""
        status, _ = await self._send_command_and_read_reply(
            command="4a", raise_errors=False
        )
        return status

    async def set_address(self, address: int) -> str:
        status, parameters = await self._send_command_and_read_reply(
            command="00", parameter=address, is_factory_command=True
        )
        if status == "00":
            self.address = address
        return status

    @classmethod
    def from_config(cls, **config):
        """Create instances via config file."""
        # Remove RunzeValve-specific keys to only have RunzeValveIO's configs
        config_for_valveio = {
            k: v for k, v in config.items() if k not in ("address", "name")
        }
        valveio = get_shared_runze_io(config.get("port"), config_for_valveio)

        return cls(
            valveio,
            address=config.get("address", 1),
            name=config.get("name", ""),
        )


if __name__ == "__main__":
    import asyncio

    conf = {
        "port": "COM5",
        "address": 1,
        "name": "runze_test",
    }
    v = RunzeValve.from_config(**conf)

    async def main(valve):
        """Test function."""
        await valve.initialize()
        # response = await valve.get_current_address()

    asyncio.run(main(v))
