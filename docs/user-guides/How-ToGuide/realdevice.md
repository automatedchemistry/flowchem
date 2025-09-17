# Configuring and running a real device

Before proceeding with the instructions on how to set up and operate a real device, it's important to have a good
understanding of the configuration file and how to interact with the API server. While the 
"[How to create a configuration file](configuration.md)" and 
"[How to work with API](using_api.md)" 
sections illustrate these concepts using fake devices, the underlying principles remain the same when working with a 
real device.

For this showcase, we have selected the Knauer Valve. The settings, as documented in the 
[reference material](../reference/devices/valves/knauer_valve.md), are outlined in the following configuration file, 
named `config.toml`. 

* The actual valve *type* will be detected automatically.
* Onyl one of either *ip_address* or *mac_address* need to be provided.
* Informing the address of the *network* where the device is located will make it easier to 
search for it.

As specified in the settings for each parameter, only the IP address or MAC address needs to be provided.
The MAC address is provided on the device: `00:80:A3:CE:7E:CB`. Additionally, the network to which the device is 
connected is identified as `192.198.*.*`.

```{note}
Knauer valves with an Ethernet connection have a MAC address registered, usually found next to the serial number 
on the device.
```

Therefore, simply configure the MAC address in the configuration.

```toml
[device.my-knauer-valve]
type = "KnauerValve"
mac_address = "00:80:A3:CE:7E:CB"
network = "192.198.*.*"
```

After running flowchem, the valve's functionalities will be accessible through the server. 

![img_1.png](img_1.png)

To access the valve directly in Python, simply use the get_all_devices function as described in item 
[tools](../tools.md).

