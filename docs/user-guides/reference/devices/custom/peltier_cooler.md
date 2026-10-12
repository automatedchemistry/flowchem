# Peltier Cooler

The Peltier Cooler is a custom temperature controller driven by a TEC05-24 or TEC16-24
Peltier controller board. It is exposed in Flowchem as a `temperature_control` component,
supporting setting/reading a temperature setpoint, checking whether the target has been
reached, and turning the temperature regulation loop on and off.

## Configuration
Configuration sample showing all possible parameters:

```toml
[device.my-peltier]
type = "PeltierCooler"        # This is the device identifier
port = "COM17"                # Serial port name (e.g., 'COM3') for Serial communication
address = 0                   # Peltier controller bus address (0-98)
peltier_defaults = "default"  # Optional, see below

# Optional overrides applied on top of the selected preset above.
# Any subset may be given; omitted values fall back to the preset's value.
heating_pid = [0.64, 0.53, 0.13]   # [P, I, D] used above base_temp
cooling_pid = [2.83, 2.36, 0.59]   # [P, I, D] used at/below base_temp
base_temp = -7.6                   # °C threshold switching between heating/cooling PID
t_max = 50                         # °C, upper temperature limit
t_min = -55                        # °C, lower temperature limit
state_dependent_data = [           # current-limit curve, must have exactly 3 rows:
    [-55, 50],                     #   temperature breakpoints (°C)
    [14, 14],                      #   cooling current limit at each breakpoint (A)
    [10, 10],                      #   heating current limit at each breakpoint (A)
]
```

```{note} Bus address
`0` above is just a placeholder value, not a safe default. Each physical controller has its
own configured bus address (set on the device itself), and commands sent with the wrong
address will fail (e.g. with a `COMMAND ERR` reply) even though the serial connection itself
is working. Make sure `address` matches the actual address of the connected unit.
```

`peltier_defaults` selects a preset profile of temperature range, PID and current-limit
parameters that are pushed to the controller on initialization. Available profiles:

| Value | Temperature range |
|---|---|
| `"default"` (or omitted) | -55 to 50 °C |
| `"low_cooling"` | -66 to 30 °C |
| `"tube_reactor"` | -55 to 25 °C |
| `"tube_reactor_chiller_2"` | -55 to 25 °C |

Each of `heating_pid`, `cooling_pid`, `base_temp`, `t_max`, `t_min` and
`state_dependent_data` may optionally be set directly in the config file to override
the corresponding value from the selected `peltier_defaults` preset. This is useful
when a preset is a good starting point but the specific application (e.g. a different
reactor volume or heat sink) needs a custom current-limit curve or temperature range.
For example, `peltier_defaults = "tube_reactor"` with only `t_max = 30` set will use
all of the `tube_reactor` preset's values except for `T_MAX`.

`state_dependent_data` must have exactly 3 rows (temperature breakpoints, cooling
current limits, heating current limits), each the same length; a mismatched row count
raises a configuration error at startup rather than failing later during operation.

Communication by Serial Port
```{note} Serial connection parameters
Further parameters for the serial connection (i.e. those accepted by `serial.Serial`) such as
`baudrate`, `parity`, `stopbits`, `bytesize` and `timeout` can be specified.
However, it should not be necessary as the following values (which are the default for the
instrument) are automatically used:
baudrate 115200,  # Fixed baudrate
timeout 0.1,      # Timeout in seconds
parity None,      # Parity: None (fixed)
stopbits 1,       # Stopbits: 1 (fixed)
bytesize 8        # Data: 8 bits (fixed)
```

## API methods

See the [device API reference](../../api/peltier_cooler/api.md) for a description of the
available methods, which include:

* `set_temperature` / `get_temperature`
* `get_temperature_setpoint`
* `power_on` / `power_off` — start/stop the regulation loop
* `is_target_reached` / `is_idle`
* `parameters` — combined configured (TOML) defaults and live hardware GPA readback

## Hardware & protocol reference

