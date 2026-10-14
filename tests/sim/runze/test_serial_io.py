"""Exercise Runze's real byte transport with an in-memory serial connection."""

import asyncio
import threading
from types import SimpleNamespace

import pytest

from flowchem.devices.runze import _common
from flowchem.devices.runze._common import (
    RunzeCommand,
    RunzeCommunicationError,
    RunzeSerialIO,
)
from flowchem.utils.exceptions import DeviceError


def _reply(address=1, status=0, parameter=0):
    data = bytes([0xCC, address, status, parameter & 0xFF, parameter >> 8, 0xDD])
    return data + sum(data).to_bytes(2, "little")


class _Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


class _ScriptedSerial:
    port = "FAKE-RUNZE"
    name = port

    def __init__(self, chunks, clock, timeout=3.0, read_delay=0.01, start_delay=0.0):
        self.chunks = list(chunks)
        self.clock = clock
        self.timeout = timeout
        self.read_delay = read_delay
        self.start_delay = start_delay
        self.writes = []
        self.read_timeouts = []
        self.events = []

    def reset_input_buffer(self):
        self.events.append(("reset", threading.get_ident()))
        self.clock.now += self.start_delay

    def write(self, data):
        self.events.append(("write", threading.get_ident()))
        self.writes.append(data)
        return len(data)

    def read(self, size):
        self.events.append(("read", threading.get_ident()))
        self.read_timeouts.append(self.timeout)
        if not self.chunks:
            self.clock.now += self.timeout or 0
            return b""
        chunk = self.chunks.pop(0)
        if isinstance(chunk, Exception):
            raise chunk
        self.clock.now += (
            min(self.read_delay, self.timeout)
            if self.timeout is not None
            else self.read_delay
        )
        if len(chunk) > size:
            self.chunks.insert(0, chunk[size:])
        return chunk[:size]


@pytest.fixture
def io_factory(monkeypatch):
    instances = []
    clock = _Clock()
    monkeypatch.setattr(_common, "time", SimpleNamespace(monotonic=clock))

    def make(chunks, **kwargs):
        serial_connection = _ScriptedSerial(chunks, clock, **kwargs)
        io = RunzeSerialIO(serial_connection)
        instances.append(io)
        return io, serial_connection, clock

    yield make
    for io in instances:
        io._io_executor.shutdown(wait=True)


async def test_fragmented_reply_is_assembled_without_resending(io_factory):
    reply = _reply(parameter=1529)
    io, serial_connection, _ = io_factory(
        [reply[:1], reply[1:3], reply[3:5], reply[5:]]
    )

    assert await io.write_and_read_reply_async(RunzeCommand(1, "66")) == ("00", "05f9")
    assert len(serial_connection.writes) == 1


async def test_leading_garbage_is_discarded_before_valid_reply(io_factory):
    io, serial_connection, _ = io_factory([b"garbage" + _reply(parameter=512)])

    assert await io.write_and_read_reply_async(RunzeCommand(1, "66")) == ("00", "0200")
    assert len(serial_connection.writes) == 1


async def test_reply_for_another_address_is_discarded(io_factory):
    io, serial_connection, _ = io_factory(
        [_reply(address=2, parameter=999) + _reply(parameter=512)]
    )

    assert await io.write_and_read_reply_async(RunzeCommand(1, "66")) == ("00", "0200")
    assert len(serial_connection.writes) == 1


@pytest.mark.parametrize(
    "corrupted",
    [
        bytes.fromhex("cc01000000eeaa01"),
        bytes.fromhex("cc01000000dd0000"),
    ],
)
async def test_corrupted_frame_is_discarded_before_valid_reply(io_factory, corrupted):
    io, serial_connection, _ = io_factory([corrupted + _reply(parameter=512)])

    assert await io.write_and_read_reply_async(RunzeCommand(1, "66")) == ("00", "0200")
    assert len(serial_connection.writes) == 1


@pytest.mark.parametrize("chunks", [[], [b"\xcc\x01\x00"], [_reply(address=2)]])
async def test_missing_complete_matching_reply_raises_communication_error(
    io_factory, chunks
):
    io, _, _ = io_factory(chunks)

    with pytest.raises(RunzeCommunicationError):
        await io.write_and_read_reply_async(RunzeCommand(1, "4a"), raise_errors=False)


