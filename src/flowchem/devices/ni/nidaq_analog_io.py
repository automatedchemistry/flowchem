"""Generic NI-DAQmx analog input/output device."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import Any

import pint
from loguru import logger

from flowchem import ureg
from flowchem.components.device_info import DeviceInfo
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.ni._common import (
    channel_sort_key,
    import_nidaqmx,
    physical_channel_names,
    resolve_ni_device,
    terminal_config_from_string,
)
from flowchem.devices.ni.nidaq_analog_io_component import (
    NIDAQAnalogInput,
    NIDAQAnalogOutput,
)
from flowchem.utils.exceptions import InvalidConfigurationError
from flowchem.utils.people import samuel_saraiva


class NIDAQAnalogIO(FlowchemDevice):
    """Generic NI-DAQmx analog I/O device exposing ADC and DAC components."""

    def __init__(
        self,
        module: str,
        adc_channel_names: Sequence[str] | None = None,
        dac_channel_names: Sequence[str] | None = None,
        adc_task: Any | None = None,
        dac_task: Any | None = None,
        name: str = "",
        dac_range: tuple[float, float] | None = None,
        serial_number: str | int = "unknown",
    ) -> None:
        super().__init__(name)
        self.module = module
        self._adc_channel_names = list(adc_channel_names or [])
        self._dac_channel_names = list(dac_channel_names or [])
        self._adc_task = adc_task
        self._dac_task = dac_task
        self._dac_range = dac_range
        self._dac_setpoints = [0.0] * len(self._dac_channel_names)
        self._adc_lock = asyncio.Lock()
        self._dac_lock = asyncio.Lock()

        if not self._adc_channel_names and not self._dac_channel_names:
            raise InvalidConfigurationError(
                "NIDAQAnalogIO requires at least one ADC or DAC channel."
            )

        self.device_info = DeviceInfo(
            authors=[samuel_saraiva],
            manufacturer="National Instruments",
            model="NI-DAQmx analog I/O",
            serial_number=serial_number,
            additional_info={
                "module": module,
                "adc_channels": self._adc_channel_names,
                "dac_channels": self._dac_channel_names,
            },
        )

    @classmethod
    def from_config(
        cls,
        module: str | None = None,
        adc_channels: Sequence[str] | None = None,
        dac_channels: Sequence[str] | None = None,
        adc_range: Sequence[str] | None = None,
        dac_range: Sequence[str] | None = None,
        terminal_config: str | None = "DEFAULT",
        name: str = "",
    ) -> "NIDAQAnalogIO":
        """Create a generic NI analog I/O device from Flowchem TOML configuration."""
        nidaqmx, system, constants = import_nidaqmx()

        module_device = None
        module_name = module or ""
        if module is not None:
            module_device = resolve_ni_device(system, module, device_label="NI analog I/O device")
            module_name = module_device.name

        adc_channel_names = list(adc_channels or [])
        dac_channel_names = list(dac_channels or [])
        if module_device is not None:
            if not adc_channel_names:
                adc_channel_names = cls._discover_adc_channels(module_device)
            if not dac_channel_names:
                dac_channel_names = cls._discover_dac_channels(module_device)

        if not module_name:
            module_name = cls._infer_module_name(adc_channel_names, dac_channel_names)

        adc_task = None
        if adc_channel_names:
            adc_task = nidaqmx.Task()
            adc_kwargs = _optional_range_kwargs(adc_range)
            terminal = terminal_config_from_string(constants, terminal_config)
            if terminal is not None:
                adc_kwargs["terminal_config"] = terminal
            adc_task.ai_channels.add_ai_voltage_chan(
                ",".join(adc_channel_names),
                **adc_kwargs,
            )

        dac_task = None
        if dac_channel_names:
            dac_task = nidaqmx.Task()
            dac_kwargs = _optional_range_kwargs(dac_range)
            dac_task.ao_channels.add_ao_voltage_chan(
                ",".join(dac_channel_names),
                **dac_kwargs,
            )

        return cls(
            module=module_name,
            adc_channel_names=adc_channel_names,
            dac_channel_names=dac_channel_names,
            adc_task=adc_task,
            dac_task=dac_task,
            name=name,
            dac_range=_range_to_volts(dac_range),
            serial_number=getattr(module_device, "serial_num", "unknown"),
        )

    async def initialize(self) -> None:
        """Register ADC and DAC components for configured channels."""
        if self._adc_channel_names:
            self.components.append(NIDAQAnalogInput("adc", self))
        if self._dac_channel_names:
            self.components.append(NIDAQAnalogOutput("dac", self))
        logger.info(
            f"Connected to NI analog I/O '{self.module}' with "
            f"{len(self._adc_channel_names)} ADC channel(s) and "
            f"{len(self._dac_channel_names)} DAC channel(s)."
        )

    async def read_adc(self, channel: str | int) -> float:
        """Read one ADC channel in volts."""
        index = self._adc_channel_index(channel)
        values = await self._read_adc_values()
        return values[index]

    async def read_all_adc(self) -> dict[str, float]:
        """Read all ADC channels in volts."""
        values = await self._read_adc_values()
        return {
            f"ADC{index + 1}": value
            for index, value in enumerate(values)
        }

    async def set_dac(self, channel: str | int, value: pint.Quantity) -> bool:
        """Set one DAC channel from a unit-aware value."""
        index = self._dac_channel_index(channel)
        volts = float(value.to("V").magnitude)
        if self._dac_range is not None and not self._dac_range[0] <= volts <= self._dac_range[1]:
            raise ValueError(
                f"DAC channel {channel} setpoint {volts} V is outside configured range "
                f"{self._dac_range[0]} to {self._dac_range[1]} V."
            )

        next_setpoints = self._dac_setpoints.copy()
        next_setpoints[index] = volts
        async with self._dac_lock:
            if self._dac_task is None:
                raise ValueError("No DAC channels are configured.")
            write_value: float | list[float]
            write_value = next_setpoints[0] if len(next_setpoints) == 1 else next_setpoints
            try:
                await asyncio.to_thread(self._dac_task.write, write_value, auto_start=True)
            except Exception:
                logger.exception(f"Could not write DAC state to NI module '{self.module}'.")
                return False
            self._dac_setpoints = next_setpoints
        return True

    def read_dac(self, channel: str | int) -> float:
        """Return cached DAC setpoint in volts."""
        return self._dac_setpoints[self._dac_channel_index(channel)]

    def close(self) -> None:
        """Close underlying NI-DAQmx tasks."""
        for task in (self._adc_task, self._dac_task):
            if task is None:
                continue
            try:
                task.close()
            except AttributeError:
                continue

    def __del__(self) -> None:
        self.close()

    async def _read_adc_values(self) -> list[float]:
        if self._adc_task is None:
            raise ValueError("No ADC channels are configured.")
        async with self._adc_lock:
            values = await asyncio.to_thread(self._adc_task.read)
        return _normalize_float_values(values, len(self._adc_channel_names))

    def _adc_channel_index(self, channel: str | int) -> int:
        return _channel_index(channel, len(self._adc_channel_names), "ADC")

    def _dac_channel_index(self, channel: str | int) -> int:
        return _channel_index(channel, len(self._dac_channel_names), "DAC")

    @staticmethod
    def _discover_adc_channels(module_device: Any) -> list[str]:
        return sorted(
            physical_channel_names(getattr(module_device, "ai_physical_chans", ())),
            key=channel_sort_key,
        )

    @staticmethod
    def _discover_dac_channels(module_device: Any) -> list[str]:
        return sorted(
            physical_channel_names(getattr(module_device, "ao_physical_chans", ())),
            key=channel_sort_key,
        )

    @staticmethod
    def _infer_module_name(
        adc_channel_names: Sequence[str],
        dac_channel_names: Sequence[str],
    ) -> str:
        all_channels = [*adc_channel_names, *dac_channel_names]
        if not all_channels:
            raise InvalidConfigurationError(
                "NIDAQAnalogIO requires a 'module' or explicit adc_channels/dac_channels."
            )
        return all_channels[0].split("/", 1)[0]


def _channel_index(channel: str | int, max_channel: int, label: str) -> int:
    if max_channel <= 0:
        raise ValueError(f"No {label} channels are configured.")
    try:
        channel_number = int(channel)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} channel must be an integer from 1 to {max_channel}.") from error
    if not 1 <= channel_number <= max_channel:
        raise ValueError(f"{label} channel must be between 1 and {max_channel}.")
    return channel_number - 1


def _normalize_float_values(values: Any, expected_count: int) -> list[float]:
    if isinstance(values, (float, int)):
        values = [values]
    elif not isinstance(values, list):
        try:
            values = list(values)
        except TypeError:
            values = [values]
    if len(values) != expected_count:
        raise ValueError(f"Expected {expected_count} ADC values, got {len(values)}.")
    return [float(value) for value in values]


def _optional_range_kwargs(configured_range: Sequence[str] | None) -> dict[str, float]:
    voltage_range = _range_to_volts(configured_range)
    if voltage_range is None:
        return {}
    return {"min_val": voltage_range[0], "max_val": voltage_range[1]}


def _range_to_volts(configured_range: Sequence[str] | None) -> tuple[float, float] | None:
    if configured_range is None:
        return None
    if len(configured_range) != 2:
        raise InvalidConfigurationError("Analog channel ranges must have exactly two values.")
    lower = float(ureg.Quantity(configured_range[0]).to("V").magnitude)
    upper = float(ureg.Quantity(configured_range[1]).to("V").magnitude)
    if lower >= upper:
        raise InvalidConfigurationError("Analog channel range lower bound must be smaller than upper bound.")
    return lower, upper
