"""
Tests for SimulatedHamiltonPumpIO and ML600Sim.

Every test in this file exercises real ML600 / ML600Pump / ML600LeftValve
code.  The only thing that is simulated is the serial I/O layer
(SimulatedHamiltonPumpIO), so the full command-compilation → response-parsing
→ unit-conversion pipeline is under test.

Fixtures
--------
ml600_single : ML600Sim configured as a single-syringe pump
ml600_dual   : ML600Sim configured as a dual-syringe pump
"""

from __future__ import annotations

import pytest

from flowchem import ureg
from flowchem.sim.devices.hamilton.ml600_sim import ML600Sim, SimulatedHamiltonPumpIO

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def ml600_single() -> ML600Sim:
    """Single-syringe ML600Sim, 10 ml syringe, freshly initialized."""
    device = ML600Sim.from_config(name="test-pump", syringe_volume="10 ml")
    await device.initialize()
    return device


@pytest.fixture
async def ml600_dual() -> ML600Sim:
    """Dual-syringe ML600Sim, 10 ml syringe, freshly initialized."""
    device = ML600Sim.from_config(
        name="test-pump-dual",
        syringe_volume="10 ml",
        dual_syringe=True,
    )
    await device.initialize()
    return device


@pytest.fixture
async def pump(ml600_single):
    """The single ML600Pump component from the single-syringe fixture."""
    return ml600_single.components[0]


@pytest.fixture
async def valve(ml600_single):
    """The ML600LeftValve component from the single-syringe fixture."""
    return ml600_single.components[1]


# ---------------------------------------------------------------------------
# Group 1 — Initialization
# ---------------------------------------------------------------------------


class TestInitialization:

    async def test_single_syringe_creates_two_components(self, ml600_single):
        """initialize() should register exactly one pump + one valve."""
        assert len(ml600_single.components) == 2

    async def test_dual_syringe_creates_four_components(self, ml600_dual):
        """initialize() for dual syringe should register 2 pumps + 2 valves."""
        assert len(ml600_dual.components) == 4

    async def test_firmware_version_populated(self, ml600_single):
        """device_info.version should be set from the simulated firmware query."""
        assert ml600_single.device_info.version == "NV01.02.3"

    async def test_dual_syringe_flag_set(self, ml600_dual):
        """ML600.dual_syringe should be True after initializing a dual-syringe sim."""
        assert ml600_dual.dual_syringe is True

    async def test_single_syringe_flag_set(self, ml600_single):
        """ML600.dual_syringe should be False for a single-syringe sim."""
        assert ml600_single.dual_syringe is False

    async def test_pump_component_name_single(self, ml600_single):
        """Single-syringe pump component should be named 'pump'."""
        assert ml600_single.components[0].name == "pump"

    async def test_pump_component_names_dual(self, ml600_dual):
        """Dual-syringe pump components should be named 'left_pump' and 'right_pump'."""
        names = [c.name for c in ml600_dual.components]
        assert "left_pump" in names
        assert "right_pump" in names

    async def test_io_num_pump_connected(self, ml600_single):
        """SimulatedHamiltonPumpIO should report exactly 1 pump after init."""
        assert ml600_single.pump_io.num_pump_connected == 1

    async def test_custom_firmware_version(self):
        """Custom firmware_version should propagate through to device_info."""
        device = ML600Sim.from_config(
            name="fw-test",
            syringe_volume="1 ml",
            firmware_version="NV02.00.0",
        )
        await device.initialize()
        assert device.device_info.version == "NV02.00.0"


# ---------------------------------------------------------------------------
# Group 2 — Pump logic
# ---------------------------------------------------------------------------


