# Knauer Autosampler

Control the Knauer Autosampler AS 6.1L via either Serial or Ethernet communication.
It enables users to interact with the device by sending and receiving commands, configuring parameters like tray temperature, 
syringe volume, and controlling the movement of the needle and valves.

[!IMPORTANT] 
This software package was created internally, utilizing a proprietary communication framework made available by the 
manufacturer.

## Configuration
Configuration sample showing all possible parameters:

```toml
[device.my-knauer-autosample]    # This is the device identifier
type = "KnauerAutosampler"
ip_address = "192.168.2.1"       # IP address for Ethernet communication (mutually exclusive with `port`).
autosampler_id = 1               # Device ID used for command addressing.
port = "COM4"                    # Serial port name (e.g., 'COM3') for Serial communication (mutually exclusive with `ip_address`).
_syringe_volume = "0.5 mL"       # Optional - Syringe volume (e.g., '250 uL', '0.5 mL') to be validated and set.
tray_type = "TRAY_48_VIAL"       # Optional - Type of sample tray used (must be one of the PlateTypes enum - e.g TRAY_48_VIAL).

```

In case of communication by Serial Port
```{note} Serial connection parameters
Note, further parameters for the serial connections (i.e. those accepted by `serial.Serial`) such as `baudrate`,
`parity`, `stopbits`, `bytesize` and `timeout` can be specified.
However, it should not be necessary as the following values (which are the default for the instrument) are
automatically used:
timeout 1,  # Timeout in seconds
baudrate 9600,  # Fixed baudrate
bytesize 8,  # Data: 8 bits (fixed)
parity None,  # Parity: None (fixed)
stopbits 1  # Stopbits: 1 (fixed)
```

In case of communication by Ethernet
```{note} Serial connection parameters
Parameters for the ethernet connections such as `tcp_port` and `buffersize` can be specified.
However, it should not be necessary as the following values (which are the default for the instrument) are
automatically used:
tcp_port 2101,
buffersize 1024
```

## Further information
For further information please refer to the [manufacturer manual](Autosampler.pdf)

## API methods
See the [device API reference](../../api/knauer_autosampler/api.md) for a description of the available methods.