# Runze Valves

## Introduction

A range of different valve heads can be mounted on the same Runze actuator, allowing multiple valve types to be 
controlled with the same protocol. Multi-position valves (with 6, 8, 10, 12, or 16 ports) are supported via `flowchem`.

As with all `flowchem` devices, the virtual instrument can be instantiated via a configuration file that generates 
an OpenAPI endpoint.

## Configuration
Configuration sample showing all possible parameters:

```toml
[device.my-runze-valve]   # Identifier for this valve
type = "RunzeValve"       # Valve type; actual model is detected automatically
port = "COM5"             # Serial port where the valve is connected
address = 1               # ID in a daisy-chained setup
```

## Valve positions
The valve position naming follow the general convention of flowchem:
* Distribution valves have positions from '1' to 'n' where n is the total amount of port available.

## Further information
For further information please refer to the [manufacturer manual](runze_valve.pdf)