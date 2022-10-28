# Harvard Apparatus Syringe Pump Elite11

## Introduction
Harvard-Apparatus Elite11 pumps connected via USB cables (which creates a virtual serial port) are supported in flowchem
via the two device types: `Elite11InfuseOnly` and `Elite11InfuseWithdraw`.
This difference reflect the existence in commerce of both variants, i.e. pumps only capable of infusion and pumps that
support both infusion and withdrawing commands.

As for all `flowchem` devices, the virtual instrument can be instantiated via a configuration file that generates an
openAPI endpoint.


## Configuration
Configuration sample showing all possible parameters:

```toml
[device.my-elite11-pump]  # This is the pump identifier
type = "Elite11InfuseOnly"  # Either Elite11InfuseOnly or Elite11InfuseWithdraw depending on model
port = "COM11"  # This will be /dev/tty* under linux/MacOS
address = 0  # Only needed for daisy-chaining. The address can be set on the pump, see manufacturer manual.
syringe_diameter = "4.6 mm"
syringe_volume = "1 ml"
baudrate = 115200  # Values between 9,600 and 115,200 can be selected on the pump! (115200 assumed if not specified)
```

```{note} Serial connection parameters
Note, further parameters for the serial connections (i.e. those accepted by `serial.Serial`) such as `baudrate`,
`parity`, `stopbits` and `bytesize` can be specified.
However, it should not be necessary as the following values (which are the default for the instrument) are
automatically used:
* baudrate 115200
```


## Device detection
Lab PCs often have several devices connected via serial ports.
Elite11 pumps can be auto-detected via the `flowchem-autodiscover` command-line utility.
After having installed flowchem, run `flowchem-autodiscover` to create a configuration stub with all the devices that
can be auto-detected on your PC.

## Further information
For further information about connection of the pump to the controlling PC, daisy-chaining via firmware cables etc.
please refer to the [manufacturer manual](./elite11_manual.pdf).
