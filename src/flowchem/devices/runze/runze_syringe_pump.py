"""Runze Smart SY-01 syringe pump control (plunger + built-in distribution valve)."""

from __future__ import annotations

import asyncio

from loguru import logger
import pint

from flowchem import ureg
from flowchem.components.flowchem_component import FlowchemComponent
from flowchem.components.device_info import DeviceInfo
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.runze._common import (
    STATUS_MESSAGES,
    RunzeCommand,
    RunzeSerialIO,
    RunzeValveHeads,
    detect_valve_type,
    get_shared_runze_io,
    send_and_await_completion,
)
from flowchem.devices.runze.runze_syringe_pump_component import (
    RunzeSyringePumpComponent,
)
from flowchem.devices.runze.runze_valve_component import (
    Runze6PortDistributionValve,
    Runze8PortDistributionValve,
    Runze10PortDistributionValve,
    Runze12PortDistributionValve,
    Runze16PortDistributionValve,
)
from flowchem.utils.exceptions import DeviceError, InvalidConfigurationError
from flowchem.utils.people import miguel

__all__ = ["RunzeSyringePump"]


class RunzeSyringePump(FlowchemDevice):
    """Control a Runze Smart SY-01 syringe pump.

    The plunger and the built-in distribution valve are two motors on one
    physical unit, addressed with the same protocol address -- the valve
    reuses the exact 0x44/0x3e commands already implemented for the
    standalone `RunzeValve` (SV-06), so its component classes are reused
    unmodified here.
    """

    def __init__(
        self,
        pump_io: RunzeSerialIO,
        name: str,
        address: int = 1,
        syringe_volume: str = "",
        total_steps: int = 12000,
    ) -> None:
        super().__init__(name)

        self.pump_io = pump_io
        self.address = address
        self.total_steps = int(total_steps)
        # Serializes move commands: if software gives up waiting on one move
        # before the device is actually done with it, a second move dispatched
        # right after can land on a still-busy device and get no response at
        # all. This won't fix that if the timeout itself is too short, but it
        # stops two moves from ever being in flight at once.
        self._move_lock = asyncio.Lock()
        # The built-in valve's current port, tracked in software -- see
        # `get_raw_position` for why (0x3e, the position-query command, is
        # documented only for the standalone SV-06 and this hardware never
        # replies to it at all; the full SY-01 manual has no query command
        # for the built-in valve's current port).
        self._last_valve_position: str = ""

        try:
            self.syringe_volume: pint.Quantity = ureg.Quantity(syringe_volume)
        except AttributeError as attribute_error:
            logger.error(f"Invalid syringe volume {syringe_volume}!")
            raise InvalidConfigurationError(
                "RunzeSyringePump requires a syringe_volume, e.g. '5 mL'."
            ) from attribute_error

        self._steps_per_ml: pint.Quantity = (
            self.total_steps * ureg.step
        ) / self.syringe_volume

        self.device_info = DeviceInfo(
            authors=[miguel],
            manufacturer="Runze",
            model="Smart SY-01",
            additional_info={
                "syringe_volume": syringe_volume,
                "total_steps": self.total_steps,
            },
        )

    async def initialize(self):
        await super().initialize()

        self.components.append(RunzeSyringePumpComponent("pump", self))

        # The built-in valve is optional -- Runze also ships valveless SY-01 pumps
        # (bare plunger units), and a valve that isn't wired/powered/installed will
        # never answer the position probe. Don't let that block the pump itself.
        try:
            valve_type = await self.get_valve_type()
        except ValueError:
            logger.warning(
                f"{self.name}: no built-in valve detected (position probing got no "
                f"successful reply). Continuing as a valveless pump. If this unit "
                f"does have a valve, check its wiring/power."
            )
            return
        self.device_info.additional_info["valve-type"] = valve_type

        valve_component: FlowchemComponent
        match valve_type:
            case RunzeValveHeads.SIX_PORT_SIX_POSITION:
                valve_component = Runze6PortDistributionValve("valve", self)
            case RunzeValveHeads.EIGHT_PORT_EIGHT_POSITION:
                valve_component = Runze8PortDistributionValve("valve", self)
            case RunzeValveHeads.TEN_PORT_TEN_POSITION:
                valve_component = Runze10PortDistributionValve("valve", self)
            case RunzeValveHeads.TWELVE_PORT_TWELVE_POSITION:
                valve_component = Runze12PortDistributionValve("valve", self)
            case RunzeValveHeads.SIXTEEN_PORT_SIXTEEN_POSITION:
                valve_component = Runze16PortDistributionValve("valve", self)
            case _:
                raise RuntimeError("Unknown valve type")

        self.components.append(valve_component)

    async def get_valve_type(self):
        """Detect the built-in valve head by testing possible port values."""
        return await detect_valve_type(self.set_raw_position)

    async def _send_command_and_read_reply(
        self,
        command: str,
        parameter: int = 0,
        raise_errors: bool = True,
        is_factory_command: bool = False,
    ):
        pump_command = RunzeCommand(
            function_code=command,
            address=self.address,
            parameter=parameter,
            is_factory_command=is_factory_command,
        )
        status, parameters = await self.pump_io.write_and_read_reply_async(
            pump_command, raise_errors
        )
        return status, parameters

    # -- Move commands (0x42/0x43): completion detection --
    #
    # Unlike 0x44/0x45 (see `send_and_await_completion`), the manual doesn't
    # document an early "busy/accepted" acknowledgment for these two -- and on
    # real hardware, they reply only once the physical move is fully done (a
    # 12000-step full-stroke aspirate got zero reply within 5 s, the same window
    # that was already too short for a much smaller ~1920-step move). So the
    # read timeout is sized proportionally to the requested step count rather
    # than a fixed window, instead of assuming an early ack we have no evidence
    # exists on this hardware.
    #
    # MOVE_FULL_STROKE_TIMEOUT is a provisional estimate, not a vendor-specified
    # value. A first guess of 120s was confirmed too short on real hardware (a
    # genuine full-stroke aspirate got no reply within that window) -- set well
    # above that pending real timing data from an actual full-stroke move.
    MOVE_FULL_STROKE_TIMEOUT = 60.0
    MOVE_MIN_TIMEOUT = 10.0

    def _raise_or_reject(self, status: str, raise_errors: bool) -> bool:
        message = STATUS_MESSAGES.get(status, "Unknown status code")
        logger.error(f"{message} (Status code: {status})")
        if raise_errors:
            raise DeviceError(f"{message} - Check command syntax or device status!")
        return False

    async def _send_move_and_wait(
        self, command: str, parameter: int = 0, raise_errors: bool = True
    ) -> bool:
        read_timeout = max(
            self.MOVE_MIN_TIMEOUT,
            (parameter / self.total_steps) * self.MOVE_FULL_STROKE_TIMEOUT,
        )
        move_command = RunzeCommand(
            function_code=command, address=self.address, parameter=parameter
        )
        # Serialized: don't let a second move be dispatched while this one's
        # reply is still outstanding (see `_move_lock` in __init__).
        async with self._move_lock:
            try:
                status, _ = await self.pump_io.write_and_read_reply_async(
                    move_command, raise_errors=False, read_timeout=read_timeout
                )
            except InvalidConfigurationError:
                logger.error(
                    f"No response to move command 0x{command} within "
                    f"{read_timeout:.0f}s -- may need an even longer timeout, "
                    f"or may still be finishing a previous move."
                )
                if raise_errors:
                    raise
                return False

        if status == "00":
            return True
        return self._raise_or_reject(status, raise_errors)

    # -- Built-in valve pass-through (shares the pump's address; set_raw_position
    # is identical to RunzeValve's, get_raw_position is not -- see its docstring) --

    async def get_raw_position(self) -> str:
        """Return current valve position, following valve nomenclature.

        Tracked in software, not queried from hardware: the SY-01 manual has
        no command for reading the built-in valve's current port back (0x3e,
        "query current located port", is documented only for the standalone
        SV-06 -- on this hardware it never replies at all, not even an error
        status). `set_raw_position` records its target on every successful
        move, which this just returns.
        """
        return self._last_valve_position

    async def set_raw_position(self, position: str | int, raise_errors: bool = True) -> bool:
        """Set valve position, following valve nomenclature.

        Per the manual, 0x44 may reply immediately with status `fe`/`04`
        rather than waiting for the switch to complete -- completion is then
        confirmed by polling `get_status` (0x4a) until it reports `00`.
        """
        status, parameters = await send_and_await_completion(
            send_fn=lambda: self._send_command_and_read_reply(
                command="44", parameter=int(position), raise_errors=False
            ),
            poll_status_fn=self.get_status,
            raise_errors=raise_errors,
        )
        if status == "00":
            logger.info(f"Valve position set to: {parameters}")
            # Cast to str regardless of caller's type: the abstract
            # Valve.set_position() (valve.py) calls this with a plain int
            # from its own _change_connections() mapping, but
            # get_raw_position()'s declared return type -- and the
            # /monitor_position REST endpoint's response model -- is str.
            # Caching the raw int here previously slipped through, silently
            # 500-ing the next GET /monitor_position with a FastAPI
            # ResponseValidationError.
            self._last_valve_position = str(position)
            return True
        return False

    async def set_address(self, address: int) -> str:
        status, _ = await self._send_command_and_read_reply(
            command="00", parameter=address, is_factory_command=True
        )
        if status == "00":
            self.address = address
        return status

    # -- Plunger control --

    async def home(self, raise_errors: bool = True) -> bool:
        """Home the plunger (0x45): runs to the reset optocoupler and stops there.

        Per the manual, 0x45 may reply immediately with status `fe`/`04`
        rather than waiting for the physical move to finish -- completion is
        then confirmed by polling `get_status` (0x4a) until it reports `00`.
        A successful home is followed by `sync_position` (0x67), which the
        manual requires for subsequent `read_position` (0x66) calls to be
        accurate.
        """
        status, _ = await send_and_await_completion(
            send_fn=lambda: self._send_command_and_read_reply(
                command="45", raise_errors=False
            ),
            poll_status_fn=self.get_status,
            raise_errors=raise_errors,
            max_wait=self.MOVE_FULL_STROKE_TIMEOUT,
        )
        if status != "00":
            return False
        return await self.sync_position(raise_errors=raise_errors)

    async def sync_position(self, raise_errors: bool = True) -> bool:
        """Tell the device the current (just-homed) position is the zero
        reference (0x67) -- required for `read_position` (0x66) to be
        accurate afterward, per the manual.
        """
        status, _ = await self._send_command_and_read_reply(
            command="67", raise_errors=raise_errors
        )
        return status == "00"

    async def stop(self) -> bool:
        """Strong stop: halts both the plunger and the valve motor (0x49)."""
        status, _ = await self._send_command_and_read_reply(
            command="49", raise_errors=False
        )
        return status == "00"

    async def dispense_steps(self, steps: int, raise_errors: bool = True) -> bool:
        """Move the plunger toward home by `steps` (0x42, "Injection"/dispense).

        Bounded by the reset optocoupler: a `steps` value larger than the
        remaining distance to home just stops early at home rather than
        overshooting.
        """
        if not 1 <= steps <= self.total_steps:
            raise ValueError(f"Steps must be between 1 and {self.total_steps}.")
        return await self._send_move_and_wait(
            command="42", parameter=steps, raise_errors=raise_errors
        )

    async def aspirate_steps(self, steps: int, raise_errors: bool = True) -> bool:
        """Move the plunger away from home by `steps` (0x43, "Suction"/aspirate).

        Bounded by the lower-limit optocoupler at the other end of travel.
        """
        if not 1 <= steps <= self.total_steps:
            raise ValueError(f"Steps must be between 1 and {self.total_steps}.")
        return await self._send_move_and_wait(
            command="43", parameter=steps, raise_errors=raise_errors
        )

    async def read_position(self) -> int:
        """Return the plunger's current position in steps from home (0x66)."""
        status, parameters = await self._send_command_and_read_reply(
            command="66", raise_errors=True
        )
        if status != "00":
            raise DeviceError(f"Could not read piston position, status '{status}'.")
        return int(parameters, 16)

    async def get_status(self) -> str:
        """Query motor status (0x4a): '00' idle, '04' busy, 'fe' task just accepted."""
        status, _ = await self._send_command_and_read_reply(
            command="4a", raise_errors=False
        )
        return status

    async def is_moving(self) -> bool:
        """Return True unless the pump reports idle."""
        return await self.get_status() != "00"

    def volume_to_steps(self, volume: pint.Quantity) -> int:
        return round((volume * self._steps_per_ml).m_as("step"))

    async def get_current_volume(self) -> pint.Quantity:
        """Return the current syringe volume, derived from the plunger's step position."""
        current_steps = await self.read_position() * ureg.step
        return current_steps / self._steps_per_ml

    async def set_to_volume(self, target_volume: pint.Quantity) -> bool:
        """Absolute move: dispense or aspirate however many steps reach `target_volume`."""
        if not ureg.Quantity("0 ml") <= target_volume <= self.syringe_volume:
            raise ValueError(
                f"Target volume {target_volume} is outside the syringe range "
                f"(0 to {self.syringe_volume})."
            )
        current_steps = await self.read_position()
        target_steps = self.volume_to_steps(target_volume)
        delta = target_steps - current_steps
        if delta == 0:
            return True
        if delta > 0:
            return await self.aspirate_steps(delta)
        return await self.dispense_steps(-delta)

    @classmethod
    def from_config(cls, **config):
        """Create a RunzeSyringePump from Flowchem TOML configuration."""
        # Remove RunzeSyringePump-specific keys to only have RunzeSerialIO's configs
        config_for_pumpio = {
            k: v
            for k, v in config.items()
            if k not in ("address", "name", "syringe_volume", "total_steps")
        }
        pump_io = get_shared_runze_io(config.get("port"), config_for_pumpio)

        return cls(
            pump_io,
            address=config.get("address", 1),
            name=config.get("name", ""),
            syringe_volume=config.get("syringe_volume", ""),
            total_steps=config.get("total_steps", 12000),
        )


