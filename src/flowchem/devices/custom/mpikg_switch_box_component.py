"""Component of the Electronic Box Control MPIKG."""

from __future__ import annotations

from typing import TYPE_CHECKING

from flowchem.components.technical.ADC import AnalogDigitalSignal
from flowchem.components.technical.DAC import DigitalAnalogSignal
from flowchem.components.technical.relay import Relay
from loguru import logger

if TYPE_CHECKING:
    from .mpikg_switch_box import SwitchBoxMPIKG


class SwitchBoxDAC(DigitalAnalogSignal):

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

    async def set_channel(self, channel: str, value: float) -> bool:
        """
        Set DAC output voltage.

        Args:
            channel (str): DAC channel index (1 or 2).
            value (float): Target voltage (0 to 5 V).

        Returns:
            bool: True if the command succeeded, False otherwise.
        """
        return await self.hw_device.set_dac(
            channel=int(channel), volts=value
        )


class SwitchBoxADC(AnalogDigitalSignal):

    def __init__(self, name: str, hw_device: "SwitchBoxMPIKG"):

        super().__init__(name=name, hw_device=hw_device)

        self.add_api_route("/read_all", self.read_all, methods=["GET"])

    async def read(self, channel: str) -> float:  # type:ignore[override]
        """
        Read ADC (Analog  Digital Channels) channel (1 to 8).

        Returns:
            voltage value.
        """
        asw = await self.read_all()
        for key in asw.keys():
            if key[-1] == channel:
                return asw[key]
        logger.error(f"There is no channel '{channel} in ADC ports!'")
        return -1

    async def read_all(self) -> dict[str, float]:
        """
        Read all ADC (Analog Digital Channels) channels.

        Returns:
            dict[str, float]: Mapping of channel IDs (e.g. "ADC1", "ADC2") to measured
            voltage values.
        """
        self.hw_device: SwitchBoxMPIKG
        return await self.hw_device.get_adc()


class SwitchBoxRelay(Relay):

    def __init__(self, name: str, hw_device: "SwitchBoxMPIKG"):

        super().__init__(name=name, hw_device=hw_device)

        self.hw_device: SwitchBoxMPIKG

        self.add_api_route("/channel", self.read_channel, methods=["GET"])

        self.add_api_route("/channel", self.set_channel, methods=["PUT"])

        self.add_api_route("/read_all", self.get_all, methods=["GET"])

        self.add_api_route("/port", self.set_ports, methods=["PUT"])


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

    async def read_channel(self, channel: str) -> int | bool:
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
                - False → if the channel index is invalid.
        """
        ch = int(channel)
        asw = await self.get_all()
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
            return False
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
                in the same port.
                If false, all other channels in the port are reset to 0.
            switch_to_low_after (float, optional):
                If >0 and value=2, automatically switches the channel
                to 1 (half power) after the given delay in seconds.
                Useful to reduce heat dissipation.
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

    async def get_all(self) -> dict[str, list[int]]:
        """
        Query the relay states of all channels.

        Returns:
            dict[str, list[int]]: A dictionary mapping port IDs ("a", "b", "c", "d")
            to lists of 8 integers each.
            Each integer is the channel state:
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

    async def set_ports(
            self,
            values: str,
            switch_to_low_after: float = -1,
            port: str = "a"
    ):
        """
        Set the relay states of all 8 channels in a port.

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