The controller boards driven by this device are the Schulz-Electronic/head electronic
**TEC05-12/TEC05-24** and **TEC16-12/TEC16-24/TEC16-32** TEC-Controllers. The vendor's
full operating manual, including the ASCII command set used by this driver, is included
alongside this page: [TEC05-12_16-32.pdf](TEC05-12_16-32.pdf).

### Serial protocol

Commands are plain ASCII, newline-terminated, and prefixed with the two-digit bus
`address` (e.g. `11 STV 2000\n`). Replies echo the address followed by `KEY=VALUE`
(e.g. `11 TEMP_SET=20.00 C`). Numeric arguments/values for temperatures and PID
factors are transmitted as the real value ×100 (i.e. two implied decimal places).
Malformed commands, out-of-range parameters, or wrong-address replies produce
`COMMAND ERR` / `FORMAT ERR` / `NUMBER ERR` respectively — see
`PeltierIO.check_for_errors` in
[peltier_cooler.py](../../../../../src/flowchem/devices/custom/peltier_cooler.py).

### Command reference

Mapping between the `PeltierCommands` used by this driver and the vendor's own
command mnemonics (manual Anhang II, "TEC-Controller ASCII Befehlssatz"):

| `PeltierCommands` | Vendor command | Description | Reply |
|---|---|---|---|
| `GET_TEMPERATURE` | `GT1` | Sensor 1 temperature reading | `TEMP1=x.xx C` |
| `GET_SINK_TEMPERATURE` | `GT2` | Sensor 2 temperature reading (heat-sink side) | `TEMP2=x.xx C` |
| `SET_TEMPERATURE` | `STV` | Setpoint temperature | `TEMP_SET=xxx.xx C` |
| `SET_SLOPE` | `STS` | Setpoint ramp rate (0 = step change) | `TEMP_SLOPE=xx.xx C/s` |
| `SWITCH_ON` | `SEN` | Enable the regulation loop | `STATUS=x` |
| `SWITCH_OFF` | `SDI` | Disable the regulation loop | `STATUS=0` |
| `COOLING_CURRENT_LIMIT` | `SCC` | Negative ("cooling") current limit | `COOL_C_LIMIT=xx.xx A` |
| `HEATING_CURRENT_LIMIT` | `SHC` | Positive ("heating") current limit | `HEAT_C_LIMIT=xx.xx A` |
| `SET_PROPORTIONAL_PID` | `SPF` | PID proportional factor (P) | `P_FACTOR=xx.xx` |
| `SET_INTEGRAL_PID` | `SIF` | PID integral factor (I) | `I_FACTOR=xx.xx` |
| `SET_DIFFERENTIAL_PID` | `SDF` | PID differential factor (D) — see note below | `D_FACTOR=xx.xx` |
| `SET_T_MAX` | `SMA` | Upper temperature limit | `TEMP_MAX=xxx.xx C` |
| `SET_T_MIN` | `SMI` | Lower temperature limit | `TEMP_MIN=xxx.xx C` |
| `GET_POWER` | `GCU` | Actual current draw — see note below | `CURRENT=x.xx A` |
| `GET_CURRENT` | `GPW` | Actual power draw — see note below | `POWER=x W` |
| `GET_SETTINGS` | `GPA` | Full parameter dump (see table below) | `PARAMS=...` |

```{note} Undocumented D-factor command
`SDF`/`D_FACTOR` (the PID derivative term) does not appear in this manual revision's
command tables at all, yet it works against real hardware and is present in the
vendor's own (newer) configuration GUI. It's a firmware addition postdating this PDF —
treat it as confirmed-by-observation rather than vendor-documented.
```

```{warning} `get_power()` / `get_current()` naming
Per the vendor manual, `GCU` ("Ist-Strom") reports **current** and `GPW`
("TEC-Leistung") reports **power** — the opposite of what `PeltierCooler.get_power()`
(which sends `GCU`) and `.get_current()` (which sends `GPW`) suggest. Until this is
fixed in code, treat the *values* returned by these two methods as swapped relative to
their names: `get_power()` currently returns amps, `get_current()` currently returns
watts.
```

