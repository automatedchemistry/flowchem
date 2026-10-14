"""Regression tests for the shared Runze protocol primitives in `_common.py`.

Fixtures here are worked byte examples taken directly from the vendor's
"Smart SY-01-Syringe" and "SV-06-Multiport Valve" manuals, so these don't
need real hardware to verify against.
"""

from types import SimpleNamespace

import pytest

from flowchem.devices.runze import _common
from flowchem.devices.runze._common import (
    MAX_MISSED_POLLS,
    RunzeCommand,
    RunzeCommunicationError,
    RunzeSerialIO,
    await_completion,
    send_and_await_completion,
)
from flowchem.utils.exceptions import DeviceError, InvalidConfigurationError


def _scripted_poll(replies):
    """Return a 0x4a poll stub that plays back `replies` in order; a `None`
    entry simulates a dropped reply (no bytes within the serial timeout)."""
    remaining = list(replies)

    async def poll():
        reply = remaining.pop(0)
        if reply is None:
            raise RunzeCommunicationError("No response received from device!")
        return reply

    return poll


class _Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    async def sleep(self, seconds):
        self.now += seconds


@pytest.fixture
def completion_clock(monkeypatch):
    clock = _Clock()
    monkeypatch.setattr(_common, "time", SimpleNamespace(monotonic=clock))
    monkeypatch.setattr(_common, "asyncio", SimpleNamespace(sleep=clock.sleep))
    return clock


class TestAwaitCompletion:
    async def test_single_dropped_poll_reply_does_not_abort_move(self):
        # Real-hardware failure: one lost 0x4a reply mid-withdraw raised, even
        # though the pump went on to finish the move.
        poll = _scripted_poll(["04", None, "04", "00"])
        status, _ = await await_completion("fe", "0000", poll, poll_interval=0)
        assert status == "00"

    async def test_device_that_stays_silent_still_raises(self):
        poll = _scripted_poll(["04"] + [None] * MAX_MISSED_POLLS)
        with pytest.raises(RunzeCommunicationError):
            await await_completion("fe", "0000", poll, poll_interval=0)

    async def test_missed_poll_counter_resets_after_a_reply(self):
        # Non-consecutive drops are tolerated however many there are in total.
        replies = [None, "04"] * MAX_MISSED_POLLS + ["00"]
        status, _ = await await_completion(
            "fe", "0000", _scripted_poll(replies), poll_interval=0
        )
        assert status == "00"

    async def test_warning_is_logged_for_a_recoverable_missed_poll(self, monkeypatch):
        warnings = []
        monkeypatch.setattr(_common.logger, "warning", warnings.append)
        status, _ = await await_completion(
            "fe", "0000", _scripted_poll([None, "00"]), poll_interval=0
        )
        assert status == "00"
        assert len(warnings) == 1

    async def test_non_raising_silent_device_returns_unconfirmed_status(self):
        status, parameters = await await_completion(
            "fe",
            "1234",
            _scripted_poll([None] * MAX_MISSED_POLLS),
            raise_errors=False,
            poll_interval=0,
        )
        assert (status, parameters) == ("fe", "1234")

    async def test_no_missed_poll_cap_recovers_after_more_than_three_misses(self):
        status, _ = await await_completion(
            "fe",
            "0000",
            _scripted_poll([None] * (MAX_MISSED_POLLS + 1) + ["00"]),
            poll_interval=0,
            max_missed_polls=None,
        )
        assert status == "00"

    @pytest.mark.parametrize("raise_errors", [True, False])
    async def test_configuration_error_is_not_a_recoverable_poll_failure(
        self, raise_errors
    ):
        async def invalid_configuration():
            raise InvalidConfigurationError("Invalid device configuration")

        with pytest.raises(
            InvalidConfigurationError, match="Invalid device configuration"
        ):
            await await_completion(
                "fe",
                "0000",
                invalid_configuration,
                raise_errors=raise_errors,
                poll_interval=0,
            )

    @pytest.mark.parametrize("raise_errors", [True, False])
    async def test_hardware_exception_is_not_a_recoverable_poll_failure(
        self, raise_errors
    ):
        async def hardware_fault():
            raise DeviceError("Motor stalled")

        with pytest.raises(DeviceError, match="Motor stalled"):
            await await_completion(
                "fe", "0000", hardware_fault, raise_errors=raise_errors, poll_interval=0
            )

    async def test_deadline_includes_time_spent_in_status_queries(
        self, completion_clock
    ):
        polls = 0

        async def slow_busy_poll():
            nonlocal polls
            polls += 1
            completion_clock.now += 0.6
            return "04"

        with pytest.raises(DeviceError, match="Motor busy"):
            await await_completion(
                "fe",
                "0000",
                slow_busy_poll,
                poll_interval=0.1,
                max_wait=0.5,
                max_missed_polls=None,
            )
        assert polls == 1

    async def test_idle_from_an_in_flight_poll_is_accepted_after_deadline(
        self, completion_clock
    ):
        async def slow_idle_poll():
            completion_clock.now += 0.6
            return "00"

        status, _ = await await_completion(
            "fe",
            "0000",
            slow_idle_poll,
            poll_interval=0.1,
            max_wait=0.5,
        )
        assert status == "00"

    @pytest.mark.parametrize("raise_errors", [True, False])
    async def test_unlimited_missed_polls_are_still_bounded_by_deadline(
        self, completion_clock, raise_errors
    ):
        polls = 0

        async def silent_poll():
            nonlocal polls
            polls += 1
            completion_clock.now += 0.3
            raise RunzeCommunicationError("Dropped status reply")

        kwargs = dict(
            raise_errors=raise_errors,
            poll_interval=0.1,
            max_wait=0.5,
            max_missed_polls=None,
        )
        if raise_errors:
            with pytest.raises(RunzeCommunicationError, match="Dropped status reply"):
                await await_completion("fe", "0000", silent_poll, **kwargs)
        else:
            assert await await_completion("fe", "0000", silent_poll, **kwargs) == (
                "fe",
                "0000",
            )
        assert 1 <= polls <= 2

    async def test_valid_busy_reply_clears_previous_communication_failure(
        self, completion_clock
    ):
        replies = iter([None, "04"])

        async def poll():
            reply = next(replies)
            completion_clock.now += 0.3
            if reply is None:
                raise RunzeCommunicationError("Dropped status reply")
            return reply

        with pytest.raises(DeviceError, match="Motor busy"):
            await await_completion(
                "fe",
                "0000",
                poll,
                poll_interval=0.1,
                max_wait=0.6,
                max_missed_polls=None,
            )

    async def test_send_helper_forwards_recovery_policy_without_resending(self):
        sends = 0

        async def send():
            nonlocal sends
            sends += 1
            return "fe", "0000"

        status, _ = await send_and_await_completion(
            send,
            _scripted_poll([None] * (MAX_MISSED_POLLS + 1) + ["00"]),
            poll_interval=0,
            max_missed_polls=None,
        )
        assert status == "00"
        assert sends == 1


