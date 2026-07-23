# Runze Smart SY-01 Syringe Pump

## Introduction

The Runze Smart SY-01 is a syringe pump with a built-in multi-position distribution valve
(6, 8, 10, 12 or 16 ports, detected automatically, same as the standalone
[Runze valve](../valves/runze_valve.md)). Pump and valve share one serial address and one
`flowchem` device, exposing two components: `pump` (infuse/withdraw) and `valve`
(distribution valve).

Runze valves and pumps are commonly multi-dropped together on a single RS-485 line; devices
sharing the same `port` in the configuration file automatically share one serial connection.

## Configuration
Configuration sample showing all possible parameters:

```toml
[device.my-runze-pump]     # Identifier for this pump
type = "RunzeSyringePump"
port = "COM5"               # Serial port where the pump is connected
address = 1                 # ID in a multi-dropped/daisy-chained setup
syringe_volume = "5 mL"     # Syringe volume, required
total_steps = 12000         # Steps for a full stroke (see the syringe's model code); default 12000
```

```{note} Speed control
The vendor's dynamic-speed command (`0x4b`) has an unconfirmed parameter range and is not
yet wired into `infuse`/`withdraw`; the pump currently runs moves at its default speed and
logs a warning if a `rate` is supplied.
```

## Pump positions
Position is tracked in steps from home (the plunger's reset optocoupler, at 0 mL) up to
`total_steps` (at `syringe_volume`). `infuse` moves the plunger toward home; `withdraw`
moves it away from home, mirroring the vendor's "Injection"/"Suction" terminology.

## Valve positions
The built-in valve position naming follows the general convention of flowchem: distribution
valves have positions from '1' to 'n', where n is the total number of available ports.

## Further information
This driver implements the binary command protocol from Runze's "Smart SY-01 Syringe"
control-code manual (not bundled in this repository), which shares its frame format and
checksum with the [SV-06 valve manual](../valves/runze_valve.pdf) already included here.
