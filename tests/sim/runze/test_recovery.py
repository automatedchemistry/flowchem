"""Exercise SY-01 recovery through its real driver and HTTP components."""

from collections import deque
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from loguru import logger
import pytest

from flowchem.devices.runze import _common
from flowchem.devices.runze._common import RunzeCommunicationError
from flowchem.devices.runze.runze_syringe_pump import RunzeSyringePump
from flowchem.devices.runze.runze_syringe_pump_component import (
    RunzeSyringePumpComponent,
)
from flowchem.devices.runze.runze_valve_component import Runze6PortDistributionValve
from flowchem.sim.devices.runze.runze_sim import SimulatedRunzeSyringePumpIO
from flowchem.utils.exceptions import DeviceError


class _Clock:
    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now

    async def sleep(self, seconds):
        self.now += seconds


@pytest.fixture
def clock(monkeypatch):
    clock = _Clock()
    # Replacing the module reference keeps TestClient's own real clock intact.
    monkeypatch.setattr(_common, "time", SimpleNamespace(monotonic=clock.monotonic))
    monkeypatch.setattr(_common.asyncio, "sleep", clock.sleep)
    return clock


@pytest.fixture
def warnings():
    messages = []
    sink = logger.add(
        lambda message: messages.append(message.record["message"]),
        filter=lambda record: record["level"].name == "WARNING",
    )
    yield messages
    logger.remove(sink)


class _ScriptedPumpIO(SimulatedRunzeSyringePumpIO):
    """Moves execute once; scripted dropped replies simulate unreliable IO."""

    def __init__(
        self,
        replies=(),
        *,
        default_status="00",
        command_replies=None,
        clock=None,
        poll_seconds=0.0,
    ):
        super().__init__(num_ports=6, total_steps=12000)
        self.replies = deque(replies)
        self.default_status = default_status
        self.command_replies = command_replies or {}
        self.clock = clock
        self.poll_seconds = poll_seconds
        self.commands = []

    async def write_and_read_reply_async(
        self, command, raise_errors=True, read_timeout=None
    ):
        function = command.function_code.lower()
        self.commands.append(function)
        if function == "4a":
            if self.clock is not None:
                self.clock.now += self.poll_seconds
            status = self.replies.popleft() if self.replies else self.default_status
            if status is None:
                raise RunzeCommunicationError("No reply on simulated status query")
            return status, "0000"

        if function in ("42", "43", "44", "45"):
            status = self.command_replies.get(function, "fe")
            if status in ("00", "fe", None):
                # A dropped acknowledgement does not imply the motor stayed still.
                await super().write_and_read_reply_async(
                    command, raise_errors=False, read_timeout=read_timeout
                )
            if status is None:
                raise RunzeCommunicationError("No reply on simulated motion command")
            return status, "0000"

        if function in self.command_replies and self.command_replies[function] is None:
            raise RunzeCommunicationError("No reply on simulated sync command")

        return await super().write_and_read_reply_async(
            command, raise_errors=raise_errors, read_timeout=read_timeout
        )


def _pump(io):
    return RunzeSyringePump(
        pump_io=io, name="recovery", syringe_volume="5 mL", address=7
    )


_ACTIONS = [
    ("aspirate_steps", "43"),
    ("dispense_steps", "42"),
    ("set_raw_position", "44"),
    ("home", "45"),
]


async def _action(pump, operation, *, raise_errors=True):
    method = getattr(pump, operation)
    if operation.endswith("_steps"):
        return await method(1200, raise_errors=raise_errors)
    if operation == "set_raw_position":
        return await method("3", raise_errors=raise_errors)
    return await method(raise_errors=raise_errors)


@pytest.mark.parametrize(("operation", "command"), _ACTIONS)
async def test_accepted_motion_recovers_after_four_missing_polls(
    operation, command, clock, warnings
):
    io = _ScriptedPumpIO([None] * 4 + ["04", "00"], clock=clock, poll_seconds=0.25)
    pump = _pump(io)

    assert await _action(pump, operation) is True

    assert io.commands.count(command) == 1
    assert io.commands.count("4a") == 6
    assert len(warnings) >= 4
    if operation == "home":
        assert io.commands[-1] == "67"
        assert io.commands.count("67") == 1
    if operation == "set_raw_position":
        assert await pump.get_raw_position() == "3"