class TestParseResponse:
    def test_two_byte_parameter_is_not_truncated(self):
        # Manual's own captured trace for "Query reset speed":
        # Rcv: CC 00 00 F9 05 DD A7 02 -> status 00, parameter (B3,B4) = F9 05
        # little-endian = 0x05F9 = 1529.
        status, parameters = RunzeSerialIO.parse_response("cc0000f905dda702")
        assert status == "00"
        assert int(parameters, 16) == 1529

    def test_small_parameter_still_parses_correctly(self):
        # Manual's captured trace for a valve move: Rcv: CC 00 00 00 00 DD A9 01
        status, parameters = RunzeSerialIO.parse_response("cc00000000dda901")
        assert status == "00"
        assert int(parameters, 16) == 0

    def test_task_suspending_status_does_not_raise_when_allowed(self):
        # `fe` ("task suspending") must be observable by callers that poll for
        # completion (see `send_and_await_completion`), not just swallowed.
        status, _ = RunzeSerialIO.parse_response("cc00fe0000dda702", raise_errors=False)
        assert status == "fe"

    @pytest.mark.parametrize(
        "response",
        [
            "",
            "cc000000",
            "cc00000000dda90100",
            "zz00000000dda901",
            "aa00000000dda901",
            "cc00000000eea901",
            "cc00000000dd0000",
        ],
    )
    def test_invalid_frames_are_communication_failures(self, response):
        with pytest.raises(RunzeCommunicationError):
            RunzeSerialIO.parse_response(response, raise_errors=False)

    def test_valid_frame_for_another_address_is_rejected(self):
        with pytest.raises(RunzeCommunicationError):
            RunzeSerialIO.parse_response("cc01000000ddaa01", expected_address=2)

    def test_valid_frame_with_expected_address_is_accepted(self):
        assert RunzeSerialIO.parse_response("cc01000000ddaa01", expected_address=1) == (
            "00",
            "0000",
        )

    def test_hardware_fault_is_preserved_after_frame_validation(self):
        with pytest.raises(DeviceError, match="Motor stalled"):
            RunzeSerialIO.parse_response("cc01050000ddaf01")


class TestRunzeCommandCompile:
    def test_standard_command_matches_manual_trace(self):
        # Manual's "Query reset speed" send: CC 00 4A 00 00 DD F3 01
        command = RunzeCommand(address=0, function_code="4a", parameter=0)
        assert command.compile().lower() == "cc004a0000ddf301"

    def test_factory_command_matches_manual_trace(self):
        # Manual's "Set RS232 baud rate" factory command:
        # CC 00 01 FF EE BB AA 04 00 00 00 DD 00 05
        command = RunzeCommand(
            address=0,
            function_code="01",
            parameter=4,
            is_factory_command=True,
        )
        assert command.compile().lower() == "cc0001ffeebbaa04000000dd0005"
