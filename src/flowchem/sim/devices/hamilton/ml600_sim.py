"""
Simulated Hamilton ML600 syringe pump.

Architecture
------------
``SimulatedHamiltonPumpIO`` replaces ``HamiltonPumpIO`` at the very bottom of
the stack.  It has no serial port; instead it maintains a small state machine
and returns the byte strings the real firmware would produce.  All layers
above it — ``ML600``, ``ML600Pump``, ``ML600LeftValve`` — run completely
unmodified.

``ML600Sim`` subclasses ``ML600`` and overrides only ``from_config`` and
``__init__`` to inject a ``SimulatedHamiltonPumpIO`` instead of a real one.

State machine
-------------
The sim tracks:

    syringe_position   int   Current syringe position in steps (0–48 000).
    valve_angle        int   Current valve angle in degrees (0–359).
    return_steps       int   Return steps setting (default 24 per hardware docs).
    firmware_version   str   Static firmware string returned for every ``U`` query.
    dual_syringe       bool  Whether to simulate a dual-syringe ML600.

All moves are instantaneous in simulation — ``REQUEST_DONE`` always returns
``"Y"`` and ``BUSY_STATUS`` always returns the idle bit pattern.  This lets
``wait_until_idle()`` return immediately, which is the correct behaviour for
software-level tests (we are testing logic, not timing).
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass

from loguru import logger

from flowchem.devices.hamilton.ml600 import (
    HamiltonPumpIO,
    ML600,
    PUMP_ADDRESS,
)
from flowchem.utils.exceptions import InvalidConfigurationError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ACK = chr(6)  # 0x06 — acknowledge
NAK = chr(21)  # 0x15 — negative acknowledge

# Reverse map: address letter → pump number (e.g. 'a' → 1)
ADDRESS_TO_NUM: dict[str, int] = {v: k for k, v in PUMP_ADDRESS.items()}


def _ack(payload: str = "") -> str:
    """Wrap a payload in an ACK response the way the real firmware does."""
    return f"{ACK}{payload}\r"


# ---------------------------------------------------------------------------
# Per-pump state
# ---------------------------------------------------------------------------


@dataclass
class _PumpState:
    """Mutable state for one pump address in the daisy chain."""

    syringe_position: int = 0  # steps, 0–48 000
    valve_angle: int = 0  # degrees, 0–359
    return_steps: int = 24  # default per hardware docs
    firmware_version: str = "NV01.02.3"


# ---------------------------------------------------------------------------
# Simulated IO layer
# ---------------------------------------------------------------------------


class SimulatedHamiltonPumpIO(HamiltonPumpIO):
    """
    Drop-in replacement for ``HamiltonPumpIO`` that needs no serial port.

    The constructor accepts the same positional signature as ``HamiltonPumpIO``
    (an ``aioserial.Serial`` object) but ignores it.  ``ML600Sim.from_config``
    passes ``None``; the parent ``__init__`` is deliberately NOT called so
    that no serial attributes are created.

    The public API surface used by ``ML600`` is:

        _assign_pump_address()           — called once during initialize()
        write_and_read_reply_async()     — normal single-command path
        multiple_write_and_read_reply_async() — dual-syringe compound commands
        _parse_response()                — inherited unchanged from HamiltonPumpIO

    ``_write_async`` and ``_read_reply_async`` are also overridden because
    ``_assign_pump_address`` calls them directly (outside the normal lock path).
    """

    def __init__(
        self,
        num_pumps: int = 1,
        dual_syringe: bool = False,
        firmware_version: str = "NV01.02.3",
    ) -> None:
        # Deliberately skip HamiltonPumpIO.__init__ — no serial port needed.
        self.num_pump_connected: int | None = None
        self._serial_lock = asyncio.Lock()

        self._num_pumps = num_pumps
        self._dual_syringe = dual_syringe
        self._firmware_version = firmware_version

        # One state object per pump address in the chain.
        self._state: dict[int, _PumpState] = {
            pump_num: _PumpState(firmware_version=firmware_version)
            for pump_num in range(1, num_pumps + 1)
        }

        # Buffer used by the raw _write/_read path (used during address assignment).
        self._raw_write_buf: list[bytes] = []
        self._raw_read_queue: list[str] = []

    # ------------------------------------------------------------------
    # Raw byte-level methods (used by _assign_pump_address)
    # ------------------------------------------------------------------

    async def _assign_pump_address(self) -> int:
        """
        Simulate the address-assignment probe used by the real pump IO layer.

        The parent implementation relies on ``self._serial.port`` for error
        reporting and assumes firmware enumeration replies contain ``"NV01"``.
        Neither assumption holds for the simulation layer, which has no serial
        object and allows custom firmware strings such as ``"NV02.00.0"``.
        """
        await self._write_async(b"1a\r")
        await self._read_reply_async()
        await self._write_async(b"1a\r")

        reply = await self._read_reply_async()
        if not reply or not reply.startswith("1"):
            raise InvalidConfigurationError("No simulated pump found in daisy chain.")

        last_pump = 0
        for pump_num, address in PUMP_ADDRESS.items():
            await self._write_async(f"{address}UR\r".encode("ascii"))
            if (await self._read_reply_async()).strip():
                last_pump = pump_num
            else:
                break

        logger.debug(f"[SIM] Found {last_pump} simulated pump(s) in daisy chain")
        return last_pump

    async def _write_async(self, command: bytes) -> None:
        """Receive a raw command and pre-compute the reply into the read queue."""
        logger.debug(f"[SIM] _write_async: {command!r}")
        self._raw_write_buf.append(command)
        reply = self._handle_raw_command(command)
        if reply is not None:
            self._raw_read_queue.append(reply)

    async def _read_reply_async(self) -> str:
        """Return the next pre-computed reply."""
        if self._raw_read_queue:
            reply = self._raw_read_queue.pop(0)
        else:
            reply = ""
        logger.debug(f"[SIM] _read_reply_async → {reply!r}")
        return reply

    def _handle_raw_command(self, command: bytes) -> str | None:
        """
        Handle raw byte commands sent during ``_assign_pump_address``.

        The real handshake sequence is:
            → b"1a\\r"          (sent twice; the first reply is discarded)
            ← "1NV01\\r"        (pump 1 present, "NV01" in response)
            → b"aUR\\r"         (enumerate pump at address 'a' = pump 1)
            ← "NV01.02.3\\r"    (firmware string contains "NV01" → pump found)
            → b"bUR\\r"         (enumerate pump at address 'b' = pump 2)
            ← "\\r"             (no pump → loop breaks)
        """
        cmd_str = command.decode("ascii", errors="replace")

        # Address-assignment probe: "1a\r"
        if cmd_str == "1a\r":
            return f"1{self._firmware_version}\r"

        # Per-address firmware query: "{letter}UR\r"
        match = re.fullmatch(r"([a-p])UR\r", cmd_str)
        if match:
            letter = match.group(1)
            pump_num = ADDRESS_TO_NUM.get(letter, 99)
            if pump_num in self._state:
                return f"{self._firmware_version}\r"
            else:
                return "\r"  # no pump at this address → enumerate loop breaks

        return None  # unknown raw command — no reply queued

    # ------------------------------------------------------------------
    # Normal command path (used by write_and_read_reply_async)
    # ------------------------------------------------------------------

    async def write_and_read_reply_async(self, command) -> str:
        """Parse the compiled command string and return a simulated ACK reply."""
        async with self._serial_lock:
            compiled = f"{command.compile()}\r"
            logger.debug(f"[SIM] write_and_read_reply_async: {compiled!r}")
            response = self._dispatch(compiled, command.target_pump_num)
            logger.debug(f"[SIM] → {response!r}")
            return self._parse_response(response)

    async def multiple_write_and_read_reply_async(self, command) -> str:
        """Handle compound (dual-syringe) commands — parse each sub-command."""
        async with self._serial_lock:
            if not isinstance(command, list):
                command = [command]

            command_compiled = ""
            for com in command:
                command_compiled += com._multiple_compile()
            full_compiled = com.multiple_compile(command_compiled)
            logger.debug(
                f"[SIM] multiple_write_and_read_reply_async: {full_compiled!r}"
            )

            # Apply each sub-command to the state; reply for the whole batch is a single ACK.
            pump_num = command[0].target_pump_num
            for com in command:
                single = f"{PUMP_ADDRESS[pump_num]}{com._multiple_compile()}R\r"
                self._dispatch(single, pump_num)

            response = _ack()
            logger.debug(f"[SIM] → {response!r}")
            return self._parse_response(response)

    # ------------------------------------------------------------------
    # Command dispatcher
    # ------------------------------------------------------------------

    def _dispatch(self, compiled: str, pump_num: int) -> str:
        """
        Parse a fully-compiled Protocol1 command string and return the
        response string (including the ACK byte prefix) the real pump
        would send.

        The compiled format is:
            {address_letter}{target_component}{command_body}{value}{R|K|$|V}\\r

        We strip the address letter, split off the execution suffix, and
        match the body against known command patterns.
        """
        state = self._state.get(pump_num)
        if state is None:
            logger.warning(f"[SIM] Unknown pump_num {pump_num}, ignoring.")
            return _ack()

        # Strip trailing \r and extract the address letter.
        raw = compiled.rstrip("\r")
        if not raw:
            return _ack()

        # The first character is the address letter; drop it.
        body = raw[1:]

        # --- Execution-only commands (no command body, just suffix) ---

        if body == "K":  # PAUSE
            return _ack()
        if body == "$":  # RESUME
            return _ack()
        if body == "V":  # CLEAR_BUFFER
            return _ack()

        # --- Strip the execution suffix (R, K, $, V) from the end ---
        execution_suffix = body[-1] if body and body[-1] in ("R", "K", "$", "V") else ""
        cmd_body = body[:-1] if execution_suffix else body

        # --- Dispatch on command body ---

        # REQUEST_DONE: "F"  → always "Y" (sim is always idle)
        if cmd_body == "F" or cmd_body.endswith("F"):
            return _ack("Y")

        # IS_SINGLE_SYRINGE: "H"
        if cmd_body == "H" or cmd_body.endswith("H"):
            return _ack("N" if self._dual_syringe else "Y")

        # FIRMWARE_VERSION: "U"
        if cmd_body == "U" or cmd_body.endswith("U"):
            return _ack(state.firmware_version)

        # BUSY_STATUS: "T1"  → all-idle bit pattern.
        if "T1" in cmd_body:
            return _ack("@")

        # STATUS_REQUEST: "E1"  → no errors, all bits clear
        if "E1" in cmd_body:
            return _ack("@")

        # CURRENT_SYRINGE_POSITION: "YQP"
        if "YQP" in cmd_body:
            # Handle optional component prefix (B/C for dual syringe)
            return _ack(str(state.syringe_position))

        # ABSOLUTE_MOVE: "M{steps}S{speed}"
        m = re.search(r"M(\d+)S(\d+)", cmd_body)
        if m:
            state.syringe_position = int(m.group(1))
            return _ack()

        # INIT_SYRINGE_ONLY: "X1S{speed}"
        m = re.search(r"X1S(\d+)", cmd_body)
        if m:
            state.syringe_position = 0
            return _ack()

        # INIT_VALVE_ONLY: "LX"
        if "LX" in cmd_body:
            state.valve_angle = 0
            return _ack()

        # VALVE_ANGLE query: "LQA"
        if "LQA" in cmd_body and "LA" not in cmd_body:
            return _ack(str(state.valve_angle))

        # SET_VALVE_ANGLE CW: "LA0{angle}"
        m = re.search(r"LA0(\d+)", cmd_body)
        if m:
            state.valve_angle = int(m.group(1)) % 360
            return _ack()

        # SET_VALVE_ANGLE CCW: "LA1{angle}"
        m = re.search(r"LA1(\d+)", cmd_body)
        if m:
            state.valve_angle = int(m.group(1)) % 360
            return _ack()

        # CURRENT_VALVE_POSITION by name: "LQP"
        if "LQP" in cmd_body:
            # Return a nominal position number; 1-indexed.
            pos = (state.valve_angle // 45) + 1
            return _ack(str(pos))

        # SET_VALVE_POSITION by name CW: "LP0{pos}"
        m = re.search(r"LP0(\w+)", cmd_body)
        if m:
            # Convert named position back to angle (each step is 45°).
            try:
                pos = int(m.group(1))
                state.valve_angle = ((pos - 1) * 45) % 360
            except ValueError:
                pass
            return _ack()

        # GET_RETURN_STEPS: "YQN"
        if "YQN" in cmd_body:
            return _ack(str(state.return_steps))

        # SET_RETURN_STEPS: "YSN{n}"
        m = re.search(r"YSN(\d+)", cmd_body)
        if m:
            state.return_steps = int(m.group(1))
            return _ack()

        # SYRINGE_HAS_ERROR: "Z" / VALVE_HAS_ERROR: "G"
        if cmd_body.endswith("Z") or cmd_body.endswith("G"):
            return _ack("N")  # no error

        # Anything else — return ACK so the real code doesn't raise.
        logger.debug(f"[SIM] Unhandled command body: {cmd_body!r} — returning ACK")
        return _ack()

    # ------------------------------------------------------------------
    # Reset helper (useful in tests to restore a clean state)
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset all pump states to their initial values."""
        for state in self._state.values():
            state.syringe_position = 0
            state.valve_angle = 0
            state.return_steps = 24


