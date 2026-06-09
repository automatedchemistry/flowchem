"""Flowchem components for generic NI-DAQmx analog I/O."""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger
from pint.errors import DimensionalityError, UndefinedUnitError

from flowchem import ureg
from flowchem.components.technical.MultiChannels import MultiChannelADC, MultiChannelDAC

if TYPE_CHECKING:
    from .nidaq_analog_io import NIDAQAnalogIO


class NIDAQAnalogInput(MultiChannelADC):
    """Multi-channel ADC component for NI-DAQmx analog inputs."""

    hw_device: NIDAQAnalogIO

    async def read(self, channel: str) -> float:  # type: ignore[override]
        """Read one analog input channel in volts."""
        return await self.hw_device.read_adc(channel)

    async def read_all(self) -> dict[str, float]:
        """Read all configured analog input channels in volts."""
        return await self.hw_device.read_all_adc()


class NIDAQAnalogOutput(MultiChannelDAC):
    """Multi-channel DAC component for NI-DAQmx analog outputs."""

    hw_device: NIDAQAnalogIO

    async def read(self, channel: str) -> float:  # type: ignore[override]
        """Return the cached analog output setpoint in volts."""
        return self.hw_device.read_dac(channel)

    async def set(self, channel: str = "1", value: str = "0 V") -> bool:  # type: ignore[override]
        """Set one analog output channel."""
        try:
            parsed_value = ureg.Quantity(value)
        except (UndefinedUnitError, DimensionalityError, Exception) as error:
            logger.error(f"Invalid DAC value '{value}' for channel {channel}: {error}")
            return False
        try:
            return await self.hw_device.set_dac(channel, parsed_value)
        except ValueError as error:
            logger.error(str(error))
            return False