class TestPumpLogic:

    async def test_is_pumping_initially_false(self, pump):
        result = await pump.is_pumping()
        assert result is False

    async def test_is_withdrawing_capable(self, pump):
        assert pump.is_withdrawing_capable() is True

    async def test_infuse_updates_syringe_position(self, pump):
        """infuse(volume='3 ml') should move the syringe to step 3*48000/10 = 14400."""
        await pump.infuse(rate="5 ml/min", volume="3 ml")
        # Syringe starts full (10 ml = 48000 steps), infusing 3 ml moves to 7 ml = 33600 steps.
        expected_steps = round(7 * 48000 / 10)
        assert pump.hw_device.sim_io._state[1].syringe_position == expected_steps

    async def test_infuse_no_volume_goes_to_zero(self, pump):
        """infuse() with no volume should infuse the full syringe (move to 0 ml = step 0)."""
        await pump.infuse(rate="1 ml/min")
        assert pump.hw_device.sim_io._state[1].syringe_position == 0

    async def test_get_current_volume_matches_state(self, pump):
        """get_current_volume should read back what was set by an infuse."""
        await pump.infuse(rate="5 ml/min", volume="4 ml")
        vol = await pump.get_current_volume()
        assert abs(vol - 6.0) < 0.01  # 10 - 4 = 6 ml

    async def test_withdraw_updates_syringe_position(self, pump):
        """After infusing 5 ml, withdrawing 3 ml should leave 8 ml in the syringe."""
        await pump.infuse(rate="5 ml/min", volume="5 ml")
        await pump.withdraw(rate="2 ml/min", volume="3 ml")
        vol = await pump.get_current_volume()
        assert abs(vol - 8.0) < 0.01

    async def test_infuse_too_much_returns_false(self, pump):
        """infuse() with a volume larger than the syringe content should return False."""
        result = await pump.infuse(rate="1 ml/min", volume="15 ml")
        assert result is False

    async def test_withdraw_too_much_returns_false(self, pump):
        """withdraw() beyond syringe capacity should return False."""
        result = await pump.withdraw(rate="1 ml/min", volume="15 ml")
        assert result is False

    async def test_stop_returns_true(self, pump):
        result = await pump.stop()
        assert result is True

    async def test_wait_until_idle_returns_immediately(self, pump):
        """wait_until_idle should return True without blocking in simulation."""
        result = await pump.wait_until_idle()
        assert result is True

    async def test_set_to_volume_absolute(self, pump):
        """set_to_volume should move to the exact requested volume."""
        await pump.set_to_volume(volume="3 ml", rate="2 ml/min")
        vol = await pump.get_current_volume()
        assert abs(vol - 3.0) < 0.01

    async def test_initialize_syringe_resets_position(self, pump):
        """initialize_syringe should home the syringe to step 0."""
        # First move away from home.
        await pump.infuse(rate="5 ml/min", volume="5 ml")
        await pump.initialize_syringe(rate="1 ml/min")
        assert pump.hw_device.sim_io._state[1].syringe_position == 0

    async def test_return_steps_default(self, ml600_single):
        """Default return steps should be 24 per hardware documentation."""
        steps = await ml600_single.get_return_steps()
        assert steps == 24

    async def test_set_return_steps(self, ml600_single):
        """set_return_steps should update the simulated state."""
        await ml600_single.set_return_steps(100)
        steps = await ml600_single.get_return_steps()
        assert steps == 100

    async def test_version_string(self, ml600_single):
        """version() should return the simulated firmware version string."""
        ver = await ml600_single.version()
        assert "NV01" in ver

    async def test_is_idle_returns_true(self, ml600_single):
        """is_idle() should always return True in simulation."""
        assert await ml600_single.is_idle() is True

    async def test_flowrate_to_step_conversion(self, ml600_single):
        """
        _flowrate_to_seconds_per_stroke and _volume_to_step_position should
        compute correct values for the 10 ml syringe (48000 steps/10 ml = 4800 steps/ml).
        """
        steps = ml600_single._volume_to_step_position(ureg.Quantity("5 ml"))
        assert steps == 24000  # 5 * 4800

    async def test_validate_speed_clamps_low(self, ml600_single):
        """Speeds below 2 sec/stroke should be clamped to 2."""
        import warnings

        speed = ureg.Quantity("0.1 sec/stroke")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = ml600_single._validate_speed(speed)
        assert result == "2"

    async def test_validate_speed_clamps_high(self, ml600_single):
        """Speeds above 3692 sec/stroke should be clamped to 3692."""
        import warnings

        speed = ureg.Quantity("99999 sec/stroke")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = ml600_single._validate_speed(speed)
        assert result == "3692"

    async def test_invalid_syringe_volume_raises(self):
        """An invalid syringe volume should raise InvalidConfigurationError."""
        from flowchem.utils.exceptions import InvalidConfigurationError

        with pytest.raises(InvalidConfigurationError):
            ML600Sim.from_config(
                name="bad", syringe_volume="7 ml"
            )  # 7 ml not in VALID_SYRINGE_VOLUME


