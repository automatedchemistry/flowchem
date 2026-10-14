"""
Control module for the USB bubble detector ("FlowControl", ESP32 board, up to 6 optical sensors).

### Serial protocol (probed 2026-10-14, firmware "FlowControl ver 1.0 from 07.10.2026")

* 115200 8N1, USB VID:PID 1A86:55D4 (WCH CH9102).
* Commands end with ``\\r``. A command that never sees ``\\r`` stays in the firmware's command buffer;
  after ~80-90 characters the board crashes (``assert failed: xQueueSemaphoreTake``) and reboots.
* The device PUSHES a data frame every ``interval`` ms and immediately on any state change::

      STATES:3,3,3 | VALUES:2118,2086,2112

  Frames and command replies can interleave inside one line, so every frame is validated.
* State codes: 0 = inactive slot, 1 = empty tube, 2 = bubble, 3 = liquid.
* Replies are human-readable text, one line each:

| **Command**          | **Reply**                                                      |
|----------------------|----------------------------------------------------------------|
| get ver              | FlowControl ver 1.0 from 07.10.2026                            |
| get sernum           | Seriennummer is set to: 000-0000                               |
| get baud             | Baud rate is set to: 115200                                    |
| get sensors          | Number of active sensors is: 3                                 |
| get interval         | Send interval is set to: 20000                                 |
| get displaytime      | Display timeout is set to: 30                                  |
| get fluid:x          | Calibration value for sensor 1 is: 998                         |
| get empty:x          | Calibration value for sensor 1 is: 3600                        |
| get states / values  | 6 lines ``Sensor N: v``                                        |
| get claib (sic)      | header + 6 lines ``Sensor N: Fluid = 998, Empty = 3600``       |
| get bubble           | 6 lines, the first prefixed ``Current bubble ... is: Sensor 1: 70`` |
| set xxx:...          | echo of the new value, e.g. ``Send interval is set to: 20000``  |
| (unknown command)    | ERROR:GET BOGUS                                                |
| (bad index)          | Invalid sensor index! Must be between 1 and 6.                 |

Firmware bugs at the time of writing: ``get sensor:x`` and ``set bubble:x:y`` reject every index.
The firmware help says settings need a ``reset`` to take effect; this driver never resets on its own.

Not exposed on purpose: ``set baud`` (connection would be lost), ``eeprom-init`` (wipes calibration),
``debug`` (its output would mix with the data lines).

### Example configuration::

    [device.bubble-detector]
    type = "BubbleDetector"
    port = "COM3"
"""

from __future__ import annotations

import asyncio
import re
import threading
import time
from dataclasses import dataclass, field

import serial
from loguru import logger

from flowchem.components.device_info import DeviceInfo
from flowchem.devices.custom.bubble_detector_component import (
    BubbleDetectorChannel,
    BubbleDetectorControl,
)
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.utils.people import miguel

MAX_SENSORS = 6
STATE_NAMES = {0: "inactive", 1: "empty", 2: "bubble", 3: "liquid"}
STATE_BUBBLE = 2
STATE_EMPTY = 1

FRAME_RE = re.compile(r"^STATES:([\d,]+) \| VALUES:([\d,]+)$")
SENSOR_LINE_RE = re.compile(r"Sensor (\d+): (\d+)$")
CALIB_LINE_RE = re.compile(r"Sensor (\d+): Fluid = (\d+), Empty = (\d+)")
ERROR_PREFIXES = ("ERROR", "Invalid")

REPLY_TIMEOUT = 3.0  # s, for a whole (possibly multi-line) reply
BOOT_SETTLE = 2.5  # s, the board may reboot when the port is opened
RESET_TIMEOUT = 10.0  # s, to see the firmware banner again after "reset"
RECONNECT_DELAY = 2.0  # s


class BubbleDetectorError(Exception):
    """Communication or command error with the bubble detector."""


@dataclass
class ChannelStatus:
    """Latest reading of one sensor plus the events latched since the last clear."""

    state: int | None = None
    value: int | None = None
    updated_at: float | None = None
    last_change_at: float | None = None
    bubble_count: int = 0
    empty_count: int = 0
    last_bubble_at: float | None = None
    last_empty_at: float | None = None
    events_cleared_at: float = field(default_factory=time.time)

    def update(self, state: int, value: int, t: float):
        if state != self.state:
            # Count entries into a state, so a bubble lasting several frames counts once
            if state == STATE_BUBBLE:
                self.bubble_count += 1
                self.last_bubble_at = t
            elif state == STATE_EMPTY:
                self.empty_count += 1
                self.last_empty_at = t
            if self.state is not None:
                self.last_change_at = t
        self.state = state
        self.value = value
        self.updated_at = t

    def clear_events(self):
        self.bubble_count = 0
        self.empty_count = 0
        self.last_bubble_at = None
        self.last_empty_at = None
        self.events_cleared_at = time.time()

    def as_dict(self) -> dict:
        now = time.time()
        return {
            "state": self.state,
            "state_name": STATE_NAMES.get(self.state, "unknown"),
            "bubble_detected": self.state == STATE_BUBBLE,
            "value": self.value,
            "age_s": None if self.updated_at is None else round(now - self.updated_at, 2),
            "bubble_count": self.bubble_count,
            "empty_count": self.empty_count,
            "last_bubble_at": self.last_bubble_at,
            "last_empty_at": self.last_empty_at,
            "events_cleared_at": self.events_cleared_at,
        }


