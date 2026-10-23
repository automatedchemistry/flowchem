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

## Waiting for the pump to finish
When you send an `infuse` or `withdraw` command to this pump, you don't get a response back
until the plunger has *actually finished moving*. Units differ in how they report this: some
stay silent until the movement is complete, others immediately answer "task being executed"
and keep moving. The driver handles both — in the second case it keeps asking the pump for its
status until it reports idle. So if your script sends the command and then immediately moves
on to the next step, you can be confident the pump is already done — there is no need to add
an extra wait or check "is it still moving?" yourself.

The driver allows each move a share of 60 s per full stroke (at least 10 s). A pump of the
second kind that is slower than that is not failed while its plunger is still moving: the
driver reads the plunger position every 5 s and keeps waiting as long as it changes, for up to
10 minutes, logging a warning that the move took longer than estimated. A pump that keeps
reporting busy while its plunger has stopped fails one check later, and the error log gives
the position where it stopped.

Temporary missing or damaged status replies produce warnings while the driver keeps
checking for completion. The same recovery applies to the built-in valve. These operations
retry status queries until their completion timeout, including time spent waiting on serial
communication. Direct status queries, such as `is-idle`, make up to three attempts. If
completion cannot be confirmed before the timeout, the operation fails rather than reporting
success. Recovery never resends a movement command, which could otherwise repeat a transfer.

On a shared RS-485 connection, the driver validates each reply's frame markers, length,
checksum, and device address. It discards damaged frames and replies from other addresses
with a warning and continues waiting within the original serial timeout. An exchange already
in progress can finish after the completion deadline, so the total wait can exceed the
deadline by one serial exchange or shared-bus wait. Flowchem must be the only sender on the
bus. The protocol does not include a command echo or transaction identifier in replies, so
a delayed reply from the same address cannot be conclusively identified as stale.

## Valve positions
The built-in valve position naming follows the general convention of flowchem: distribution
valves have positions from '1' to 'n', where n is the total number of available ports.

## Further information
This driver implements the binary command protocol from Runze's "Smart SY-01 Syringe"
control-code manual (not bundled in this repository), which shares its frame format and
checksum with the [SV-06 valve manual](../valves/runze_valve.pdf) already included here.
