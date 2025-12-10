# Bio-Chem Solenoid Valve

Solenoid valve controlled by the flowchem device MPIKG switchbox

## Configuration
Configuration sample showing all possible parameters:

⚙️ BioChemSolenoidValve Initialization Parameters

When creating a BioChemSolenoidValve, you must specify how the valve connects to a device that provides a Relay 
component — either as a single-channel or multi-channel relay controller.

| Parameter          | Type                     | Required                 | Description                                                                                                                                                                                            |
| ------------------ | ------------------------ | ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `support_platform` | `str`                    | ✅                        | Identifier of the relay component that controls this valve. It must match an existing entry in `Relay.INSTANCES`, formatted as `device_name/relay_name`. <br><br>Example: `mpibox/relay-A`             |
| `channel`          | `int`, optional          | ⚙️ Only if multi-channel | The relay channel number (1–32) to use. Required only when the relay component supports multiple channels (e.g., a switch box or multiplexer). <br><br>For single-channel relays, this can be omitted. |
| `normally_open`    | `bool`, default = `True` | ❌                        | Defines the valve’s electrical and flow logic. <br>• **True** → Valve is *open* when unpowered (Normally Open). <br>• **False** → Valve is *closed* when unpowered (Normally Closed).                  |


```toml
[device.my-solenoid]
type = "BioChemSolenoidValve"  # This is the device identifier
support_platform = "mybox/relay-A"  # Name of the `device/component` instance to bind to (key in Relay.INSTANCES`).
channel = 1  # Relay channel index (1–32) on the switch box.
normally_open = 1 # (optional) : 0 - False and 1 - True, default 1. Electrical/flow logic of the valve. 
                  # If True, the valve is open by default (no power). If False, the valve is closed by default (no power).
```

💡 Notes

* The support_platform must reference a device that already exposes a Relay component.

* The relay component can be multi-channel (e.g., controlling multiple valves) or single-channel.

* The communication between the valve and relay is managed automatically after initialization (await valve.initialize()).

More details access an example of device with relay component [mpibox](../custom/mpikg_switch_box.md).

## API methods

See the [device API reference](../../api/biochem_solenoid/solenoid_valve.md) for a description of the available methods.

## Further information:

More detail can be found in [datasheet](biochem_solenoids.pdf).