if __name__ == "__main__":
    import asyncio
    import subprocess
    import sys
    import time
    from pathlib import Path

    # Real-hardware test harness for the physical pump on COM10 -- talks to the
    # device directly, does NOT go through the flowchem server. Exercises the
    # RunzeSyringePumpComponent API surface (the same methods the server would
    # expose as REST endpoints) directly in Python, plus camera snapshots via
    # `__script/cam_capture.py` for visual position confirmation (self-reported
    # step counts alone aren't trustworthy: `home()`'s follow-up `sync_position`
    # call resets the position counter regardless of whether the plunger
    # actually got there, so a bad home would still read back as "0").
    CAM_SCRIPT = Path("__script/cam_capture.py")
    _snapshot_count = 0

    def snapshot(label: str) -> None:
        global _snapshot_count
        if not CAM_SCRIPT.exists():
            print(f"  (skipping snapshot -- {CAM_SCRIPT} not found from cwd {Path.cwd()})")
            return
        _snapshot_count += 1
        out = Path(f"pump_{_snapshot_count:02d}_{label}.png")
        try:
            # cv2/camera-backend cold start alone measured ~19.5s in isolation
            # (nothing to do with the pump or asyncio) -- 50s leaves real margin.
            subprocess.run(
                [sys.executable, str(CAM_SCRIPT), "-o", str(out)],
                check=True,
                timeout=50,
            )
        except Exception as exc:
            print(f"  camera snapshot failed: {exc}")

    async def raw(pump: RunzeSyringePump, command: str, parameter: int = 0, timeout: float | None = None):
        """Send one command and print its raw status/parameters/latency, bypassing
        every higher-level helper (retries, completion-polling, error-raising)."""
        cmd = RunzeCommand(function_code=command, address=pump.address, parameter=parameter)
        t0 = time.perf_counter()
        try:
            status, parameters = await pump.pump_io.write_and_read_reply_async(
                cmd, raise_errors=False, read_timeout=timeout
            )
        except InvalidConfigurationError:
            status, parameters = "<no reply>", ""
        dt = time.perf_counter() - t0
        print(f"  0x{command} param={parameter:<6} -> status={status!r:8} params={parameters!r:8} ({dt:.2f}s)")
        return status, parameters

    async def call(label: str, coro) -> object | None:
        """Await `coro`, printing its result/latency. A raised exception (e.g. the
        component's withdraw()/infuse() have no raise_errors=False escape hatch,
        so a hardware timeout propagates as a real exception) is caught and
        reported instead of killing the rest of the endpoint sweep -- we want to
        see every endpoint's outcome in one run, not just the first failure.
        """
        t0 = time.perf_counter()
        try:
            result = await coro
            print(f"  {label:32} -> {result!r} ({time.perf_counter() - t0:.1f}s)")
            return result
        except Exception as exc:
            print(f"  {label:32} -> RAISED {type(exc).__name__}: {exc} ({time.perf_counter() - t0:.1f}s)")
            return None

    async def test_component_endpoints(pump: RunzeSyringePump) -> None:
        """Call every method `RunzeSyringePumpComponent` registers as a REST
        route, in the same sequence a user driving the API would: reachability
        and read-only queries first, then a small round-trip move, then stop,
        then the two full-stroke endpoints (bounded safely by the limit
        switches per `infuse_all`/`withdraw_all`'s own docstrings).
        """
        component = next(c for c in pump.components if c.name == "pump")
        assert isinstance(component, RunzeSyringePumpComponent)

        print("\n== component endpoint tests (direct Python calls, no HTTP/flowchem server) ==")

        await call("is_reachable()", component.is_reachable())
        await call("get_current_volume()", component.get_current_volume())
        await call("is_pumping()", component.is_pumping())
        await raw(pump, "4a")  # raw status, for comparison with is_pumping()'s interpretation
        await raw(pump, "66")  # raw position, ground truth for the volume conversion above

        snapshot("component_start")

        print("\n  -- withdraw(volume='0.5 mL') / infuse(volume='0.5 mL') round trip --")
        await call("withdraw(volume='0.5 mL')", component.withdraw(volume="0.5 mL"))
        await raw(pump, "4a")  # if the move above hung, see what status the device reports right now
        await call("get_current_volume()", component.get_current_volume())
        snapshot("after_withdraw_0.5ml")

        await call("infuse(volume='0.5 mL')", component.infuse(volume="0.5 mL"))
        await call("get_current_volume()", component.get_current_volume())
        snapshot("after_infuse_0.5ml")

        print("\n  -- stop() while idle (should be a safe no-op) --")
        await call("stop()", component.stop())

        print("\n  -- withdraw_all() / infuse_all() full-stroke round trip --")
        await call("withdraw_all()", component.withdraw_all())
        await call("get_current_volume()", component.get_current_volume())
        snapshot("after_withdraw_all")

        await call("infuse_all()", component.infuse_all())
        await call("get_current_volume()", component.get_current_volume())
        snapshot("after_infuse_all")

        await call("is_pumping()", component.is_pumping())

    async def main():
        pump = RunzeSyringePump.from_config(
            port="COM10",
            address=0,
            name="Test Pump",
            syringe_volume="5 mL",
            total_steps=12000,
            baudrate=9600,
        )

        print("== raw protocol sanity check (address/speed/status/position) ==")
        await raw(pump, "20")  # query address
        await raw(pump, "27")  # query max speed
        await raw(pump, "2b")  # query reset speed
        await raw(pump, "4a")  # query motor status
        await raw(pump, "66")  # read piston position

        print("\n== pump.initialize() (mirrors what the flowchem server does) ==")
        await pump.initialize()
        print(f"  components: {[c.name for c in pump.components]}")

        await test_component_endpoints(pump)

    asyncio.run(main())
