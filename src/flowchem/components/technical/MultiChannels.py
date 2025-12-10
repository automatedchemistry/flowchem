from flowchem.components.technical.ADC import AnalogDigitalConverter
from flowchem.components.technical.DAC import DigitalAnalogConverter
from flowchem.components.technical.relay import Relay


class MultiChannelADC(AnalogDigitalConverter):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.add_api_route("/read_all", self.read_all, methods=["GET"])

    async def read(self, channel: str) -> float:  # type:ignore[override]
        """
        Read the current value of the signal.

        Args:
            channel: Identifier of the relay channel to be read.

        Returns:
            float: The measured or estimated signal value.
        """
        raise NotImplementedError

    async def read_all(self) -> dict[str, float]:
        """
        Read all ADC (Analog-to-Digital Converter) channels.

        Returns:
            dict[str, float]: Mapping of channel IDs (e.g. "ADC1", "ADC2") to measured
            voltage values in volts.
        """
        raise NotImplementedError


class MultiChannelDAC(DigitalAnalogConverter):

    async def read(self, channel: str) -> float:  # type:ignore[override]
        """
        Read the DAC output of a channel.

        Args:
            channel (str): DAC channel index.
        """
        raise NotImplementedError

    async def set(self, channel: str = "1", value: str = "0 V") -> bool:  # type:ignore[override]
        """
        Set the analog output value of a channel.

        Args:
            channel: The identifier or name of the channel to control.
            value: The analog value to set (e.g., voltage in volts).

        Returns:
            True if the value was accepted and applied successfully.
        """
        raise NotImplementedError


class MultiChannelRelay(Relay):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.add_api_route("/multiple_channel", self.switch_multiple_channel, methods=["PUT"])

        self.add_api_route("/channels_set_point", self.read_channels_set_point, methods=["GET"])

    async def power_on(self, channel: str) -> bool:  # type:ignore[override]
        """
        Switch a relay channel ON.

        Args:
            channel: Identifier of the relay channel to be switched.

        Returns:
            True if the channel was successfully switched on, False otherwise
        """
        raise NotImplementedError

    async def power_off(self, channel: str) -> bool:  # type:ignore[override]
        """
        Switch a relay channel OFF.

        Args:
            channel: Identifier of the relay channel to be switched.

        Returns:
            True if the channel was successfully switched off, False otherwise
        """
        raise NotImplementedError

    async def is_on(self, channel: str) -> bool:  # type:ignore[override]
        """
        Check whether the relay is currently ON.

        This asynchronous method queries the current state of the relay channel
        to determine if it is active (ON) or inactive (OFF).

        Returns:
            bool: True if the relay is ON, False if it is OFF.
        """
        value = await self.read_channel_set_point(channel)
        if value:
            return value > 0
        else:
            raise Exception(f"The component {self.name} from {self.hw_device.name} has not channel: {channel}!!")


    async def switch_multiple_channel(self, values: str):
        """
        Set the relay states of all channels.

        Channel states:
            * 0 → OFF
            * 1 → ON

        Args:
            values (str): List of up to 'n' integers (0, 1, or 2).
                - Example: "00010012"
                - If shorter than 'n', remaining channels are set to 0.
                - If longer than 'n', extra values are ignored.
                where 'n' is the number of channel
                Observation: Any value greater than 0 will be considered as ON
        Returns:
            bool: True if the device acknowledged the command, False otherwise.
        """
        raise NotImplementedError

    async def read_channel_set_point(self, channel: str) -> int | None:
        """
        Read the current relay state of a single channel.

        Channel states:
            * 0 → OFF
            * 1 → ON

        Args:
            channel (str): Relay channel index (1–n).
            where 'n' is the number of channel

        Returns:
            int | bool:
                - 0, 1 → valid relay state.
                - None → if the channel index is invalid.
        """
        raise NotImplementedError

    async def read_channels_set_point(self) -> list[int]:
        """
        Read the current relay state of a single channel.

        Channel states:
            * 0 → OFF
            * 1 → ON

        Returns:
            list[int]:
                - 0, 1 → valid relay state.
        """
        raise NotImplementedError



