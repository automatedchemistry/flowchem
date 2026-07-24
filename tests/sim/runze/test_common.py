"""Regression tests for the shared Runze protocol primitives in `_common.py`.

Fixtures here are worked byte examples taken directly from the vendor's
"Smart SY-01-Syringe" and "SV-06-Multiport Valve" manuals, so these don't
need real hardware to verify against.
"""

from flowchem.devices.runze._common import RunzeCommand, RunzeSerialIO


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
        status, _ = RunzeSerialIO.parse_response("cc00fe0000dd0000", raise_errors=False)
        assert status == "fe"


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
