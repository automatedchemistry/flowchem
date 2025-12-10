"""Component of the Electronic Box Control MPIKG."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pint.errors import UndefinedUnitError, DimensionalityError
from flowchem.components.technical.MultiChannels import (
    MultiChannelADC,
    MultiChannelDAC,
    MultiChannelRelay
)
from flowchem import ureg
from loguru import logger

if TYPE_CHECKING:
    from .mpikg_switch_box import SwitchBoxMPIKG


class SwitchBoxDAC(MultiChannelDAC):

    def __init__(self, name: str, hw_device: "SwitchBoxMPIKG"):

        super().__init__(name=name, hw_device=hw_device)

        self.hw_device: SwitchBoxMPIKG

    async def read(self, channel: str) -> float:  # type:ignore[override]
        """
        Read the DAC output of a channel.

        Args:
            channel (str): DAC channel index (1 or 2).

        Returns:
            float: DAC output in volts.
        """
        return await self.hw_device.get_dac(channel=int(channel), volts=True)

    async def set(self, channel: str = "1", value: str = "0 V") -> bool:  # type:ignore[override]
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


class SwitchBoxADC(MultiChannelADC):

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
        raise AttributeError(f"There is no channel '{channel} in ADC ports!'")

    async def read_all(self) -> dict[str, float]:
        """
        Read all ADC (Analog-to-Digital Converter) channels.

        Returns:
            dict[str, float]: Mapping of channel IDs (e.g. "ADC1", "ADC2") to measured
            voltage values in volts.
        """
        self.hw_device: SwitchBoxMPIKG
        return await self.hw_device.get_adc()


class SwitchBoxRelay(MultiChannelRelay):
    """
    Interface for controlling a multichannel relay module within a SwitchBox device.

    The `SwitchBoxRelay` class provides asynchronous control of relay ports ("a", "b", "c", or "d"),
    where each port controls up to 8 relay channels. It allows powering channels ON/OFF, setting
    multiple channels simultaneously, and reading their current state.

    Each channel supports three power modes:
        * 0 → OFF
        * 1 → Half power (~12 V)
        * 2 → Full power (~24 V)

    The `identify` parameter determines which physical port this instance controls:
        - Port "a" → channels 1–8
        - Port "b" → channels 9–16
        - Port "c" → channels 17–24
        - Port "d" → channels 25–32

    Args:
        name (str): Name assigned to the relay device instance.
        hw_device (SwitchBoxMPIKG): Reference to the connected SwitchBox hardware.
        identify (str): Port identifier ("a", "b", "c", or "d").
    """

    def __init__(self, name: str, hw_device: "SwitchBoxMPIKG", identify: str):
        super().__init__(name=name, hw_device=hw_device)
        self.hw_device: SwitchBoxMPIKG
        self.identify = identify  # Port identifier ("a", "b", "c", or "d")

        self.add_api_route("/lower_power_approach", self.set_lower_power_approach, methods=["PUT"])

        self.add_api_route("/channel_set_point", self.read_channel_set_point, methods=["GET"])

    async def power_on(self, channel: str) -> bool:  # type:ignore[override]
        """
        Power ON a single relay channel at full power (~24 V).

        Sends a command to set the specified channel to state "2".

        Args:
            channel (str): Relay channel index (1–8) or (1–32) depending on the port mapping:
                - Port a → channels 1–8
                - Port b → channels 9–16
                - Port c → channels 17–24
                - Port d → channels 25–32

        Returns:
            bool: True if the device acknowledged the command, False otherwise.
        """
        return await self.set_channel(channel, value="2")

    async def power_off(self, channel: str) -> bool:  # type:ignore[override]
        """
        Power OFF a single relay channel.

        Sends a command to set the given channel to state "0" (no voltage).

        Args:
            channel (str): Relay channel index (1–8) or (1–32) depending on the port mapping.

        Returns:
            bool: True if the device acknowledged the command, False otherwise.
        """
        return await self.set_channel(channel, value="0")

    async def switch_multiple_channel(self, values: str) -> bool:
        """
        Set the relay states of all 8 channels on the current port simultaneously.

        Each character in `values` represents one channel’s state:
            * 0 → OFF
            * 1 → Half power (~12 V)
            * 2 → Full power (~24 V)

        Args:
            values (str): String of up to 8 digits (0, 1, or 2).
                Example: "00010012"
                - If shorter than 8, remaining channels default to 0 (OFF).
                - If longer than 8, extra values are ignored.

        Returns:
            bool: True if the device acknowledged the command, False otherwise.
        """
        return await self.hw_device.set_relay_port(
            values=[int(c) for c in values],
            port=self.identify
        )

    async def read_channel_set_point(self, channel: str) -> int | None:
        """
        Read the current state of a specific relay channel.

        Channel states:
            * 0 → OFF
            * 1 → Half power (~12 V)
            * 2 → Full power (~24 V)

        Args:
            channel (str): Relay channel index (1–8) or (1–32) depending on the port.

        Returns:
            int | None:
                - 0, 1, or 2 → Valid relay state.
                - None → If the channel index is invalid or not part of this port.
        """
        ch = int(channel)
        if not 0 < ch <= 8:
            logger.error(f"There is not channel {ch} in device {self.name} at port-{self.identify}!")
            return None
        if ch > 8:
            if 8 < ch <= 16 and self.identify == "b":
                ch = ch - 8
            elif 16 < ch <= 24 and self.identify == "c":
                ch = ch - 16
            elif 24 < ch <= 32 and self.identify == "d":
                ch = ch - 24
            logger.error(f"There is not channel {ch} in device {self.hw_device.name} at port-{self.identify}!")
            return None
        asw = await self.hw_device.get_relay_channels()
        return asw[self.identify][ch - 1]

    async def read_multiple_channels_set_point(self) -> list[int]:
        """
        Read the current states of all 8 channels on the current port.

        Channel states:
            * 0 → OFF
            * 1 → Half power (~12 V)
            * 2 → Full power (~24 V)

        Returns:
            list[int]: List of 8 integers (0, 1, or 2) representing the current state
            of each relay channel on this port.
        """
        asw = await self.hw_device.get_relay_channels()
        return asw[self.identify]

    async def set_lower_power_approach(self, switch_to_low_after: str = "1 s"):
        """
        Configure automatic switching from full power to half power after a delay.

        This function reduces heat generation by automatically changing the relay output
        from full power (2) to half power (1) after the specified time.
        If the delay is set to 0 seconds, the feature is disabled.

        Args:
            switch_to_low_after (str): Delay time before switching to half power, with units.
                Example: "1 s", "500 ms", "2 s".
                Use "0 s" to disable automatic reduction.
        """
        value = ureg.Quantity(switch_to_low_after).to("s").magnitude
        if value > 0:
            return await self.hw_device.set_lower_power_approach(
                port=self.identify, switch_to_low_after=value
            )
        else:
            return await self.hw_device.set_lower_power_approach(
                port=self.identify, switch_to_low_after=-1
            )

    """ Auxiliary methods """

    async def set_channel(
        self,
        channel: str,
        value: str,
        keep_port_status: bool = True
    ) -> bool:
        """
        Set the state of a single relay channel.

        Args:
            channel (str): Relay channel index (1–8) or (1–32) if it matches the corresponding port.
            value (str): Desired channel state:
                * 0 → OFF
                * 1 → Half power (~12 V)
                * 2 → Full power (~24 V)
            keep_port_status (bool, optional):
                Whether to preserve the state of other channels in the same port.
                Defaults to True.

        Returns:
            bool: True if the device acknowledged the command, False otherwise.
        """
        return await self.hw_device.set_relay_single_channel(
            channel=int(channel),
            value=int(value),
            keep_port_status=keep_port_status,
            port_identify=self.identify
        )