@pytest.mark.parametrize(("operation", "command"), _ACTIONS)
async def test_unconfirmed_motion_returns_false_without_retrying_motion(
    operation, command, clock
):
    io = _ScriptedPumpIO(default_status=None, clock=clock, poll_seconds=61)
    pump = _pump(io)
    pump._last_valve_position = "2"
    pump.get_status = AsyncMock(side_effect=AssertionError("Nested status retries"))

    assert await _action(pump, operation, raise_errors=False) is False

    assert io.commands == [command, "4a"]
    pump.get_status.assert_not_awaited()
    assert await pump.get_raw_position() == "2"


@pytest.mark.parametrize(("operation", "command"), _ACTIONS)
async def test_unconfirmed_motion_raises_communication_error_in_strict_mode(
    operation, command, clock
):
    io = _ScriptedPumpIO(default_status=None, clock=clock, poll_seconds=61)
    pump = _pump(io)

    with pytest.raises(RunzeCommunicationError):
        await _action(pump, operation)

    assert io.commands == [command, "4a"]


@pytest.mark.parametrize(("operation", "command"), _ACTIONS)
async def test_missing_initial_acknowledgement_returns_false_without_resending(
    operation, command
):
    io = _ScriptedPumpIO(command_replies={command: None})
    pump = _pump(io)
    pump._last_valve_position = "2"

    assert await _action(pump, operation, raise_errors=False) is False

    assert io.commands == [command]
    assert await pump.get_raw_position() == "2"


async def test_successful_home_with_missing_sync_reply_returns_false():
    io = _ScriptedPumpIO(command_replies={"45": "00", "67": None})

    assert await _pump(io).home(raise_errors=False) is False

    assert io.commands == ["45", "67"]


@pytest.mark.parametrize(("operation", "command"), _ACTIONS)
@pytest.mark.parametrize(
    ("status", "message"), [("03", "Optocoupler error"), ("05", "Motor stalled")]
)
async def test_hardware_fault_is_preserved(operation, command, status, message):
    io = _ScriptedPumpIO(command_replies={command: status})
    pump = _pump(io)

    with pytest.raises(DeviceError, match=message):
        await _action(pump, operation)

    assert io.commands == [command]


@pytest.mark.parametrize(("operation", "command"), _ACTIONS[:2])
async def test_immediate_busy_reply_rejects_plunger_move(operation, command):
    io = _ScriptedPumpIO(command_replies={command: "04"})
    pump = _pump(io)

    with pytest.raises(DeviceError, match="Motor busy"):
        await _action(pump, operation)

    assert io.commands == [command]


@pytest.mark.parametrize("misses", [1, 2])
async def test_direct_status_query_recovers_within_three_attempts(
    misses, clock, warnings
):
    io = _ScriptedPumpIO([None] * misses + ["00"])

    assert await _pump(io).get_status() == "00"

    assert io.commands == ["4a"] * (misses + 1)
    assert len(warnings) >= misses


async def test_direct_status_query_stops_after_three_total_attempts(clock):
    io = _ScriptedPumpIO(default_status=None)

    with pytest.raises(RunzeCommunicationError, match="recovery"):
        await _pump(io).get_status()

    assert io.commands == ["4a"] * 3


async def test_direct_status_preserves_reported_hardware_fault():
    io = _ScriptedPumpIO(["05"])

    assert await _pump(io).get_status() == "05"

    assert io.commands == ["4a"]


def _app(pump):
    app = FastAPI()
    app.include_router(RunzeSyringePumpComponent("pump", pump).router)
    app.include_router(Runze6PortDistributionValve("valve", pump).router)

    @app.get("/unrelated")
    def unrelated():
        return {"available": True}

    return app


@pytest.mark.parametrize("component", ["pump", "valve"])
def test_idle_http_query_recovers_after_missing_reply(component):
    io = _ScriptedPumpIO([None, "00"])
    pump = _pump(io)

    with TestClient(_app(pump), raise_server_exceptions=False) as client:
        response = client.get(f"/recovery/{component}/is-idle")

    assert response.status_code == 200
    assert response.json() is True
    assert io.commands == ["4a", "4a"]


