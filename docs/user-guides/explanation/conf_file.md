# flowchem Configuration File: Simple, Flexible, and User-Friendly

Flowchem uses a TOML (Tom's Obvious, Minimal Language) configuration file to manage device settings. This format was 
chosen for its simplicity and readability, making it easy for users to edit without requiring extensive technical 
knowledge.

## Key Features of the Configuration File

1. **Human-Readable Format**: TOML is designed to be easy to read and write, using simple key-value pairs and sections.

2. **Flexible Device Naming**: Users can name devices according to their preference, enhancing clarity and organization.

3. **Easy Updates**: Changing device settings or switching devices can be done quickly by editing the relevant sections.

4. **Clear Structure**: Each device is represented by its own block, making the file easy to navigate and understand.

## Understanding the File Structure

```toml
[device.user_chosen_name]
type = "DeviceClass"
communication_parameter = "value"
additional_parameter1 = "value1"
additional_parameter2 = "value2"
```

- **Device Block**: Starts with `[device.user_chosen_name]`. The name (e.g., socl2, hexyldecanoic) can be freely chosen by the user.
- **Type**: Specifies the device class (e.g., "Elite11", "AzuraCompact").
- **Communication Parameter**: How to connect to the device (e.g., port, IP address, URL).
- **Additional Parameters**: Any extra settings specific to the device type.

## Example Breakdown

Let's look at one device from the example:

```toml
[device.socl2]
type = "Elite11"                 # Class name of the device
port = "COM4"                    # Communication access
syringe_diameter = "14.567 mm"   # Additional configuration
syringe_volume = "10 ml"         # Additional configuration
baudrate = 115200                # Additional configuration
```

- The device is named "socl2" (user's choice).
- It's an "Elite11" type device.
- It's connected via COM4 port.
- It has specific syringe and communication settings.

## Creating the File

1. **Editing Device Names**: Simply edit the `[device.name]` line.
2. **Updating Settings**: Modify the values after the `=` sign.
3. **Adding/Removing Devices**: Add or delete entire `[device.name]` blocks as needed.

```{important}
When editing, ensure that:
- The `type` parameter matches an implemented device class in flowchem.
- The communication parameter (port, IP, URL) is correct for your setup.
- Any additional parameters are appropriate for the device type.
- For details of supported devices and their specific configuration options, refer to the 
[device configuration guides](../reference/devices/supported_devices.md).
```

## File Usage

1. Make your changes in the TOML file.
2. Save the file with a `.toml` extension.
3. Flowchem will use this configuration to connect to and manage the devices.

This user-friendly approach allows for quick adjustments to your flowchem setup, enabling efficient management of 
various devices without the need for complex programming or system changes.

## Practical Impact

This level of abstraction ensures that users can manage and configure devices with minimal effort, focusing on 
high-level functionality rather than low-level implementation details.