# ---------------------------------------------------------------------------
# ML600Sim — the public sim device
# ---------------------------------------------------------------------------


class ML600Sim(ML600):
    """
    Simulated Hamilton ML600 syringe pump.

    Subclasses ``ML600`` and overrides only ``from_config`` / ``__init__``
    to inject ``SimulatedHamiltonPumpIO`` instead of a real serial connection.
    All business logic in ``ML600``, ``ML600Pump``, and ``ML600LeftValve`` /
    ``ML600RightValve`` runs completely unmodified.

    TOML usage (identical to real ML600 — no port required)
    --------------------------------------------------------
        [device.my-pump]
        type = "ML600"          # flowchem-sim replaces this with ML600Sim
        syringe_volume = "10 ml"
        # dual_syringe = true   # optional, default false

    Direct instantiation in tests
    ------------------------------
        device = ML600Sim.from_config(
            name="test-pump",
            syringe_volume="10 ml",
        )
        await device.initialize()
        pump = device.components[0]   # ML600Pump
        valve = device.components[1]  # ML600LeftValve
    """

    sim_io: SimulatedHamiltonPumpIO

    @classmethod
    def from_config(cls, **config) -> "ML600Sim":
        """
        Create an ML600Sim from a config dict.

        Accepts the same keys as the real ``ML600.from_config`` except that
        ``port`` is not required (and is ignored if provided).
        """
        dual_syringe: bool = config.pop("dual_syringe", False)
        syringe_volume: str = config.pop("syringe_volume", "10 ml")
        address: int = int(config.pop("address", 1))
        name: str = config.pop("name", "sim-ml600")
        firmware_version: str = config.pop("firmware_version", "NV01.02.3")

        # Ignore port and any other serial params.
        config.pop("port", None)

        # Build the simulated IO layer.
        sim_io = SimulatedHamiltonPumpIO(
            num_pumps=1,
            dual_syringe=dual_syringe,
            firmware_version=firmware_version,
        )

        # Build valid ML600 kwargs from remaining config (valve types, rates…)
        valid_keys = set(ML600.DEFAULT_CONFIG.keys())
        extra_config = {k: v for k, v in config.items() if k in valid_keys}

        instance = cls(
            pump_io=sim_io,
            syringe_volume=syringe_volume,
            name=name,
            address=address,
            **extra_config,
        )
        # Expose the IO layer directly so tests can inspect/manipulate state.
        instance.sim_io = sim_io
        return instance

    async def initialize(self, init_speed: str = "200 sec / stroke"):
        """Initialize the simulated pump and start with a full syringe volume."""
        await super().initialize(init_speed=init_speed)
        for state in self.sim_io._state.values():
            state.syringe_position = 48000
