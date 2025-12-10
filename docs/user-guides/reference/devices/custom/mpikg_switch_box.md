# Switch Box

The Switch Box was custom-built by the Electronics Lab of the Max Planck Institute of Colloids and Interfaces (MPIKG).

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

🔌 Control Devices Connected to a Relay Box

Some Flowchem devices (such as a Switch Box) expose multiple relay, ADC, or DAC components that can be used to 
control or read from other instruments.

While you can interact directly with the box and its components through the Flowchem API, it’s often more 
convenient to define which device and component another instrument (like a valve) should use.

This is done by referencing the box instance and its component name using the format:

```
device_name/component_name
```

For example, a SwitchBoxMPIKG device may expose several relay components and analog channels:

* my-box/relay-A

* my-box/relay-B

* my-box/relay-C

* my-box/relay-D

* my-box/adc

* my-box/dac

These component identifiers can then be reused by other Flowchem devices (such as valves or pumps) that depend on 
relay control or analog feedback.

🧩 Example: Attaching a Device to a Relay Box

Below is an example configuration showing how to connect a BioChemSolenoidValve to a specific relay on the box.

```toml
# Define the control box that provides the relay components
[device.mybox]
type = "SwitchBoxMPIKG"
port = "COM8"

# Define a valve controlled through one relay channel of the box
[device.valve]
type = "BioChemSolenoidValve"
support_platform = "mybox/relay-A"  # Reference to the relay component
channel = 1                         # Channel number (if multi-channel relay)
normally_open = 1                   # Valve logic (1 = normally open)
```

In this example:

* The device mybox represents the control box hardware.

* The relay-A component belongs to that box and provides a digital ON/OFF output.

* The valve device uses that output to control its open/close state.

💡 Notes

* The support_platform must always point to a valid device/component pair already defined in your configuration.

* If the relay component supports multiple channels, the channel parameter specifies which one to use (e.g., channel = 1).

* For single-channel relays, channel can be omitted.

* If the user does not wish to expose the attached device explicitly (e.g., a manually wired solenoid), the corresponding 
device entry can be omitted from the configuration file.

## API methods

See the [device API reference](../../api/mpikg_box/api.md) for a description of the available methods.

## Further information:

More detail can be found as a docstring in the
[main class](../../../../../src/flowchem/devices/custom/mpikg_switch_box.py).