### `GPA` field reference

`GET_SETTINGS`/`GPA` returns a single comma-separated line dumping the controller's
internal parameter table (exposed as `live.raw_gpa_reply` by the `parameters`
component endpoint). The manual documents the following field order (1-indexed):

| # | Field |
|---|---|
| 1 | Setpoint temperature |
| 2–3 | *(undocumented in this manual revision)* |
| 4 | Heating current limit |
| 5 | Cooling current limit |
| 6 | P factor |
| 7 | I factor |
| 8 | "Temperature OK" positive threshold |
| 9 | "Temperature OK" negative threshold |
| 10 | Minimum temperature (`T_MIN`) |
| 11 | Maximum temperature (`T_MAX`) |
| 12 | Auto-enable active |
| 13 | Use analog setpoint input |
| 14 | Sensor 1 cutoff temperature |
| 15 | Max. temperature delta, sensors 1/2 |
| 16 | Control sensor selection |
| 17 | Sensor 2 cutoff temperature |
| 18 | Sensor 3 cutoff temperature |
| 19 | Fan control sensor |
| 20 | Fan control temperature delta |
| 21 | Fan control ambient temperature |
| 22 | Fan control max power |
| 23 | Sensor 1 coefficient |
| 24 | Sensor 1 zero-point offset |
| 25 | Sensor 2 coefficient |
| 26 | Sensor 2 zero-point offset |
| 27–29 | Aux I/O 1–3 |
| 30–35 | Aux 1–3 lower/upper temperature limits |
| 36 | Setpoint ramp rate |
| 37 | Enable via digital input |
| 38 | Buzzer active |
| 39 | Fan tach pulses per revolution |

```{note} Real replies may be longer than this table
On the firmware tested this session, the real reply had ~51 fields rather than the 39
listed above — extra, undocumented fields (including D-factor) are appended after
field 39. Field order beyond #39 is not vendor-documented and was not decoded.
```

## Further information:

More detail can be found as a docstring in the
[main class](../../../../../src/flowchem/devices/custom/peltier_cooler.py).

# Peltier Cooler

The Peltier Cooler is a custom temperature controller driven by a TEC05-24 or TEC16-24
Peltier controller board. It is exposed in Flowchem as a `temperature_control` component,
supporting setting/reading a temperature setpoint, checking whether the target has been
reached, and turning the temperature regulation loop on and off.

## Configuration
Configuration sample showing all possible parameters:

```toml
[device.my-peltier]
type = "PeltierCooler"        # This is the device identifier
port = "COM17"                # Serial port name (e.g., 'COM3') for Serial communication
address = 0                   # Peltier controller bus address (0-98)
peltier_defaults = "default"  # Optional, see below

# Optional overrides applied on top of the selected preset above.
# Any subset may be given; omitted values fall back to the preset's value.
heating_pid = [0.64, 0.53, 0.13]   # [P, I, D] used above base_temp
cooling_pid = [2.83, 2.36, 0.59]   # [P, I, D] used at/below base_temp
base_temp = -7.6                   # °C threshold switching between heating/cooling PID
t_max = 50                         # °C, upper temperature limit
t_min = -55                        # °C, lower temperature limit
state_dependent_data = [           # current-limit curve, must have exactly 3 rows:
    [-55, 50],                     #   temperature breakpoints (°C)
    [14, 14],                      #   cooling current limit at each breakpoint (A)
    [10, 10],                      #   heating current limit at each breakpoint (A)
]
```

```{note} Bus address
`0` above is just a placeholder value, not a safe default. Each physical controller has its
own configured bus address (set on the device itself), and commands sent with the wrong
address will fail (e.g. with a `COMMAND ERR` reply) even though the serial connection itself
is working. Make sure `address` matches the actual address of the connected unit.
```

`peltier_defaults` selects a preset profile of temperature range, PID and current-limit
parameters that are pushed to the controller on initialization. Available profiles:

| Value | Temperature range |
|---|---|
| `"default"` (or omitted) | -55 to 50 °C |
| `"low_cooling"` | -66 to 30 °C |
| `"tube_reactor"` | -55 to 25 °C |
| `"tube_reactor_chiller_2"` | -55 to 25 °C |

Each of `heating_pid`, `cooling_pid`, `base_temp`, `t_max`, `t_min` and
`state_dependent_data` may optionally be set directly in the config file to override
the corresponding value from the selected `peltier_defaults` preset. This is useful
when a preset is a good starting point but the specific application (e.g. a different
reactor volume or heat sink) needs a custom current-limit curve or temperature range.
For example, `peltier_defaults = "tube_reactor"` with only `t_max = 30` set will use
all of the `tube_reactor` preset's values except for `T_MAX`.

`state_dependent_data` must have exactly 3 rows (temperature breakpoints, cooling
current limits, heating current limits), each the same length; a mismatched row count
raises a configuration error at startup rather than failing later during operation.

Communication by Serial Port
```{note} Serial connection parameters
Further parameters for the serial connection (i.e. those accepted by `serial.Serial`) such as
`baudrate`, `parity`, `stopbits`, `bytesize` and `timeout` can be specified.
However, it should not be necessary as the following values (which are the default for the
instrument) are automatically used:
baudrate 115200,  # Fixed baudrate
timeout 0.1,      # Timeout in seconds
parity None,      # Parity: None (fixed)
stopbits 1,       # Stopbits: 1 (fixed)
bytesize 8        # Data: 8 bits (fixed)
```

## API methods

See the [device API reference](../../api/peltier_cooler/api.md) for a description of the
available methods, which include:

* `set_temperature` / `get_temperature`
* `get_temperature_setpoint`
* `power_on` / `power_off` — start/stop the regulation loop
* `is_target_reached` / `is_idle`

## Hardware & protocol reference

The controller boards driven by this device are the Schulz-Electronic/head electronic
**TEC05-12/TEC05-24** and **TEC16-12/TEC16-24/TEC16-32** TEC-Controllers. The vendor's
full operating manual, including the ASCII command set used by this driver, is included
alongside this page: [TEC05-12_16-32.pdf](TEC05-12_16-32.pdf).

### Serial protocol

Commands are plain ASCII, newline-terminated, and prefixed with the two-digit bus
`address` (e.g. `11 STV 2000\n`). Replies echo the address followed by `KEY=VALUE`
(e.g. `11 TEMP_SET=20.00 C`). Numeric arguments/values for temperatures and PID
factors are transmitted as the real value ×100 (i.e. two implied decimal places).
Malformed commands, out-of-range parameters, or wrong-address replies produce
`COMMAND ERR` / `FORMAT ERR` / `NUMBER ERR` respectively — see
`PeltierIO.check_for_errors` in
[peltier_cooler.py](../../../../../src/flowchem/devices/custom/peltier_cooler.py).

### Command reference

Mapping between the `PeltierCommands` used by this driver and the vendor's own
command mnemonics (manual Anhang II, "TEC-Controller ASCII Befehlssatz"):