async def test_garbage_does_not_restart_read_deadline(io_factory):
    io, serial_connection, clock = io_factory([b"junk"] * 100, read_delay=0.4)

    with pytest.raises(RunzeCommunicationError):
        await io.write_and_read_reply_async(RunzeCommand(1, "4a"), read_timeout=1.0)

    assert clock.now == pytest.approx(1.0)
    assert serial_connection.read_timeouts == pytest.approx([1.0, 0.6, 0.2])
    assert len(serial_connection.writes) == 1
    assert serial_connection.timeout == 3.0


async def test_exchange_setup_time_counts_against_read_deadline(io_factory):
    io, serial_connection, clock = io_factory([], start_delay=0.8)

    with pytest.raises(RunzeCommunicationError):
        await io.write_and_read_reply_async(RunzeCommand(1, "4a"), read_timeout=1.0)

    assert serial_connection.read_timeouts == pytest.approx([0.2])
    assert clock.now == pytest.approx(1.0)
    assert serial_connection.timeout == 3.0


@pytest.mark.parametrize("chunks", [[_reply()], []])
async def test_original_serial_timeout_is_restored_after_success_or_failure(
    io_factory, chunks
):
    io, serial_connection, _ = io_factory(chunks, timeout=4.0)

    if chunks:
        assert await io.write_and_read_reply_async(
            RunzeCommand(1, "4a"), read_timeout=0.5
        ) == ("00", "0000")
    else:
        with pytest.raises(RunzeCommunicationError):
            await io.write_and_read_reply_async(RunzeCommand(1, "4a"), read_timeout=0.5)

    assert serial_connection.read_timeouts[0] == pytest.approx(0.5)
    assert serial_connection.timeout == 4.0


async def test_original_serial_timeout_is_restored_after_read_exception(io_factory):
    io, serial_connection, _ = io_factory([OSError("Read backend failed")], timeout=4.0)

    with pytest.raises(OSError, match="Read backend failed"):
        await io.write_and_read_reply_async(RunzeCommand(1, "4a"), read_timeout=0.5)
    assert serial_connection.timeout == 4.0


async def test_valid_hardware_fault_preserves_device_error(io_factory):
    io, _, _ = io_factory([_reply(status=5)])

    with pytest.raises(DeviceError, match="Motor stalled"):
        await io.write_and_read_reply_async(RunzeCommand(1, "4a"))


async def test_parallel_callers_keep_each_exchange_on_one_serial_thread(io_factory):
    io, serial_connection, _ = io_factory([_reply(address=1), _reply(address=2)])

    replies = await asyncio.gather(
        io.write_and_read_reply_async(RunzeCommand(1, "4a"), read_timeout=0.5),
        io.write_and_read_reply_async(RunzeCommand(2, "4a"), read_timeout=1.0),
    )

    assert replies == [("00", "0000"), ("00", "0000")]
    assert [event for event, _ in serial_connection.events] == [
        "reset",
        "write",
        "read",
    ] * 2
    thread_ids = {thread_id for _, thread_id in serial_connection.events}
    assert len(thread_ids) == 1
    assert threading.get_ident() not in thread_ids
    assert serial_connection.read_timeouts == pytest.approx([0.5, 1.0])
    assert serial_connection.timeout == 3.0


async def test_nonblocking_read_has_one_attempt_without_busy_loop(io_factory):
    io, serial_connection, _ = io_factory([], timeout=0)

    with pytest.raises(RunzeCommunicationError):
        await io.write_and_read_reply_async(RunzeCommand(1, "4a"))

    assert len(serial_connection.read_timeouts) == 1


async def test_nonblocking_read_accepts_a_complete_reply(io_factory):
    io, serial_connection, _ = io_factory([_reply()], timeout=0)

    assert await io.write_and_read_reply_async(RunzeCommand(1, "4a")) == ("00", "0000")
    assert serial_connection.read_timeouts == [0]
    assert serial_connection.timeout == 0


async def test_blocking_read_retains_none_timeout_across_fragments(io_factory):
    reply = _reply()
    io, serial_connection, _ = io_factory([reply[:4], reply[4:]], timeout=None)

    assert await io.write_and_read_reply_async(RunzeCommand(1, "4a")) == ("00", "0000")
    assert serial_connection.read_timeouts == [None, None]
    assert serial_connection.timeout is None
