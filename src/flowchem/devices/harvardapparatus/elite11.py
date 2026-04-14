"""This module is used to control Harvard Apparatus Elite 11 syringe pump via the 11 protocol."""

from __future__ import annotations

import asyncio
import warnings

import pint
from loguru import logger
from pydantic import BaseModel

from flowchem import ureg
from flowchem.components.device_info import DeviceInfo
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.harvardapparatus._pumpio import (
    HarvardApparatusPumpIO,
    Protocol11Command,
    PumpStatus,
)
from flowchem.devices.harvardapparatus.elite11_pump import (
    Elite11PumpOnly,
    Elite11PumpWithdraw,
)
from flowchem.utils.exceptions import InvalidConfigurationError
from flowchem.utils.people import dario, jakob, wei_hsin


class PumpInfo(BaseModel):
    """Detailed pump info. e.g.:

    ('Pump type          Pump 11',
    'Pump type string   11 ELITE I/W Single',
    'Display type       Sharp',
    'Steps per rev      400',
    'Gear ratio         1:1',
    'Pulley ratio       2.4:1',
    'Lead screw         24 threads per inch',
    'Microstepping      16 microsteps per step',
    'Low speed limit    27 seconds',
    'High speed limit   26 microseconds',
    'Motor polarity     Reverse',
    'Min syringe size   0.1 mm',
    'Max syringe size   33 mm',
    'Min raw force %    20%',
    'Max raw force %    80%',
    'Encoder            100 lines',
    'Direction          Infuse/withdraw',
    'Programmable       Yes',
    'Limit switches     No',
    'Command set        None', '')
    """

    pump_type: str
    pump_description: str
    infuse_only: bool

    @classmethod
    def parse_pump_string(cls, metrics_text: list[str]):
        """Parse pump response string into model."""
        pump_type, pump_description, infuse_only = "", "", True
        for line in metrics_text:
            if line.startswith("Pump type  "):
                pump_type = line[9:].strip()
            elif line.startswith("Pump type string"):
                pump_description = line[16:].strip()
            elif line.startswith("Direction"):
                infuse_only = "withdraw" not in line
        return cls(
            pump_type=pump_type,
            pump_description=pump_description,
            infuse_only=infuse_only,
        )