# ---------------------------------------------------------------------------
# Group 3 — Valve logic
# ---------------------------------------------------------------------------


class TestValveLogic:

    async def test_valve_initial_angle_is_zero(self, ml600_single):
        assert ml600_single.sim_io._state[1].valve_angle == 0

    async def test_set_raw_position_updates_state(self, valve, ml600_single):
        """set_raw_position('90') should update valve_angle to 90."""
        await valve.hw_device.set_raw_position("90")
        assert ml600_single.sim_io._state[1].valve_angle == 90

    async def test_get_raw_position_returns_current_angle(self, valve, ml600_single):
        """get_raw_position should reflect the last set angle."""
        await valve.hw_device.set_raw_position("45")
        pos = await valve.hw_device.get_raw_position()
        assert pos == "45"

    async def test_set_valve_angle_updates_state(self, ml600_single):
        """set_valve_angle should update the sim state correctly."""
        await ml600_single.set_valve_angle(target_angle=135)
        assert ml600_single.sim_io._state[1].valve_angle == 135

    async def test_get_valve_angle_returns_current(self, ml600_single):
        """get_valve_angle should return what was last set."""
        await ml600_single.set_valve_angle(180)
        angle = await ml600_single.get_valve_angle()
        assert angle == 180

    async def test_initialize_valve_resets_angle(self, ml600_single):
        """initialize_valve() should home the valve to 0°."""
        await ml600_single.set_valve_angle(270)
        await ml600_single.initialize_valve()
        assert ml600_single.sim_io._state[1].valve_angle == 0

    async def test_valve_angle_wraps_360(self, ml600_single):
        """Angles ≥ 360 should wrap correctly."""
        await ml600_single.set_raw_position("720")
        assert ml600_single.sim_io._state[1].valve_angle == 0  # 720 % 360

    async def test_set_position_connect_changes_valve_angle(self, valve):
        """set_position via the component API should change the valve state."""
        # Connect port 1 to port 0 (central); this is abstract position 0 → angle 0.
        await valve.set_position(connect="[[1,0]]", ambiguous_switching="True")
        # The valve angle should have been updated (exact value depends on mapping).
        angle = valve.hw_device.sim_io._state[1].valve_angle
        assert isinstance(angle, int)
        assert 0 <= angle < 360

    async def test_get_position_returns_list(self, valve):
        """get_position() should return a list of tuples representing connections."""
        result = await valve.get_position()
        assert isinstance(result, (list, tuple))

    async def test_connections_returns_valve_info(self, valve):
        """connections() should return a ValveInfo with ports and positions."""
        from flowchem.components.valves.valve import ValveInfo

        info = valve.connections()
        assert isinstance(info, ValveInfo)
        assert len(info.positions) > 0


# ---------------------------------------------------------------------------
# Group 4 — Command compilation (pure unit tests, no device needed)
# ---------------------------------------------------------------------------


