# DataApex Clarity (HPLC control software)
```{admonition} Additional software needed!
:class: attention

Data Apex Clarity is a third-party HPLC control software that can be controlled via a CLI tool.
```

Clarity is a chromatography data software for data acquisition, processing, and instrument control that can be
controlled via a command line interface (CLI) as described on the [manufacturer website](https://www.dataapex.com/documentation/Content/Help/110-technical-specifications/110.020-command-line-parameters/110.020-command-line-parameters.htm?Highlight=command%20line).

In `flowchem` we provide a device type, named `Clarity`, to control local Clarity instances via HTTP with flowchem API.


## Configuration
Configuration sample showing all possible parameters:

```toml
[device.hplc]  # This is the 'device' identifier
type = "Clarity"

# Optional paramters (default shown)
executable = "C:\\claritychrom\\bin\\claritychrom.exe"
instrument_number = 1  # Specify the instrument to be controlled (if the same Clarity instance has more than one)
startup-time = 20  # Max time necessary to start-up Clarity and connect all the instrument specified in the configuration
startup-method = "startup-method.met"  # Method sent to the device upon startup.
cmd_timeout =  3  # Max amount of time (in s) to wait for the execution of claritychrom.exe commands.
user = "admin"  # Default user name
password = ""  # Empty or option not present for no password
clarity-cfg-file = ""  # Configuration file for Clarity, if e.g. LaunchManager is used to save different configutations
```

## API methods
See the [device API reference](../../api/clarity/api.md) for a description of the available methods.

## Further information
Only few of the commands available through Clarity CLI are exposed via flowchem.
It is possible to add support for more commands if necessary, please refer to the
[manufacturer website](https://www.dataapex.com/documentation/Content/Help/110-technical-specifications/110.020-command-line-parameters/110.020-command-line-parameters.htm?Highlight=command%20line)
for a list of all the available options.
