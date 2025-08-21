# Switch Box

The Switch Box was custom-built by the Electronics Lab of the Max Planck Institute of Colloids and Interfaces (MPIKG).  
The Switch Box was custom-built by the Electronics Lab of the
Max Planck Institute of Colloids and Interfaces (MPIKG).

It provides:

* 32 digital outputs (0–24V) with two options (Low power 12 V and High power 24 V)

* Analog input channels (0–5 V)

* Analog output channels (DAC) (0–10 V, 12-bit resolution)

## Configuration
Configuration sample showing all possible parameters:

```toml
[device.my-box]                 
type = "SwitchBoxMPIKG"          # This is the device identifier
port = "COM4"                    # Serial port name (e.g., 'COM3') for Serial communication
```

Communication by Serial Port
```{note} Serial connection parameters
Note, further parameters for the serial connections (i.e. those accepted by `serial.Serial`) such as `baudrate`,
`parity`, `stopbits`, `bytesize` and `timeout` can be specified.
However, it should not be necessary as the following values (which are the default for the instrument) are
automatically used:
timeout 1,       # Timeout in seconds
baudrate 57600,  # Fixed baudrate
bytesize 8,      # Data: 8 bits (fixed)
parity None,     # Parity: None (fixed)
stopbits 1       # Stopbits: 1 (fixed)
```

## API methods

See the [device API reference](../../api/mpikg_box/api.md) for a description of the available methods.

## Further information:

More detail can be found as a docstring in the
[main class](../../../../../src/flowchem/devices/custom/mpikg_switch_box.py).


