"""Control module for the Knauer DAD."""

import asyncio
from typing import TYPE_CHECKING

from loguru import logger

from flowchem.devices.flowchem_device import RepeatedTaskInfo
from flowchem.components.device_info import DeviceInfo
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.knauer._common import KnauerEthernetDevice
from flowchem.devices.knauer.dad_component import (
    DADChannelControl,
    KnauerDADLampControl,
)
from flowchem.utils.exceptions import InvalidConfigurationError
from flowchem.utils.people import dario, jakob, wei_hsin

if TYPE_CHECKING:
    pass

try:
    from flowchem_knauer import KnauerDADCommands

    HAS_DAD_COMMANDS = True
except ImportError:
    HAS_DAD_COMMANDS = False


class KnauerDAD(KnauerEthernetDevice, FlowchemDevice):
    """DAD control class."""

    def __init__(
        self,
        ip_address: object = None,
        mac_address: object = None,
        name: str | None = None,
        turn_on_d2: bool = False,
        turn_on_halogen: bool = False,
        display_control: bool = True,
    ) -> None:
        super().__init__(ip_address, mac_address, name=name)
        self.eol = b"\n\r"
        self._d2 = turn_on_d2
        self._hal = turn_on_halogen
        self._state_d2 = False
        self._state_hal = False
        self._control = display_control  # True for Local

        if not HAS_DAD_COMMANDS:
            raise InvalidConfigurationError(
                "You tried to use a Knauer DAD device but the relevant commands are missing!\n"
                "Unfortunately, we cannot publish those as they were provided under NDA.\n"
                "Contact Knauer for further assistance."
            )

        self.cmd = KnauerDADCommands()
        self.device_info = DeviceInfo(
            authors=[dario, jakob, wei_hsin],
            manufacturer="Knauer",
            model="DAD",
        )

    async def initialize(self):
        """Initialize connection."""
        await super().initialize()

        if self._control:
            await self.display_control(True)

        # get device information
        logger.info(f"Connected with Knauer DAD num {await self.serial_num()}")
        logger.info(f"Knauer DAD info: {await self.identify()} {await self.info()}")
        logger.info(f"Knauer DAD status: {await self.status()}")

        await self.set_wavelength(1, 254)
        await self.bandwidth(8)
        logger.info("set channel 1 : WL = 254 nm, BW = 8nm ")

        self.components = [
            KnauerDADLampControl("d2", self),
            KnauerDADLampControl("hal", self),
        ]

        self.components.extend(
            [DADChannelControl(f"channel{n + 1}", self, n + 1) for n in range(4)]
        )

    async def lamp(self, lamp: str, state: bool | str = "REQUEST") -> str:
        """Turn on or off the lamp, or request lamp state."""
        if isinstance(state, bool):
            state = "ON" if state else "OFF"

        lamp_mapping = {"d2": "_D2", "hal": "_HAL"}

        lampstatus_mapping = {
            "REQUEST": "?",
            "OFF": "0",
            "ON": "1",
            "HEAT": "2",
            "ERROR": "3",
        }
        _reverse_lampstatus_mapping = {v: k for k, v in lampstatus_mapping.items()}

        cmd = self.cmd.LAMP.format(
            lamp=lamp_mapping[lamp],
            state=lampstatus_mapping[state],
        )
        response = await self._send_and_receive(cmd)  # 'LAMP_D2:0'
        return response
        # if response.isnumeric() else _reverse_lampstatus_mapping[response[response.find(":") + 1:]]

    async def serial_num(self) -> str:
        """Get serial number."""
        return await self._send_and_receive(self.cmd.SERIAL)

    async def identify(self) -> str:
        """Get the instrument information
        CATEGORY (=3), MANUFACTURER,  MODEL_NR, SERNUM, VERSION,  MODIFICATION
        Example: 3,KNAUER,PDA-1,CSA094400001,2,01.
        """
        return await self._send_and_receive(self.cmd.IDENTIFY)

    async def info(self) -> str:
        """Get the instrument information
        NUMBER OF PIXEL (256, 512, 1024), SPECTRAL RANGE(“UV”, “VIS”, “UV-VIS”),
        HARDWARE VERSION, YEAR OF PRODUCTION,WEEK OF PRODUCTION,,CALIBR. A,CALIBR. B,, CALIBR. C.
        """
        return await self._send_and_receive(self.cmd.INFO)

    async def status(self):
        """Get status of the instrument
        Sending spectra (ON = 1, OFF = 0),
        D2 Lamp (OFF = 0, ON = 1, HEAT= 2, ERROR = 3),
        HAL Lamp (OFF = 0, ON = 1, ERROR = 3),
        Shutter(OFF = 0, ON=1, FILTER=2),
        External Error IN, External Start IN, External Autozero IN,
        Event1 OUT, Event2 OUT, Event3 OUT, Valve OUT, Error Code.
        """
        return await self._send_and_receive(self.cmd.STATUS)

    async def display_control(self, control: bool = True):
        cmd = self.cmd.LOCAL if control else self.cmd.REMOTE
        self._control = control
        return await self._send_and_receive(cmd)

    async def shutter(self, shutter: str) -> str:
        shutter_mapping = {"REQUEST": "?", "CLOSED": "0", "OPEN": "1", "FILTER": "2"}
        _reverse_shutter_mapping = {v: k for k, v in shutter_mapping.items()}

        cmd = self.cmd.SHUTTER.format(state=shutter_mapping[shutter])
        response = await self._send_and_receive(cmd)
        return (
            response
            if not response.isnumeric()
            else _reverse_shutter_mapping[response[response.find(":") + 1 :]]
        )

    async def signal_type(self, s_type: str = "microAU") -> str:
        """Set and get the type of signal shown on the display
        0 = signal is Absorption Units
        1 = signal is intensity.
        """
        type_mapping = {"REQUEST": "?", "microAU": "0", "intensity": "1"}
        _reverse_type_mapping = {v: k for k, v in type_mapping.items()}

        cmd = self.cmd.SIGNAL_TYPE.format(state=type_mapping[s_type])
        response = await self._send_and_receive(cmd)
        return (
            response
            if not response.isnumeric()
            else _reverse_type_mapping[response[response.find(":") + 1 :]]
        )

    async def get_wavelength(self, channel: int) -> int:
        cmd = self.cmd.WAVELENGTH.format(channel=channel, wavelength="?")
        return int(await self._send_and_receive(cmd))

    async def set_wavelength(self, channel: int, wavelength: int) -> str:
        """Set and read wavelength."""
        cmd = self.cmd.WAVELENGTH.format(channel=channel, wavelength=wavelength)
        return await self._send_and_receive(cmd)

    async def set_signal(self, channel: int, signal: int = 0):
        """Set signal to specific number."""
        cmd = self.cmd.SIGNAL.format(channel=channel, signal=signal)
        return await self._send_and_receive(cmd)

    async def read_signal(self, channel: int) -> float:
        """Read signal
        -9999999 to +9999999 (μAU, SIG_SRC = 0); 0 to 1000000 (INT, SIG_SRC = 1).
        """
        cmd = self.cmd.SIGNAL.format(channel=channel, signal="?")
        response = await self._send_and_receive(cmd)
        logger.info(f"signal: {response}")  # SIG1:113545,
        parsed_response = response.split(":")
        if parsed_response[1] == "OK":
            logger.warning(
                f"ValueError[channel{channel}]:the reply of 'get signal' command is OK.."
            )
            return await self.read_signal(channel)
        elif parsed_response[0] == f"SIG{channel}":
            return float(parsed_response[1]) / 10000
        else:
            logger.warning(
                f"ValueError[channel{channel}]: receive the reply not for channel{channel}!"
            )
            return await self.read_signal(channel)

    async def integration_time(self, integ_time: int | str = "?") -> str | int:
        """Set and read the integration time in 10 - 2000 ms."""
        cmd = self.cmd.INTEGRATION_TIME.format(time=integ_time)
        response = await self._send_and_receive(cmd)
        try:
            return int(response)  # ms
        except ValueError:
            return response

    async def bandwidth(self, bw: str | int) -> str | int:
        """Set bandwidth in the range of 4 to 25 nm
        read the setting of bandwidth.
        """
        if isinstance(bw, int):
            cmd = self.cmd.BANDWIDTH.format(bandwidth=bw)
            return await self._send_and_receive(cmd)
        else:
            cmd = self.cmd.BANDWIDTH.format(bandwidth="?")
            response = await self._send_and_receive(cmd)
            return int(response)

    def repeated_task(self):
        async def keepalive():
            await self.status()

        return RepeatedTaskInfo(seconds_every=45, task=keepalive)


async def main(dad):
    """Test function."""
    await dad.initialize()
    lamp_d2, lamp_hal, ch1, ch2, ch3, ch4 = dad.components()
    # bg1 = dad.bg_keep_connect()
    dad.info()
    # await asyncio.gather(asyncio.to_thread(bg2), bg2)

    # # set signal of channel 1 to zero
    # # await DAD.set_signal(1)
    # await ch1.set_wavelength(520)
    # await ch1.set_integration_time(70)
    # await ch1.set_bandwidth(4)
    # await ch1.acquire_signal()
    # await asyncio.sleep(60)
    # await DAD.initialize()
    # await ch1.acquire_signal()

    # set signal of channel 1 to zero
    # await DAD.set_signal(1)
    await ch1.set_wavelength(500)
    await ch1.set_integration_time(70)
    await ch1.set_bandwidth(8)
    await ch1.acquire_signal()


if __name__ == "__main__":
    k_dad = KnauerDAD(
        ip_address="192.168.10.7", turn_on_d2=False, turn_on_halogen=False
    )
    asyncio.run(main(k_dad))
