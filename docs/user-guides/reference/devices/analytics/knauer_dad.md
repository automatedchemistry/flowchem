# Knauer Diode Array Detector
```{admonition} Additional software needed!
:class: attention

To control the Knauer Diode Array Detector, a set of commands are required.
These cannot be provided with flowchem as they were provided under the terms of an NDA.
You can contact your Knauer representative for further help on this matter.
```

## Configuration
Configuration sample showing all possible parameters:

```toml
[device.my-knauer-dad]  # This is the device identifier
type = "KnauerDAD"
ip_address = "192.168.2.1"  # Onyl one of either ip_address or mac_address need to be provided
mac_address = "00:11:22:33:44:55"  #  Onyl one of either ip_address or mac_address need to be provided
turn_on_d2 = true
turn_on_halogen = true
display_control = false  # If true the display on the device will be disabled (remote control only).
```

## API methods
See the [device API reference](../../api/knauer_valve/api.md) for a description of the available methods.
