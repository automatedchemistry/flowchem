# Knauer Valves
## Introduction
A range of different valve heads can be mounted on the same Knauer actuator, so several type of valves can be controlled
with the same protocol. Both standard 6-port-2-position injection valve and multi-position valves
(with 6, 12 or 16 ports) can be controlled via flowchem.

As for all `flowchem` devices, the virtual instrument can be instantiated via a configuration file that generates an
openAPI endpoint.


## Connection
Knauer valves are originally designed to be used with HPLC instruments, so they support ethernet communication.
Moreover, they feature an autodiscover mechanism that makes it possible to automatically find the device IP address
of a device given its (immutable) MAC address.
This enables the use of the valves with dynamic addresses (i.e. with a DHCP server) which simplify the setup procedure.


## Configuration
Configuration sample showing all possible parameters:

```toml
[device.my-knauer-valve]  # This is the valve identifier
type = "KnauerValve"  # The actual valve type will be detected automatically
ip_address = "192.168.2.1"  # Onyl one of either ip_address or mac_address need to be provided
mac_address = "00:11:22:33:44:55"  #  Onyl one of either ip_address or mac_address need to be provided
network = "192.198.*.*" # Informing the address of the network where the device is located will make it easier to search for it.
```

## API methods
See the [device API reference](../../api/knauer_valve/api.md) for a description of the available methods.

## Valve positions
The valve position naming follow the general convention of flowchem, depending on the valve type:
* Injection valves have position named 'load' and 'inject'
* Distribution valves have positions from '1' to 'n' where n is the total amount of port available.

## Device detection
Knauer Valves can be auto-detected via the `flowchem-autodiscover` command-line utility.
After having installed flowchem, run `flowchem-autodiscover` to create a configuration stub with all the devices that
can be auto-detected on your PC.


## Further information
For further information please refer to the [manufacturer manual](knauer_valve.pdf)