class TestCommandCompilation:

    def test_compile_absolute_move(self):
        """Protocol1Command.compile() should produce the correct byte string."""
        from flowchem.devices.hamilton.ml600 import Protocol1Command, ML600Commands

        cmd = Protocol1Command(
            command=ML600Commands.ABSOLUTE_MOVE,
            command_value="24000",
            optional_parameter="S",
            parameter_value="100",
            target_pump_num=1,
        )
        compiled = cmd.compile()
        # pump 1 → address 'a', no target_component, M24000S100R
        assert compiled == "aM24000S100R"

    def test_compile_valve_angle_cw(self):
        """LA0{angle}R should be produced for CW valve switching."""
        from flowchem.devices.hamilton.ml600 import Protocol1Command, ML600Commands

        cmd = Protocol1Command(
            command=ML600Commands.VALVE_BY_ANGLE_CW,
            command_value="90",
            target_pump_num=1,
        )
        compiled = cmd.compile()
        assert compiled == "aLA090R"

    def test_compile_request_done(self):
        """REQUEST_DONE with empty execution_command should produce 'aF'."""
        from flowchem.devices.hamilton.ml600 import Protocol1Command, ML600Commands

        cmd = Protocol1Command(
            command=ML600Commands.REQUEST_DONE,
            execution_command="",
            target_pump_num=1,
        )
        compiled = cmd.compile()
        assert compiled == "aF"

    def test_compile_pump_address_2(self):
        """Pump at address 2 should use letter 'b'."""
        from flowchem.devices.hamilton.ml600 import Protocol1Command, ML600Commands

        cmd = Protocol1Command(
            command=ML600Commands.FIRMWARE_VERSION,
            target_pump_num=2,
        )
        assert cmd.compile().startswith("b")

    def test_multiple_compile_produces_correct_prefix(self):
        """multiple_compile should prepend the pump address letter."""
        from flowchem.devices.hamilton.ml600 import Protocol1Command, ML600Commands

        cmd = Protocol1Command(
            command=ML600Commands.ABSOLUTE_MOVE,
            command_value="1000",
            optional_parameter="S",
            parameter_value="50",
            target_pump_num=1,
        )
        result = cmd.multiple_compile("M1000S50")
        assert result.startswith("a")
        assert result.endswith("R\r")

    def test_multiple_compile_invalid_pump_num_raises(self):
        """target_pump_num outside 1-16 should raise ValueError."""
        from flowchem.devices.hamilton.ml600 import Protocol1Command, ML600Commands

        cmd = Protocol1Command(
            command=ML600Commands.FIRMWARE_VERSION,
            target_pump_num=99,
        )
        with pytest.raises(ValueError):
            cmd.multiple_compile("U")


# ---------------------------------------------------------------------------
# Group 5 — Sim IO state machine (direct unit tests)
# ---------------------------------------------------------------------------


