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
id = "unit_identifier"
communication_parameter = "value"
additional_parameter1 = "value1"
additional_parameter2 = "value2"
```

- **Device Block**: Starts with `[device.user_chosen_name]`. The name (e.g., socl2, hexyldecanoic) can be freely chosen by the user.
- **Type**: Specifies the device class (e.g., "Elite11", "AzuraCompact").
- **Id** (optional): Your own identifier for the physical unit, described below.
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

## Tracking the physical unit

The optional `id` records which physical unit is behind a device name. The model alone can't tell you that when one
unit is swapped for another of the same model. Flowchem stores it in the device metadata, so here `GET /socl2/` returns
`"id": "PUMP-042"`:

```toml
[device.socl2]
type = "Elite11"
id = "PUMP-042"
port = "COM4"
syringe_diameter = "14.567 mm"
syringe_volume = "10 ml"
```

Flowchem doesn't check that ids are unique, and a number is stored as text.

## Settings a device doesn't use

A setting the device doesn't use is ignored, and real drivers log a warning naming it when the server starts. This lets
one file work with both `flowchem` and `flowchem-sim`. Here `num_ports` configures the simulated valve, and the real
driver ignores it:

```toml
[device.valve1]
type = "RunzeValve"
port = "COM5"
num_ports = 6
```

Ignored settings can still be read at `GET /startup_config`, which returns the whole configuration file.

```{warning}
A misspelled optional setting doesn't stop the server either: the device starts with the default value instead. For
example, `normally_opn = false` leaves a solenoid valve configured as normally open. Check the startup log for warnings
about unrecognized settings. A missing mandatory setting still stops the server.
```

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