| `PeltierCommands` | Vendor command | Description | Reply |
|---|---|---|---|
| `GET_TEMPERATURE` | `GT1` | Sensor 1 temperature reading | `TEMP1=x.xx C` |
| `GET_SINK_TEMPERATURE` | `GT2` | Sensor 2 temperature reading (heat-sink side) | `TEMP2=x.xx C` |
| `SET_TEMPERATURE` | `STV` | Setpoint temperature | `TEMP_SET=xxx.xx C` |
| `SET_SLOPE` | `STS` | Setpoint ramp rate (0 = step change) | `TEMP_SLOPE=xx.xx C/s` |
| `SWITCH_ON` | `SEN` | Enable the regulation loop | `STATUS=x` |
| `SWITCH_OFF` | `SDI` | Disable the regulation loop | `STATUS=0` |
| `COOLING_CURRENT_LIMIT` | `SCC` | Negative ("cooling") current limit | `COOL_C_LIMIT=xx.xx A` |
| `HEATING_CURRENT_LIMIT` | `SHC` | Positive ("heating") current limit | `HEAT_C_LIMIT=xx.xx A` |
| `SET_PROPORTIONAL_PID` | `SPF` | PID proportional factor (P) | `P_FACTOR=xx.xx` |
| `SET_INTEGRAL_PID` | `SIF` | PID integral factor (I) | `I_FACTOR=xx.xx` |
| `SET_DIFFERENTIAL_PID` | `SDF` | PID differential factor (D) — see note below | `D_FACTOR=xx.xx` |
| `SET_T_MAX` | `SMA` | Upper temperature limit | `TEMP_MAX=xxx.xx C` |
| `SET_T_MIN` | `SMI` | Lower temperature limit | `TEMP_MIN=xxx.xx C` |
| `GET_POWER` | `GCU` | Actual current draw — see note below | `CURRENT=x.xx A` |
| `GET_CURRENT` | `GPW` | Actual power draw — see note below | `POWER=x W` |
| `GET_SETTINGS` | `GPA` | Full parameter dump (see table below) | `PARAMS=...` |

```{note} Undocumented D-factor command
`SDF`/`D_FACTOR` (the PID derivative term) does not appear in this manual revision's
command tables at all, yet it works against real hardware and is present in the
vendor's own (newer) configuration GUI. It's a firmware addition postdating this PDF —
treat it as confirmed-by-observation rather than vendor-documented.
```

```{warning} `get_power()` / `get_current()` naming
Per the vendor manual, `GCU` ("Ist-Strom") reports **current** and `GPW`
("TEC-Leistung") reports **power** — the opposite of what `PeltierCooler.get_power()`
(which sends `GCU`) and `.get_current()` (which sends `GPW`) suggest. Until this is
fixed in code, treat the *values* returned by these two methods as swapped relative to
their names: `get_power()` currently returns amps, `get_current()` currently returns
watts.
```

### `GPA` field reference

`GET_SETTINGS`/`GPA` returns a single comma-separated line dumping the controller's
internal parameter table (exposed as `live.raw_gpa_reply` by the `parameters`
component endpoint). The manual documents the following field order (1-indexed):

| # | Field |
|---|---|
| 1 | Setpoint temperature |
| 2–3 | *(undocumented in this manual revision)* |
| 4 | Heating current limit |
| 5 | Cooling current limit |
| 6 | P factor |
| 7 | I factor |
| 8 | "Temperature OK" positive threshold |
| 9 | "Temperature OK" negative threshold |
| 10 | Minimum temperature (`T_MIN`) |
| 11 | Maximum temperature (`T_MAX`) |
| 12 | Auto-enable active |
| 13 | Use analog setpoint input |
| 14 | Sensor 1 cutoff temperature |
| 15 | Max. temperature delta, sensors 1/2 |
| 16 | Control sensor selection |
| 17 | Sensor 2 cutoff temperature |
| 18 | Sensor 3 cutoff temperature |
| 19 | Fan control sensor |
| 20 | Fan control temperature delta |
| 21 | Fan control ambient temperature |
| 22 | Fan control max power |
| 23 | Sensor 1 coefficient |
| 24 | Sensor 1 zero-point offset |
| 25 | Sensor 2 coefficient |
| 26 | Sensor 2 zero-point offset |
| 27–29 | Aux I/O 1–3 |
| 30–35 | Aux 1–3 lower/upper temperature limits |
| 36 | Setpoint ramp rate |
| 37 | Enable via digital input |
| 38 | Buzzer active |
| 39 | Fan tach pulses per revolution |

```{note} Real replies may be longer than this table
On the firmware tested this session, the real reply had ~51 fields rather than the 39
listed above — extra, undocumented fields (including D-factor) are appended after
field 39. Field order beyond #39 is not vendor-documented and was not decoded.
```

## Further information:

More detail can be found as a docstring in the
[main class](../../../../../src/flowchem/devices/custom/peltier_cooler.py).