class BubbleDetector(FlowchemDevice):
    """USB bubble detector with up to 6 optical sensors (push-mode serial device)."""

    DEFAULT_CONFIG = {
        "baudrate": 115200,
        "bytesize": serial.EIGHTBITS,
        "parity": serial.PARITY_NONE,
        "stopbits": serial.STOPBITS_ONE,
        "timeout": 0.5,
    }

    def __init__(self, port: str, name: str = "", **serial_kwargs) -> None:
        super().__init__(name)
        self.port = port
        self.serial_config = self.DEFAULT_CONFIG | serial_kwargs
        self.device_info = DeviceInfo(
            authors=[miguel],
            manufacturer="Custom",
            model="FlowControl bubble detector",
        )
        self._serial: serial.Serial | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._replies: asyncio.Queue[str] | None = None
        self._command_lock: asyncio.Lock | None = None
        self._reader_thread: threading.Thread | None = None
        self._status_lock = threading.Lock()
        self.channels: list[ChannelStatus] = []
        self.n_sensors = 0
        self.interval_ms: int | None = None
        self.last_frame_at: float | None = None
        self.last_update_at: float | None = None  # last frame OR poll
        self.connected = False

    @classmethod
    def from_config(cls, port: str, name: str = "", **serial_kwargs):
        return cls(port=port, name=name, **serial_kwargs)

    # ------------------------------------------------------------------ connection

    def _open_serial(self) -> serial.Serial:
        ser = serial.Serial()
        ser.port = self.port
        for key, value in self.serial_config.items():
            setattr(ser, key, value)
        # Keep DTR/RTS low: toggling them is what triggers the ESP32 auto-reset circuit
        ser.dtr = False
        ser.rts = False
        ser.open()
        return ser

    async def initialize(self):
        self._loop = asyncio.get_running_loop()
        self._replies = asyncio.Queue()
        self._command_lock = asyncio.Lock()
        try:
            self._serial = self._open_serial()
        except serial.SerialException as e:
            raise ConnectionError(f"Cannot open bubble detector on {self.port}: {e}") from e
        self.connected = True

        self._reader_thread = threading.Thread(
            target=self._reader_loop, name=f"{self.name}-reader", daemon=True
        )
        self._reader_thread.start()

        # Let a possible boot finish, then drop whatever the board printed meanwhile
        await asyncio.sleep(BOOT_SETTLE)
        self._drain_replies()

        try:
            self.device_info.version = await self._query_line("get ver")
        except BubbleDetectorError:
            # One retry: the first command can collide with the end of a boot
            await asyncio.sleep(1)
            self.device_info.version = await self._query_line("get ver")
        self.device_info.serial_number = _after_colon(await self._query_line("get sernum"))
        self.n_sensors = await self.get_active_sensors()
        self.interval_ms = await self.get_interval()
        self.channels = [ChannelStatus() for _ in range(self.n_sensors)]

        # Seed the status so routes have data before the first pushed frame
        await self.poll_states()

        self.components.append(BubbleDetectorControl("control", self))
        self.components.extend(
            BubbleDetectorChannel(f"sensor-{i + 1}", self, channel=i + 1)
            for i in range(self.n_sensors)
        )
        logger.info(
            f"Connected to bubble detector '{self.device_info.version}' on {self.port} "
            f"({self.n_sensors} active sensors, send interval {self.interval_ms} ms)"
        )

    def _reader_loop(self):
        """Background thread: route data frames to the status, everything else to the reply queue."""
        while True:
            try:
                if self._serial is None or not self._serial.is_open:
                    raise serial.SerialException("port closed")
                raw = self._serial.readline()
            except (serial.SerialException, OSError) as e:
                self.connected = False
                logger.error(f"Bubble detector on {self.port}: serial error '{e}', reconnecting...")
                self._reconnect()
                continue
            if not raw:
                continue
            line = raw.decode("ascii", errors="ignore").strip()
            if not line:
                continue
            if "STATES:" in line:
                self._handle_frame(line)
            else:
                self._loop.call_soon_threadsafe(self._replies.put_nowait, line)

    def _reconnect(self):
        try:
            if self._serial is not None:
                self._serial.close()
        except Exception:
            pass
        while True:
            time.sleep(RECONNECT_DELAY)
            try:
                self._serial = self._open_serial()
            except serial.SerialException:
                continue
            self.connected = True
            logger.info(f"Bubble detector on {self.port}: reconnected")
            return

    def _handle_frame(self, line: str):
        # Interleaved output looks like "STATES:3STATES:3,3,3 | VALUES:...": keep the last frame start
        candidate = line[line.rfind("STATES:"):]
        match = FRAME_RE.match(candidate)
        if not match:
            logger.debug(f"Bubble detector: discarded malformed frame '{line}'")
            return
        states = [int(s) for s in match.group(1).split(",") if s]
        values = [int(v) for v in match.group(2).split(",") if v]
        if len(states) != len(values) or len(states) < len(self.channels):
            logger.debug(f"Bubble detector: discarded inconsistent frame '{line}'")
            return
        self._apply_readings(states, values)
        self.last_frame_at = time.time()

    def _apply_readings(self, states: list[int], values: list[int]):
        t = time.time()
        with self._status_lock:
            for channel, state, value in zip(self.channels, states, values):
                if state not in STATE_NAMES:
                    logger.warning(f"Bubble detector: unknown state code {state}")
                previous = channel.state
                channel.update(state, value, t)
                if state == STATE_BUBBLE and previous != STATE_BUBBLE:
                    logger.info(f"Bubble detector: bubble on sensor {self.channels.index(channel) + 1}")
            self.last_update_at = t

    # ------------------------------------------------------------------ commands

    def _drain_replies(self):
        while not self._replies.empty():
            self._replies.get_nowait()

    async def _command(self, command: str, n_lines: int = 1) -> list[str]:
        """Send one command and collect its reply lines."""
        if not self.connected:
            raise BubbleDetectorError(f"Bubble detector on {self.port} is not connected")
        async with self._command_lock:
            self._drain_replies()
            try:
                await asyncio.to_thread(self._serial.write, f"{command}\r".encode("ascii"))
            except serial.SerialException as e:
                raise BubbleDetectorError(f"Write of '{command}' failed: {e}") from e
            lines: list[str] = []
            deadline = self._loop.time() + REPLY_TIMEOUT
            while len(lines) < n_lines:
                remaining = deadline - self._loop.time()
                if remaining <= 0:
                    raise BubbleDetectorError(
                        f"No (complete) reply to '{command}': got {lines}"
                    )
                try:
                    line = await asyncio.wait_for(self._replies.get(), remaining)
                except asyncio.TimeoutError:
                    continue
                if line.startswith(ERROR_PREFIXES):
                    raise BubbleDetectorError(f"'{command}' rejected by device: {line}")
                lines.append(line)
        logger.debug(f"Bubble detector: '{command}' -> {lines}")
        return lines

    async def _query_line(self, command: str) -> str:
        return (await self._command(command))[0]

    async def _query_int(self, command: str) -> int:
        return _last_int(await self._query_line(command))

    async def _set_int(self, command: str, value: int) -> int:
        reply = _last_int(await self._query_line(command))
        if reply != value:
            raise BubbleDetectorError(f"'{command}' echoed {reply} instead of {value}")
        return reply

    @staticmethod
    def _check_channel(channel: int):
        if not 1 <= channel <= MAX_SENSORS:
            raise BubbleDetectorError(f"Sensor index must be 1-{MAX_SENSORS}, got {channel}")

    # ------------------------------------------------------------------ readings

    def is_stale(self) -> bool:
        """True if neither a frame nor a poll updated the readings for more than two send intervals."""
        if self.last_update_at is None:
            return True
        limit = 2 * (self.interval_ms or 20000) / 1000 + 5
        return time.time() - self.last_update_at > limit

    async def poll_states(self):
        """Ask the device for states and values instead of waiting for a pushed frame."""
        states = _sensor_lines(await self._command("get states", MAX_SENSORS))
        values = _sensor_lines(await self._command("get values", MAX_SENSORS))
        self._apply_readings(states[: self.n_sensors], values[: self.n_sensors])

    async def _fresh(self):
        if self.is_stale():
            logger.warning("Bubble detector: no recent frame, polling states")
            await self.poll_states()

    async def get_channel(self, channel: int) -> dict:
        await self._fresh()
        with self._status_lock:
            return self.channels[channel - 1].as_dict()

    async def get_all(self) -> dict:
        await self._fresh()
        with self._status_lock:
            return {
                "connected": self.connected,
                "last_frame_age_s": None
                if self.last_frame_at is None
                else round(time.time() - self.last_frame_at, 2),
                "interval_ms": self.interval_ms,
                "bubble_detected": any(c.state == STATE_BUBBLE for c in self.channels),
                "sensors": {
                    f"sensor-{i + 1}": c.as_dict() for i, c in enumerate(self.channels)
                },
            }

    def clear_events(self, channel: int | None = None):
        with self._status_lock:
            targets = self.channels if channel is None else [self.channels[channel - 1]]
            for c in targets:
                c.clear_events()

    # ------------------------------------------------------------------ settings

    async def get_info(self) -> dict:
        return {
            "version": await self._query_line("get ver"),
            "serial_number": _after_colon(await self._query_line("get sernum")),
            "baudrate": await self._query_int("get baud"),
            "port": self.port,
        }

    async def get_interval(self) -> int:
        return await self._query_int("get interval")

    async def set_interval(self, interval_ms: int) -> int:
        if interval_ms < 100:
            raise BubbleDetectorError("Send interval must be at least 100 ms")
        self.interval_ms = await self._set_int(f"set interval:{interval_ms}", interval_ms)
        return self.interval_ms

    async def get_active_sensors(self) -> int:
        return await self._query_int("get sensors")

    async def set_active_sensors(self, n: int) -> int:
        if not 1 <= n <= MAX_SENSORS:
            raise BubbleDetectorError(f"Active sensors must be 1-{MAX_SENSORS}")
        reply = await self._set_int(f"set sensors:{n}", n)
        if reply != self.n_sensors:
            logger.warning(
                f"Bubble detector: active sensors changed to {reply}; reset the device and "
                f"restart flowchem to get the matching sensor components"
            )
        return reply

    async def get_display_time(self) -> int:
        return await self._query_int("get displaytime")

    async def set_display_time(self, seconds: int) -> int:
        if seconds < 0:
            raise BubbleDetectorError("Display time must be >= 0 s")
        return await self._set_int(f"set displaytime:{seconds}", seconds)

    async def get_calibration(self) -> dict:
        lines = await self._command("get claib", MAX_SENSORS + 1)
        calibration = {}
        for line in lines:
            if match := CALIB_LINE_RE.search(line):
                calibration[f"sensor-{match.group(1)}"] = {
                    "fluid": int(match.group(2)),
                    "empty": int(match.group(3)),
                }
        return calibration

    async def get_fluid_calibration(self, channel: int) -> int:
        self._check_channel(channel)
        return await self._query_int(f"get fluid:{channel}")

    async def set_fluid_calibration(self, channel: int, value: int) -> int:
        self._check_channel(channel)
        return await self._set_int(f"set fluid:{channel}:{value}", value)

    async def get_empty_calibration(self, channel: int) -> int:
        self._check_channel(channel)
        return await self._query_int(f"get empty:{channel}")

    async def set_empty_calibration(self, channel: int, value: int) -> int:
        self._check_channel(channel)
        return await self._set_int(f"set empty:{channel}:{value}", value)

    async def get_bubble_thresholds(self) -> list[int]:
        return _sensor_lines(await self._command("get bubble", MAX_SENSORS))

    async def set_bubble_threshold(self, channel: int, value: int) -> int:
        # NB: rejected by firmware 1.0 (07.10.2026) for every index - firmware bug
        self._check_channel(channel)
        return await self._set_int(f"set bubble:{channel}:{value}", value)

    async def reset(self) -> bool:
        """Soft-reset the device and wait for its banner. Latched events are kept."""
        async with self._command_lock:
            self._drain_replies()
            await asyncio.to_thread(self._serial.write, b"reset\r")
            got_banner = False
            deadline = self._loop.time() + RESET_TIMEOUT
            while (remaining := deadline - self._loop.time()) > 0:
                try:
                    line = await asyncio.wait_for(self._replies.get(), remaining)
                except asyncio.TimeoutError:
                    break
                if line.startswith("FlowControl ver"):
                    self.device_info.version = line
                    got_banner = True
                    break
        if not got_banner:
            logger.warning("Bubble detector: no firmware banner after reset")
        await asyncio.sleep(1)
        self.interval_ms = await self.get_interval()
        await self.poll_states()
        return True


def _last_int(line: str) -> int:
    numbers = re.findall(r"\d+", line)
    if not numbers:
        raise BubbleDetectorError(f"No number in reply '{line}'")
    return int(numbers[-1])


def _after_colon(line: str) -> str:
    return line.split(":", 1)[-1].strip()


def _sensor_lines(lines: list[str]) -> list[int]:
    """Parse 'Sensor N: v' lines into a list ordered by N."""
    parsed = {}
    for line in lines:
        if match := SENSOR_LINE_RE.search(line):
            parsed[int(match.group(1))] = int(match.group(2))
    if sorted(parsed) != list(range(1, MAX_SENSORS + 1)):
        raise BubbleDetectorError(f"Incomplete sensor list in reply {lines}")
    return [parsed[i] for i in range(1, MAX_SENSORS + 1)]