class Elite11(FlowchemDevice):
    """Controls Harvard Apparatus Elite11 syringe pumps.

    The same protocol (Protocol11) can be used on other HA pumps, but is untested.
    Several pumps can be daisy-chained on the same serial connection, if so address 0 must be the first one.
    Read the manufacturer manual for more details.
    """

    # This class variable is used for daisy chains (i.e. multiple pumps on the same serial connection).
    _io_instances: set[HarvardApparatusPumpIO] = set()

    def __init__(
        self,
        pump_io: HarvardApparatusPumpIO,
        syringe_diameter: str = "",
        syringe_volume: str = "",
        address: int = 0,
        name: str = "",
        force: int = 30,
    ) -> None:
        super().__init__(name)

        # Create communication
        self.pump_io = pump_io
        Elite11._io_instances.add(self.pump_io)

        self.address = address
        self._infuse_only = False  # Actual value set in initialize

        # syringe diameter and volume, and force will be set in initialize()
        self._force = force
        if syringe_diameter:
            self._diameter = syringe_diameter
        else:
            raise InvalidConfigurationError("Please provide the syringe diameter!")

        if syringe_volume:
            self._syringe_volume = syringe_volume
        else:
            raise InvalidConfigurationError("Please provide the syringe volume!")

        self.device_info = DeviceInfo(
            authors=[dario, jakob, wei_hsin],
            manufacturer="HarvardApparatus",
            model="Elite11",
        )

    @classmethod
    def from_config(
        cls,
        port: str,
        syringe_diameter: str,
        syringe_volume: str,
        address: int = -1,
        name: str = "",
        force: int = 30,
        **serial_kwargs,
    ):
        """Programmatic instantiation from configuration.

        Many pump can be present on the same serial port with different addresses.
        This shared list of PumpIO objects allow shared state in a borg-inspired way, avoiding singletons
        This is only relevant to programmatic instantiation, i.e. when from_config() is called per each pump from a
        config file, as it is the case in the HTTP server.
        Pump_IO() manually instantiated are not accounted for.
        """
        pumpio = None
        for obj in Elite11._io_instances:
            if obj._serial.port == port:
                pumpio = obj
                break

        # If not existing serial object are available for the port provided, create a new one
        if pumpio is None:
            pumpio = HarvardApparatusPumpIO(port, **serial_kwargs)

        return cls(
            pumpio,
            address=address,
            name=name,
            syringe_diameter=syringe_diameter,
            syringe_volume=syringe_volume,
            force=force,
        )

    async def initialize(self):
        """Initialize Elite11.

        Query model and version number of firmware to check if pump is connected.
        Responds with a load of stuff, but the last three characters
        are the prompt XXY, where XX is the address and Y is pump status.
        The status can be one of the three: [":", ">" "<"] respectively
        when stopped, running forwards (pumping), or backwards (withdrawing).
        The prompt is used to confirm that the address is correct.
        """
        # Autodetect address if none provided
        if self.address == -1:
            self.address = self.pump_io.autodiscover_address()

        # Test communication and return InvalidConfiguration on failure
        try:
            await self.stop()
        except IndexError as index_e:
            raise InvalidConfigurationError(
                f"Check pump address! Currently {self.address=}"
            ) from index_e

        # Sets syringe parameters
        await self.set_syringe_diameter(ureg.Quantity(self._diameter))
        await self.set_syringe_volume(ureg.Quantity(self._syringe_volume))
        await self.set_force(self._force)

        logger.info(
            f"Connected to '{self.name}'! [{self.pump_io._serial.name}:{self.address}]",
        )
        version = await self.version()
        self._infuse_only = "I/W" not in version

        # Clear target volume eventually set to prevent pump from stopping prematurely
        await self.set_target_volume("0 ml")

        # Add components
        if self._infuse_only:
            self.components.append(Elite11PumpOnly("pump", self))
        else:
            self.components.append(Elite11PumpWithdraw("pump", self))

    @staticmethod
    def _parse_version(version_text: str) -> tuple[int, int, int]:
        """Extract semver from Elite11 version string, e.g. '11 ELITE I/W Single 3.0.4'."""
        version = version_text.split(" ")[-1]
        digits = version.split(".")
        return int(digits[0]), int(digits[1]), int(digits[2])

    async def _send_command_and_read_reply(
        self,
        command: str,
        parameter="",
        parse=True,
        multiline=False,
    ):
        """Send a command based on its template and return the corresponding reply as str."""
        cmd = Protocol11Command(
            command=command,
            pump_address=self.address,
            arguments=parameter,
        )
        reply = await self.pump_io.write_and_read_reply(cmd, return_parsed=parse)
        if multiline:
            return reply
        else:
            return reply[0]

    async def get_syringe_diameter(self) -> str:
        """Get syringe diameter in mm. A value between 1 and 33 mm."""
        return await self._send_command_and_read_reply("diameter")

    async def set_syringe_diameter(self, diameter: pint.Quantity):
        """Set syringe diameter. This can be set in the interval 1 mm to 33 mm."""
        if not 1 * ureg.mm <= diameter <= 33 * ureg.mm:
            logger.warning(
                f"Invalid diameter provided: {diameter}! [Valid range: 1-33 mm]",
            )
            return False

        await self._send_command_and_read_reply(
            "diameter",
            parameter=f"{diameter.to('mm').magnitude:.4f} mm",
        )
        return None

    async def get_syringe_volume(self) -> str:
        """Return the syringe volume as str w/ units."""
        return await self._send_command_and_read_reply("svolume")  # e.g. '100 ml'

    async def set_syringe_volume(self, volume: pint.Quantity):
        """Set the syringe volume in ml."""
        await self._send_command_and_read_reply(
            "svolume",
            parameter=f"{volume.m_as('ml'):.15f} m",
        )

    async def get_force(self):
        """Pump force, in percentage.

        Manufacturer suggested values are:
            stainless steel:    100%
            plastic syringes:   50% if volume <= 5 ml else 100%
            glass/glass:        30% if volume <= 20 ml else 50%
            glass/plastic:      30% if volume <= 250 ul, 50% if volume <= 5ml else 100%
        """
        percent = await self._send_command_and_read_reply("FORCE")
        return int(percent[:-1])

    async def set_force(self, force_percent: int):
        """Set the pump force, see `Elite11.get_force()` for suggested values."""
        await self._send_command_and_read_reply(
            "FORCE",
            parameter=str(int(force_percent)),
        )

    async def _bound_rate_to_pump_limits(self, rate: str) -> float:
        """Bound the rate provided to pump's limit.

        These are function of the syringe diameter.
        NOTE: Infusion and withdraw limits are equal!
        """
        # Get current pump limits (those are function of the syringe diameter)
        limits_raw = await self._send_command_and_read_reply("irate lim")

        # Lower limit usually expressed in nl/min so unit-aware quantities are needed
        lower_limit, upper_limit = map(ureg, limits_raw.split(" to "))

        # add units by assumption
        # if rate.isnumeric():
        #     rate = flowrate + "ml/min"
        #     logger.warning("No units provided, assuming milliliter/minutes.")
        # parsed_f = ureg.Quantity(flow)

        # Also add units to the provided rate
        set_rate: pint.Quantity = ureg.Quantity(rate)

        # Bound rate to acceptance range
        if set_rate < lower_limit:
            logger.warning(
                f"The requested rate {rate} is lower than the minimum possible ({lower_limit})!"
                f"Setting rate to {lower_limit} instead!",
            )
            set_rate = lower_limit

        if set_rate > upper_limit:
            logger.warning(
                f"The requested rate {rate} is higher than the maximum possible ({upper_limit})!"
                f"Setting rate to {upper_limit} instead!",
            )
            set_rate = upper_limit

        return set_rate.to("ml/min").magnitude

    async def version(self) -> str:
        """Return the current firmware version reported by the pump."""
        return await self._send_command_and_read_reply(
            "VER",
        )  # '11 ELITE I/W Single 3.0.4

    async def is_moving(self) -> bool:
        """Evaluate prompt for current status, i.e. moving or not."""
        status = await self._send_command_and_read_reply(" ", parse=False)
        prompt = PumpStatus(status[2:3])
        return prompt in (PumpStatus.INFUSING, PumpStatus.WITHDRAWING)

    async def infuse(self):
        """Run pump in infuse mode."""
        await self._send_command_and_read_reply("irun")
        logger.info("Pump infusion started!")
        return True

    async def withdraw(self):
        """Activate pump to run in withdraw mode."""
        await self._send_command_and_read_reply("wrun")
        logger.info("Pump withdraw started!")
        return True

    async def stop(self):
        """Stop pump."""
        await self._send_command_and_read_reply("stp")
        logger.info("Pump stopped")

    async def wait_until_idle(self):
        """Wait until the pump is not moving."""
        while await self.is_moving():
            await asyncio.sleep(0.05)

    async def get_flow_rate(self) -> float:
        """Return the infusion rate as str w/ units."""
        flow_value = await self._send_command_and_read_reply("irate")
        flowrate = ureg.Quantity(flow_value)
        logger.debug(f"Current infusion flow rate is {flowrate}")
        return flowrate.m_as("ml/min")

    async def set_flow_rate(self, rate: str):
        """Set the infusion rate."""
        set_rate = await self._bound_rate_to_pump_limits(rate=rate)
        await self._send_command_and_read_reply(
            "irate",
            parameter=f"{set_rate:.10f} m/m",
        )

    async def get_withdrawing_flow_rate(self) -> float:
        """Return the withdrawing flow rate as ml/min."""
        flow_value = await self._send_command_and_read_reply("wrate")
        flowrate = ureg.Quantity(flow_value)
        logger.debug(f"Current withdraw flow rate is {flowrate}")
        return flowrate.m_as("ml/min")

    async def set_withdrawing_flow_rate(self, rate: str):
        """Set the infusion rate."""
        set_rate = await self._bound_rate_to_pump_limits(rate=rate)
        await self._send_command_and_read_reply("wrate", parameter=f"{set_rate} m/m")

    async def set_target_volume(self, volume: str):
        """Set target volume in ml. If the volume is set to 0, the target is cleared."""
        await self._send_command_and_read_reply("cvolume")

        target_volume: pint.Quantity = ureg.Quantity(volume)
        if target_volume.magnitude == 0:
            await self._send_command_and_read_reply("ctvolume")
        else:
            set_vol = await self._send_command_and_read_reply(
                "tvolume",
                parameter=f"{target_volume.m_as('ml')} m",
            )
            if "Argument error" in set_vol:
                warnings.warn(
                    f"Cannot set target volume of {target_volume} with a "
                    f"{self.get_syringe_volume()} syringe!",
                    stacklevel=2,
                )

    async def pump_info(self) -> PumpInfo:
        """Return pump info."""
        parsed_multiline_response = await self._send_command_and_read_reply(
            "metrics",
            multiline=True,
        )
        return PumpInfo.parse_pump_string(parsed_multiline_response)


if __name__ == "__main__":
    pump = Elite11.from_config(
        port="COM5",
        syringe_volume="10 ml",
        syringe_diameter="14.567 mm",
        address=3,
    )

    async def main():
        """Test function."""
        await pump.initialize()
        # await pump.set_syringe_diameter("30 mm")
        # await pump.set_syringe_diameter("30 mm")
        print(await pump.version())
        await pump.set_flow_rate("0.001 ml/min")
        await pump.set_target_volume("0.001 ml")
        await pump.infuse()
        await asyncio.sleep(2)
        await pump.pump_info()

    asyncio.run(main())
