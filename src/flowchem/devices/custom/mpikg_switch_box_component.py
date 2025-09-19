"""Component of the Electronic Box Control MPIKG."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pint.errors import UndefinedUnitError, DimensionalityError
from flowchem.components.technical.ADC import AnalogDigitalConverter
from flowchem.components.technical.DAC import DigitalAnalogConverter
from flowchem.components.technical.relay import Relay
from flowchem import ureg
from loguru import logger

if TYPE_CHECKING:
    from .mpikg_switch_box import SwitchBoxMPIKG


class SwitchBoxDAC(DigitalAnalogConverter):

    def __init__(self, name: str, hw_device: "SwitchBoxMPIKG"):

        super().__init__(name=name, hw_device=hw_device)

        self.hw_device: SwitchBoxMPIKG

    async def read_channel(self, channel: str) -> float:
        """
        Read the DAC output of a channel.

        Args:
            channel (str): DAC channel index (1 or 2).

        Returns:
            float: DAC output in volts.
        """
        return await self.hw_device.get_dac(channel=int(channel), volts=True)

    async def set_channel(self, channel: str = "1", value: str = "0 V") -> bool:
        """
        Set the DAC output voltage for a given channel.

        Args:
            channel (str, optional): DAC channel index. Must be a digit string
                (e.g., "1", "2"). Defaults to "1".
            value (str, optional): Target voltage with unit, expressed as a string
                parsable by the unit registry (e.g., "2.5 V", "500 mV").
                Defaults to "0 V".

        Returns:
            bool:
                - True if the voltage command was successfully sent to the hardware.
                - False if the channel argument is invalid or if the value cannot be parsed.

        Notes:
            - The channel must be convertible to an integer.
            - The voltage string is parsed using the unit registry (`ureg`).
            - Any parsing or hardware errors are logged via `logger`.
        """
        if not channel.isdigit():
            logger.error("The argument channel of the DAC should be a digit (1, 2, ...)")
            return False
        try:
            volts = ureg(value)
        except (UndefinedUnitError, DimensionalityError, Exception) as e:
            logger.error(
                f"Invalid DAC value '{value}' for channel {channel}: {e}"
            )
            return False
        return await self.hw_device.set_dac(  # type:ignore[call-arg]
            channel=int(channel), value=volts
        )


class SwitchBoxADC(AnalogDigitalConverter):

    def __init__(self, name: str, hw_device: "SwitchBoxMPIKG"):

        super().__init__(name=name, hw_device=hw_device)

        self.add_api_route("/read_all", self.read_all, methods=["GET"])

    async def read(self, channel: str) -> float:  # type:ignore[override]
        """
        Read ADC (Analog-to-Digital Converter) channel (1 to 8).

        Returns:
            voltage value in volts.
        """
        asw = await self.read_all()
        value = asw.get(f"ADC{channel}")
        if value:
            return value
        logger.error(f"There is no channel '{channel} in ADC ports!'")
        return -1

    async def read_all(self) -> dict[str, float]:
        """
        Read all ADC (Analog-to-Digital Converter) channels.

        Returns:
            dict[str, float]: Mapping of channel IDs (e.g. "ADC1", "ADC2") to measured
            voltage values in volts.
        """
        self.hw_device: SwitchBoxMPIKG
        return await self.hw_device.get_adc()


class SwitchBoxRelay(Relay):

    def __init__(self, name: str, hw_device: "SwitchBoxMPIKG"):

        super().__init__(name=name, hw_device=hw_device)

        self.hw_device: SwitchBoxMPIKG

        self.add_api_route("/channel_setpoint", self.read_channel_setpoint, methods=["GET"])

        self.add_api_route("/channel", self.set_channel, methods=["PUT"])

        self.add_api_route("/read_channels_modules", self.read_channels_modules, methods=["GET"])

        self.add_api_route("/port_module", self.set_port_module, methods=["PUT"])


    async def power_on(self, channel: str) -> bool:  # type:ignore[override]
        """
        Set the state ON of a single relay channel.

        Args:
            channel (str): Relay channel index (1–32).

        Returns:
            bool: True if the device acknowledged the command, False otherwise.
        """
        return await self.set_channel(channel, value="2")

    async def power_off(self, channel: str) -> bool:  # type:ignore[override]
        """
        Set the state OFF of a single relay channel.

        Args:
            channel (str): Relay channel index (1–32).

        Returns:
            bool: True if the device acknowledged the command, False otherwise.
        """
        return await self.set_channel(channel, value="0")

    async def read_channel_setpoint(self, channel: str) -> int | None:
        """
        Read the current relay state of a single channel.

        Each channel corresponds to one relay (1–32), organized in four ports:
        - Port A → channels 1–8
        - Port B → channels 9–16
        - Port C → channels 17–24
        - Port D → channels 25–32

        Channel states:
            * 0 → OFF
            * 1 → Half power (power1 only, ~12 V)
            * 2 → Full power (power1 + power2, ~24 V)

        Args:
            channel (str): Relay channel index (1–32).

        Returns:
            int | bool:
                - 0, 1, or 2 → valid relay state.
                - None → if the channel index is invalid.
        """
        ch = int(channel)
        asw = await self.read_channels_modules()
        if 0 < ch <= 8:
            port, ch = "a", ch
        elif 8 < ch <= 16:
            port, ch = "b", ch - 8
        elif 16 < ch <= 24:
            port, ch = "c", ch - 16
        elif 24 < ch <= 32:
            port, ch = "d", ch - 24
        else:
            logger.error(f"There is not channel {ch} in device {self.name}!")
            return None
        return asw[port][ch-1]

    async def set_channel(
            self,
            channel: str,
            value: str,
            keep_port_status: str = "true",
            switch_to_low_after: float = -1) -> bool:
        """
        Set the state of a single relay channel.

        Args:
            channel (str): Relay channel index (1–32).
            value (str): Desired channel state:
                * 0 → OFF
                * 1 → Half power (~12 V)
                * 2 → Full power (~24 V)
            keep_port_status (str, optional):
                If true (default), preserves the state of other channels
                in the same port (module).
                If false, all other channels in the port are reset to 0.
            switch_to_low_after (float, optional):
                If >0 and value=2, automatically switches the channel
                to 1 (half power) after the given delay in seconds.
                Useful to reduce heat generation.
                Default = -1 (disabled).

        Returns:
            bool: True if the device acknowledged the command, False otherwise.
        """
        return await self.hw_device.set_relay_single_channel(
            channel=int(channel),
            value=int(value),
            keep_port_status=keep_port_status=="true",
            switch_to_low_after=switch_to_low_after
        )

    async def read_channels_modules(self) -> dict[str, list[int]]:
        """
        Query the relay states of all channels in modules.

        Returns:
            dict[str, list[int]]: A dictionary mapping port modules IDs ("a", "b", "c", "d")
            to lists of 8 integers each.
            Each integer represents the current state of one of the 8 channels:
                * 0 → OFF
                * 1 → Half power (~12 V)
                * 2 → Full power (~24 V)

        Example:
            {
                "a": [0, 1, 2, 0, 0, 1, 0, 0],
                "b": [...],
                "c": [...],
                "d": [...]
            }
        """
        return await self.hw_device.get_relay_channels()

    async def set_port_module(
            self,
            values: str,
            switch_to_low_after: float = -1,
            port: str = "a"
    ):
        """
        Set the relay states of all 8 channels in a port module.

        Channel states:
            * 0 → OFF
            * 1 → Half power (~12 V)
            * 2 → Full power (~24 V)

        Args:
            values (str): List of up to 8 integers (0, 1, or 2).
                - Example: "00010012"
                - If shorter than 8, remaining channels are set to 0.
                - If longer than 8, extra values are ignored.
            switch_to_low_after (float, optional):
                If >0, channels set to 2 (full power) are automatically
                reduced to 1 (half power) after the given delay in seconds.
                Default = -1 (disabled).
            port (str, optional): Port identifier ("a", "b", "c", or "d").
                Default = "a".

        Returns:
            bool: True if the device acknowledged the command, False otherwise.
        """

        return await self.hw_device.set_relay_port(
            values=[int(c) for c in values],
            switch_to_low_after=switch_to_low_after,
            port=port
        )
