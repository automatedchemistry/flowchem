"""Control an NI-6519 digital I/O device through NI-DAQmx."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import Any

from loguru import logger

from flowchem.components.device_info import DeviceInfo
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.ni._common import (
    import_nidaqmx,
    line_sort_key,
    physical_channel_names,
    resolve_ni_device,
)
from flowchem.devices.ni.ni6519_component import NI6519DigitalInput, NI6519Relay
from flowchem.utils.exceptions import InvalidConfigurationError
from flowchem.utils.people import samuel_saraiva

NI6519_INPUT_CHANNEL_COUNT = 16
NI6519_OUTPUT_CHANNEL_COUNT = 16


class NI6519(FlowchemDevice):
    """NI-6519 16-input, 16-output industrial digital I/O device."""

    def __init__(
        self,
        module: str,
        input_task: Any,
        output_task: Any,
        name: str = "",
        reset_outputs_on_initialize: bool = True,
        input_line_names: Sequence[str] | None = None,
        output_line_names: Sequence[str] | None = None,
        serial_number: str | int = "unknown",
    ) -> None:
        super().__init__(name)
        self.module = module
        self._input_task = input_task
        self._output_task = output_task
        self.reset_outputs_on_initialize = reset_outputs_on_initialize
        self._input_line_names = (
            list(input_line_names) if input_line_names else self.default_input_line_names(module)
        )
        self._output_line_names = (
            list(output_line_names) if output_line_names else self.default_output_line_names(module)
        )
        self._output_channel_states = [False] * NI6519_OUTPUT_CHANNEL_COUNT
        self._input_lock = asyncio.Lock()
        self._output_lock = asyncio.Lock()

        if len(self._input_line_names) != NI6519_INPUT_CHANNEL_COUNT:
            raise InvalidConfigurationError(
                f"NI6519 requires {NI6519_INPUT_CHANNEL_COUNT} digital input lines, "
                f"got {len(self._input_line_names)} for module '{module}'.",
            )
        if len(self._output_line_names) != NI6519_OUTPUT_CHANNEL_COUNT:
            raise InvalidConfigurationError(
                f"NI6519 requires {NI6519_OUTPUT_CHANNEL_COUNT} digital output lines, "
                f"got {len(self._output_line_names)} for module '{module}'.",
            )

        self.device_info = DeviceInfo(
            authors=[samuel_saraiva],
            manufacturer="National Instruments",
            model="NI-6519",
            serial_number=serial_number,
            additional_info={
                "module": module,
                "digital_inputs": NI6519_INPUT_CHANNEL_COUNT,
                "digital_outputs": NI6519_OUTPUT_CHANNEL_COUNT,
                "input_ports": "P0/P1",
                "output_ports": "P2/P3",
                "output_type": "sinking digital output",
            },
        )

    @classmethod
    def from_config(
        cls,
        module: str | None = None,
        name: str = "",
        reset_outputs_on_initialize: bool = True,
    ) -> "NI6519":
        """Create an NI6519 from Flowchem TOML configuration."""
        nidaqmx, system, constants = import_nidaqmx()
        module_device = resolve_ni_device(
            system,
            module,
            product_fragment="6519",
            device_label="NI-6519",
        )
        module_name = module_device.name
        input_line_names = cls._discover_input_line_names(module_device, module_name)
        output_line_names = cls._discover_output_line_names(module_device, module_name)

        input_task = nidaqmx.Task()
        input_task.di_channels.add_di_chan(
            ",".join(input_line_names),
            line_grouping=constants.LineGrouping.CHAN_PER_LINE,
        )

        output_task = nidaqmx.Task()
        output_task.do_channels.add_do_chan(
            ",".join(output_line_names),
            line_grouping=constants.LineGrouping.CHAN_PER_LINE,
        )

        return cls(
            module=module_name,
            input_task=input_task,
            output_task=output_task,
            name=name,
            reset_outputs_on_initialize=reset_outputs_on_initialize,
            input_line_names=input_line_names,
            output_line_names=output_line_names,
            serial_number=getattr(module_device, "serial_num", "unknown"),
        )

    async def initialize(self) -> None:
        """Register digital input and relay components and optionally set outputs OFF."""
        if self.reset_outputs_on_initialize:
            initialized = await self.set_output_channels([False] * NI6519_OUTPUT_CHANNEL_COUNT)
            if not initialized:
                raise InvalidConfigurationError(
                    "Could not reset NI6519 output channels during initialization."
                )

        self.components.append(NI6519Relay("relay", self))
        self.components.append(NI6519DigitalInput("digital-input", self))
        logger.info(
            f"Connected to NI-6519 module '{self.module}' with "
            f"{NI6519_INPUT_CHANNEL_COUNT} digital inputs and "
            f"{NI6519_OUTPUT_CHANNEL_COUNT} digital outputs."
        )

    async def set_output_channel(self, channel: str | int, active: bool) -> bool:
        """Set one output channel active or inactive."""
        channel_index = self._output_channel_index(channel)
        next_states = self._output_channel_states.copy()
        next_states[channel_index] = active
        return await self.set_output_channels(next_states)

    async def set_output_channels(self, states: Sequence[bool]) -> bool:
        """Write all output states to the NI-6519 P2/P3 output bank."""
        if len(states) != NI6519_OUTPUT_CHANNEL_COUNT:
            raise ValueError(
                f"NI6519 expects {NI6519_OUTPUT_CHANNEL_COUNT} output states, got {len(states)}."
            )

        next_states = [bool(state) for state in states]
        async with self._output_lock:
            try:
                await asyncio.to_thread(self._output_task.write, next_states, auto_start=True)
            except Exception:
                logger.exception(
                    f"Could not write output state to NI6519 module '{self.module}'."
                )
                return False
            self._output_channel_states = next_states
        return True

    def get_output_channel_state(self, channel: str | int) -> bool:
        """Return the cached output state for one Flowchem output channel."""
        return self._output_channel_states[self._output_channel_index(channel)]

    def get_output_channel_states(self) -> list[bool]:
        """Return cached output states for all output channels."""
        return self._output_channel_states.copy()

    async def read_input_channel(self, channel: str | int) -> bool:
        """Read one NI-6519 input channel."""
        channel_index = self._input_channel_index(channel)
        return (await self.read_input_channels())[channel_index]

    async def read_input_channels(self) -> list[bool]:
        """Read all NI-6519 P0/P1 input bank states."""
        async with self._input_lock:
            values = await asyncio.to_thread(self._input_task.read)
        return self._normalize_read_values(values, NI6519_INPUT_CHANNEL_COUNT)

    def close(self) -> None:
        """Close underlying NI-DAQmx tasks."""
        for task in (self._input_task, self._output_task):
            try:
                task.close()
            except AttributeError:
                continue

    def __del__(self) -> None:
        self.close()

    @staticmethod
    def default_input_line_names(module: str) -> list[str]:
        """Return NI-6519 factory input lines P0/P1."""
        return [
            *(f"{module}/port0/line{index}" for index in range(8)),
            *(f"{module}/port1/line{index}" for index in range(8)),
        ]

    @staticmethod
    def default_output_line_names(module: str) -> list[str]:
        """Return NI-6519 factory output lines P2/P3."""
        return [
            *(f"{module}/port2/line{index}" for index in range(8)),
            *(f"{module}/port3/line{index}" for index in range(8)),
        ]

    @classmethod
    def _discover_input_line_names(cls, module_device: Any, module_name: str) -> list[str]:
        line_names = cls._filter_ports(
            physical_channel_names(getattr(module_device, "di_lines", ())),
            ports=("port0", "port1"),
        )
        if len(line_names) == NI6519_INPUT_CHANNEL_COUNT:
            return line_names
        logger.warning(
            f"Could not discover exactly {NI6519_INPUT_CHANNEL_COUNT} NI6519 DI lines for '{module_name}'. "
            "Using conventional port0/line0:7 and port1/line0:7 names.",
        )
        return cls.default_input_line_names(module_name)

    @classmethod
    def _discover_output_line_names(cls, module_device: Any, module_name: str) -> list[str]:
        line_names = cls._filter_ports(
            physical_channel_names(getattr(module_device, "do_lines", ())),
            ports=("port2", "port3"),
        )
        if len(line_names) == NI6519_OUTPUT_CHANNEL_COUNT:
            return line_names
        logger.warning(
            f"Could not discover exactly {NI6519_OUTPUT_CHANNEL_COUNT} NI6519 DO lines for '{module_name}'. "
            "Using conventional port2/line0:7 and port3/line0:7 names.",
        )
        return cls.default_output_line_names(module_name)

    @staticmethod
    def _filter_ports(line_names: Sequence[str], ports: tuple[str, ...]) -> list[str]:
        return sorted(
            [line_name for line_name in line_names if any(f"/{port}/" in line_name for port in ports)],
            key=line_sort_key,
        )

    @staticmethod
    def _input_channel_index(channel: str | int) -> int:
        return _channel_index(channel, NI6519_INPUT_CHANNEL_COUNT, "NI6519 input")

    @staticmethod
    def _output_channel_index(channel: str | int) -> int:
        return _channel_index(channel, NI6519_OUTPUT_CHANNEL_COUNT, "NI6519 output")

    @staticmethod
    def _normalize_read_values(values: Any, expected_count: int) -> list[bool]:
        if isinstance(values, bool):
            values = [values]
        elif not isinstance(values, list):
            try:
                values = list(values)
            except TypeError:
                values = [values]
        if len(values) != expected_count:
            raise ValueError(f"NI6519 expected {expected_count} input values, got {len(values)}.")
        return [bool(value) for value in values]


def _channel_index(channel: str | int, max_channel: int, label: str) -> int:
    try:
        channel_number = int(channel)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} channel must be an integer from 1 to {max_channel}.") from error
    if not 1 <= channel_number <= max_channel:
        raise ValueError(f"{label} channel must be between 1 and {max_channel}.")
    return channel_number - 1
