"""Flowchem components for generic NI-DAQmx analog I/O."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pint
from loguru import logger
from pint.errors import DimensionalityError, UndefinedUnitError

from flowchem import ureg
from flowchem.components.reachability import ReachabilityStatus
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

    async def is_reachable(self) -> ReachabilityStatus:
        """Return ONLINE if the NI-DAQmx analog input task responds."""
        try:
            await self.read_all()
            return ReachabilityStatus.ONLINE
        except Exception:
            return ReachabilityStatus.OFFLINE


class NIDAQAnalogOutput(MultiChannelDAC):
    """Multi-channel DAC component for NI-DAQmx analog outputs."""

    hw_device: NIDAQAnalogIO

    async def read(self, channel: str) -> float:  # type: ignore[override]
        """Return the cached analog output setpoint in volts."""
        return self.hw_device.read_dac(channel)

    async def is_reachable(self) -> ReachabilityStatus:
        """Return OFFLINE if the NI-DAQmx analog output task failed to initialise, UNKNOWN otherwise.

        The DAC task existing confirms initialisation succeeded, but there is no
        live hardware probe to confirm the physical device is still responding.
        """
        if self.hw_device._dac_task is None:
            return ReachabilityStatus.OFFLINE
        return ReachabilityStatus.UNKNOWN

    async def set(self, channel: str = "1", value: str = "0 V") -> bool:  # type: ignore[override]
        """Set one analog output channel."""
        try:
            parsed_value: pint.Quantity = ureg.Quantity(value)
        except (UndefinedUnitError, DimensionalityError, Exception) as error:
            logger.error(f"Invalid DAC value '{value}' for channel {channel}: {error}")
            return False
        try:
            return await self.hw_device.set_dac(channel, parsed_value)
        except ValueError as error:
            logger.error(str(error))
            return False