@pytest.mark.parametrize("component", ["pump", "valve"])
def test_failed_idle_http_query_keeps_other_routes_and_later_queries_available(
    component,
):
    io = _ScriptedPumpIO(default_status=None)
    pump = _pump(io)

    with TestClient(_app(pump), raise_server_exceptions=False) as client:
        response = client.get(f"/recovery/{component}/is-idle")
        assert response.status_code == 500
        assert io.commands == ["4a"] * 3

        response = client.get("/unrelated")
        assert response.status_code == 200
        assert response.json() == {"available": True}

        io.default_status = "00"
        response = client.get(f"/recovery/{component}/is-idle")
        assert response.status_code == 200
        assert response.json() is True
        assert io.commands == ["4a"] * 4


class _SlowPumpIO(SimulatedRunzeSyringePumpIO):
    """Acknowledges moves with `fe`, then advances the plunger `steps_per_poll`
    steps per 0x4a poll, reporting `04` until the target is reached. With
    `stall_at`, the plunger stops there while the pump keeps reporting busy."""

    def __init__(self, steps_per_poll, *, stall_at=None, position_readable=True):
        super().__init__(num_ports=6, total_steps=12000)
        self.steps_per_poll = steps_per_poll
        self.stall_at = stall_at
        self.position_readable = position_readable
        self.target = None
        self.commands = []

    async def write_and_read_reply_async(
        self, command, raise_errors=True, read_timeout=None
    ):
        function = command.function_code.lower()
        self.commands.append(function)
        position = self._sim_plunger_position
        if function in ("42", "43"):
            sign = 1 if function == "43" else -1
            self.target = position + sign * command.parameter
            return "fe", "0000"
        if function == "4a" and self.target is not None:
            if position == self.target:
                self.target = None
                return "00", "0000"
            if position != self.stall_at:
                step = min(self.steps_per_poll, abs(self.target - position))
                self._sim_plunger_position += step if self.target > position else -step
            return "04", "0000"
        if function == "66" and not self.position_readable:
            raise RunzeCommunicationError("No reply on simulated position query")
        return await super().write_and_read_reply_async(
            command, raise_errors=raise_errors, read_timeout=read_timeout
        )


async def test_slow_move_is_awaited_while_the_plunger_keeps_moving(clock, warnings):
    # 20 steps per 0.2 s poll: 4800 steps take ~48 s, twice the 24 s budget.
    io = _SlowPumpIO(steps_per_poll=20)
    pump = _pump(io)

    assert await pump.aspirate_steps(4800) is True

    assert io._sim_plunger_position == 4800
    assert io.commands.count("43") == 1
    assert io.commands.count("66") >= 2
    assert 47 < clock.now < 60
    assert any("taking longer than the 24s estimated" in w for w in warnings)


async def test_busy_pump_whose_plunger_stopped_fails_after_one_check(clock):
    io = _SlowPumpIO(steps_per_poll=20, stall_at=1000)
    pump = _pump(io)

    with pytest.raises(DeviceError, match="Motor busy"):
        await pump.aspirate_steps(4800)

    assert io.commands.count("66") == 2
    assert clock.now == pytest.approx(24 + pump.MOVE_PROGRESS_CHECK, abs=0.5)


async def test_busy_pump_with_unreadable_position_fails_at_the_budget(clock):
    io = _SlowPumpIO(steps_per_poll=20, position_readable=False)
    pump = _pump(io)

    with pytest.raises(DeviceError, match="Motor busy"):
        await pump.aspirate_steps(4800)

    assert io.commands.count("66") == 1
    assert clock.now == pytest.approx(24, abs=0.5)


async def test_moving_plunger_is_awaited_at_most_move_max_wait(clock):
    io = _SlowPumpIO(steps_per_poll=1)  # 12000 steps would take 2400 s
    pump = _pump(io)

    assert await pump.aspirate_steps(12000, raise_errors=False) is False

    assert io.commands.count("43") == 1
    assert clock.now == pytest.approx(pump.MOVE_MAX_WAIT, abs=1)
