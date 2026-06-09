# NI-DAQmx analog I/O

`NIDAQAnalogIO` exposes generic NI-DAQmx analog input and output channels. It does not apply pressure, temperature, or
other sensor calibration; it reads and writes hardware-level analog values in volts.

## Configuration

Use a NI MAX device name and let Flowchem discover analog channels:

```toml
[device.analog_io]
type = "NIDAQAnalogIO"
module = "Dev2"
```

Or provide explicit physical channels:

```toml
[device.analog_io]
type = "NIDAQAnalogIO"
adc_channels = ["Dev2/ai0", "Dev2/ai1"]
dac_channels = ["Dev2/ao0", "Dev2/ao1"]
```

Analog ranges are optional. When omitted, Flowchem uses the NI-DAQmx defaults. Override them only when your hardware or
measurement needs a specific range:

```toml
adc_range = ["0 V", "10 V"]
dac_range = ["0 V", "10 V"]
terminal_config = "DEFAULT"
```

## API

The `adc` component provides:

* `GET /read?channel=1`
* `GET /read_all`

The `dac` component provides:

* `PUT /set?channel=1&value=2.5 V`
* `GET /read?channel=1`
