# Bio-Chem Solenoid Valve

Solenoid valve controlled by the flowchem device MPIKG switchbox

## Configuration
Configuration sample showing all possible parameters:

```toml
[device.my-solenoid]
type = "BioChemSolenoidValve"  # This is the device identifier
support_platform = "mybox"  # Name of the `SwitchBoxMPIKG` instance to bind to (key in SwitchBoxMPIKG.INSTANCES`).
channel = 1  # Relay channel index (1–32) on the switch box.
normally_open = 1 # (optional) : 0 - False and 1 - True, default 1. Electrical/flow logic of the valve. 
                  # If True, the valve is open by default (no power). If False, the valve is closed by default (no power).
```

## API methods

See the [device API reference](../../api/biochem_solenoid/solenoid_valve.md) for a description of the available methods.

## Further information:

More detail can be found in [datasheet](biochem_solenoids.pdf).


