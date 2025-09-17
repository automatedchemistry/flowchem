# Vici Valco Valves
## Introduction
While different valve heads can be mounted on the same Vici Universal actuator, so far only injection valves are
supported, as they are the most common type.
Support for additional valve types can be trivially added, based on the example of Knauer Valves.

As for all `flowchem` devices, the virtual instrument can be instantiated via a configuration file that generates an
openAPI endpoint.


## Connection
Depending on the device options, Vici valves can be controlled in different ways.
The code here reported assumes serial communication, but can be easily ported to different connection type if necessary.

## Configuration
Configuration sample showing all possible parameters:

```toml
[device.my-vici-valve]  # This is the valve identifier
type = "ViciValve"
port = "COM11"  # This will be /dev/tty* under linux/MacOS
address = 0  # Only needed for daisy-chaining. The address can be set on the pump, see manufacturer manual.
```

```{note} Serial connection parameters
Note, further parameters for the serial connections (i.e. those accepted by `serial.Serial`) such as `baudrate`,
`parity`, `stopbits` and `bytesize` can be specified.
However, it should not be necessary as the default for the instrument are automatically used.
```

## API methods
See the [device API reference](../../api/vici_valve/api.md) for a description of the available methods.

## Valve positions
The valve position naming follow the general convention of flowchem:
* Injection valves have position named 'load' and 'inject'
* Distribution valves have positions from '1' to 'n' where n is the total amount of port available.

## Device detection
Knauer Valves can be auto-detected via the `flowchem-autodiscover` command-line utility.
After having installed flowchem, run `flowchem-autodiscover` to create a configuration stub with all the devices that
can be auto-detected on your PC.

```{note} Valve types
Note that the actual type of valve cannot be detected automatically, so you will need to replace the generic
`KnauerValve` type in the configuration with one of the valid device types (i.e. one of `Knauer6Port2PositionValve`,
`Knauer6Port6PositionValve`, `Knauer12PortValve` and `Knauer16PortValve`)
```

## Further information
For further information please refer to the [manufacturer manual](vici_valve.pdf)