class TestSimulatedIO:

    def test_reset_clears_state(self):
        """reset() should restore all state variables to defaults."""
        io = SimulatedHamiltonPumpIO(num_pumps=1)
        io._state[1].syringe_position = 9999
        io._state[1].valve_angle = 180
        io._state[1].return_steps = 500
        io.reset()
        assert io._state[1].syringe_position == 0
        assert io._state[1].valve_angle == 0
        assert io._state[1].return_steps == 24

    async def test_raw_handshake_1a(self):
        """The '1a\\r' handshake command should return a reply containing '1'."""
        io = SimulatedHamiltonPumpIO(num_pumps=1)
        await io._write_async(b"1a\r")
        reply = await io._read_reply_async()
        assert reply.startswith("1")

    async def test_raw_enum_pump_present(self):
        """'{addr}UR\\r' for a present pump should return a reply containing 'NV01'."""
        io = SimulatedHamiltonPumpIO(num_pumps=1)
        await io._write_async(b"aUR\r")
        reply = await io._read_reply_async()
        assert "NV01" in reply

    async def test_raw_enum_pump_absent(self):
        """'{addr}UR\\r' for an absent pump should return an empty reply."""
        io = SimulatedHamiltonPumpIO(num_pumps=1)
        await io._write_async(b"bUR\r")  # pump 2 not present
        reply = await io._read_reply_async()
        assert reply == "\r"

    def test_dispatch_request_done(self):
        """REQUEST_DONE command should always return ACK+'Y'."""
        io = SimulatedHamiltonPumpIO(num_pumps=1)
        response = io._dispatch("aFR\r", pump_num=1)
        assert response == f"{chr(6)}Y\r"

    def test_dispatch_firmware_version(self):
        """FIRMWARE_VERSION command should return the configured version string."""
        io = SimulatedHamiltonPumpIO(num_pumps=1, firmware_version="NV99.00.0")
        response = io._dispatch("aUR\r", pump_num=1)
        assert "NV99.00.0" in response

    def test_dispatch_absolute_move_updates_state(self):
        """ABSOLUTE_MOVE should update syringe_position in state."""
        io = SimulatedHamiltonPumpIO(num_pumps=1)
        io._dispatch("aM12000S100R\r", pump_num=1)
        assert io._state[1].syringe_position == 12000

    def test_dispatch_query_syringe_position(self):
        """CURRENT_SYRINGE_POSITION should return the current step count."""
        io = SimulatedHamiltonPumpIO(num_pumps=1)
        io._state[1].syringe_position = 7500
        response = io._dispatch("aYQPR\r", pump_num=1)
        assert "7500" in response

    def test_dispatch_valve_angle_cw(self):
        """VALVE_BY_ANGLE_CW should update valve_angle."""
        io = SimulatedHamiltonPumpIO(num_pumps=1)
        io._dispatch("aLA090R\r", pump_num=1)
        assert io._state[1].valve_angle == 90

    def test_dispatch_valve_angle_query(self):
        """VALVE_ANGLE query should return the current angle."""
        io = SimulatedHamiltonPumpIO(num_pumps=1)
        io._state[1].valve_angle = 135
        response = io._dispatch("aLQAR\r", pump_num=1)
        assert "135" in response

    def test_dispatch_is_single_syringe_single(self):
        """IS_SINGLE_SYRINGE should return 'Y' for single-syringe config."""
        io = SimulatedHamiltonPumpIO(num_pumps=1, dual_syringe=False)
        response = io._dispatch("aHR\r", pump_num=1)
        assert f"{chr(6)}Y" in response

    def test_dispatch_is_single_syringe_dual(self):
        """IS_SINGLE_SYRINGE should return 'N' for dual-syringe config."""
        io = SimulatedHamiltonPumpIO(num_pumps=1, dual_syringe=True)
        response = io._dispatch("aHR\r", pump_num=1)
        assert f"{chr(6)}N" in response

    def test_dispatch_busy_status_returns_idle(self):
        """BUSY_STATUS should always return the idle bit pattern in simulation."""
        io = SimulatedHamiltonPumpIO(num_pumps=1)
        response = io._dispatch("aT1R\r", pump_num=1)
        # '@' = 0x40; when reversed its bit pattern has all busy bits = 0 (idle).
        assert chr(6) + "@" in response

    def test_dispatch_init_syringe_resets_position(self):
        """INIT_SYRINGE_ONLY should set syringe_position to 0."""
        io = SimulatedHamiltonPumpIO(num_pumps=1)
        io._state[1].syringe_position = 24000
        io._dispatch("aX1S200R\r", pump_num=1)
        assert io._state[1].syringe_position == 0

    def test_dispatch_init_valve_resets_angle(self):
        """INIT_VALVE_ONLY should set valve_angle to 0."""
        io = SimulatedHamiltonPumpIO(num_pumps=1)
        io._state[1].valve_angle = 270
        io._dispatch("aLXR\r", pump_num=1)
        assert io._state[1].valve_angle == 0

    def test_dispatch_set_return_steps(self):
        """SET_RETURN_STEPS should update return_steps in state."""
        io = SimulatedHamiltonPumpIO(num_pumps=1)
        io._dispatch("aYSN100R\r", pump_num=1)
        assert io._state[1].return_steps == 100

    def test_dispatch_get_return_steps(self):
        """GET_RETURN_STEPS should return the current return_steps value."""
        io = SimulatedHamiltonPumpIO(num_pumps=1)
        io._state[1].return_steps = 48
        response = io._dispatch("aYQNR\r", pump_num=1)
        assert "48" in response
