# Manson Laboratory Power Supply

## Introduction
The following models of Manson lab power supply are supported: "HCS-3102", "HCS-3014", "HCS-3204" and "HCS-3202".
Once connected via USB, they are recognized as a virtual serial port and are supported in `flowchem` via the device type `MansonPowerSupply`.

As for all `flowchem` devices, the virtual instrument can be instantiated via a configuration file that generates an openAPI endpoint.


## Configuration
Configuration sample showing all possible parameters:

```toml
[device.my-power-supply]  # This is the device name
type = "MansonPowerSupply"
port = "COM12"  # This will be /dev/tty* under linux/MacOS
```

```{note} Serial connection parameters
Note, further parameters for the serial connections (i.e. those accepted by `serial.Serial`) such as `baudrate`, 
`parity`, `stopbits` and `bytesize` can be specified.
```

## API methods
See the [device API reference](../../api/manson_power_supply/api.md) for a description of the available methods.
