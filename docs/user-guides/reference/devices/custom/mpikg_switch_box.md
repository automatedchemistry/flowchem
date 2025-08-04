# Switch Box

The Switch Box was custom-built by the Electronics Lab of the Max Planck Institute of Colloids and Interfaces (MPIKG).  
It provides **32 digital outputs** capable of delivering signals from **0 to 24 V**.

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

## Further details for reference:

### Serial Commands to the box device

Port Befehle

* These control the current state of the box’s 32 digital output lines, grouped into four “ports” (A, B, C, D).
* Each port is 16 bits wide (0–65535 decimal), and you can set or read them individually (a, b, c, d) or all at once (abcd).

| **Command** | **channel** | **Value**            | **return**           |
|-------------|-------------|----------------------|----------------------|
| set         | a           | 0-65535 Byte Decimal |                      |
| set         | b           | 0-65535 Byte Decimal |                      |
| set         | c           | 0-65535 Byte Decimal |                      |
| set         | d           | 0-65535 Byte Decimal |                      |
| set         | abcd        | 0-65535 Byte Decimal |                      |
| get         | a           |                      | 0-65535 Byte Decimal |
| get         | b           |                      | 0-65535 Byte Decimal |
| get         | c           |                      | 0-65535 Byte Decimal |
| get         | d           |                      | 0-65535 Byte Decimal |
| get         | abcd        |                      | 0-65535 Byte Decimal |

Example::
```shell
set a:65535  # Turns all 8 outputs in Port A ON
get b        # Reads the current 16-bit value of Port B
```

PortA Startwert
* These define the power-on default for each port (what state it should start in when the device is powered up or reset).\
* They are stored in the device’s memory.
* Same structure as the Port Commands table, but prefixed with start.

| **Command** | **channel** | **Value**            | **return**           |
|-------------|-------------|----------------------|----------------------|
| set         | starta      | 0-65535 Byte Decimal |                      |
| set         | startb      | 0-65535 Byte Decimal |                      |
| set         | startc      | 0-65535 Byte Decimal |                      |
| set         | startd      | 0-65535 Byte Decimal |                      |
| get         | starta      |                      | 0-65535 Byte Decimal |
| get         | startb      |                      | 0-65535 Byte Decimal |
| get         | startc      |                      | 0-65535 Byte Decimal |
| get         | startd      |                      | 0-65535 Byte Decimal |

Example::
```shell
set starta:65535
get startc
```

ADC (Analog-Digital) Commands

* Commands here are for analog outputs — setting a voltage from 0 to 10 V using a 12-bit value (0–4095).
* You can control each channel individually (x = 1–32).

| **Command** | **channel**   | **Value**      | **return** |
|-------------|---------------|----------------|------------|
| set         | dacx (x=1-32) | 0-4095 (0-10V) |            |
| get         | dacx (x=1-32) |                | 0-4095     |

DAC (Digital-Analog) Commands
* Commands read analog input voltages (0–5 V)
* Useful for monitoring sensor inputs connected to the box.

| **Command** | **channel** | **return** |
|-------------|-------------|------------|
| get         | dacx        | 0-5 Volt   |
| get         | dac0        | 0-5 Volt   |
| get         | dac1        | 0-5 Volt   |
| get         | dac2        | 0-5 Volt   |
| get         | dac3        | 0-5 Volt   |
| get         | dac4        | 0-5 Volt   |
| get         | dac5        | 0-5 Volt   |
| get         | dac6        | 0-5 Volt   |
| get         | dac7        | 0-5 Volt   |

Example::
```shell
set dac1:4095
get dac8
```

Special commands

Get version and help

| **Command** | **return** |
|-------------|------------|
| get         | ver        |
| help        |            |

