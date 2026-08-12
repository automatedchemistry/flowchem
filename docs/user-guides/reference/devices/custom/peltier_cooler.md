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

## Further information:

More detail can be found as a docstring in the
[main class](../../../../../src/flowchem/devices/custom/peltier_cooler.py).
