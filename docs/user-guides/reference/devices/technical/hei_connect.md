# Heidolph MR Hei-Connect

The Heidolph MR Hei-Connect magnetic stirrer can be controlled via RS232 using the `HeiConnect` device type.
The implementation uses the extended interface protocol described in the official operating manual.

## Configuration

Real hardware:

```toml
[device.hei-connect]
type = "HeiConnect"
port = "COM1"
connection_check = true
```

Simulation:

```toml
[device.hei-connect-sim]
type = "SimulatedHeiConnect"
```

```{note} Serial connection parameters
The following serial parameters are used by default:
* timeout 1 s
* baudrate 9600
* parity even
* stopbits 1
* bytesize 7

Further parameters accepted by `serial.Serial` can be specified in the device configuration.
```

## API methods

The device exposes three components:

* `stirring-control` to set/query speed and start/stop rotation.
* `temperature-control` to set/query temperature, start/stop heating, and select fast or precise heating mode.
* `control` to query status and software version.

`temperature-control-mode` is read-only and reports whether the device is controlling temperature from the hotplate
or from the external Pt1000 sensor.

The operating manual is available from [Heidolph][heidolph-manual].

[heidolph-manual]: https://heidolph.com/Documents/Operation%20manuals/magnetic%20stirrer/Operation-Manual-Magnetic%20Stirrer-Hei-Standard-Tec-Connect.pdf
