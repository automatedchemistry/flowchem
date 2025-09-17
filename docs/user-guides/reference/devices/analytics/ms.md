# Waters Xevo MS via Autolynx

This module provides a class-based interface for controlling a Waters Xevo MS system
through AutoLynx by generating properly formatted experiment queue files and optionally
triggering conversion of proprietary `.raw` data to open `.mzML` format using msconvert
from ProteoWizard.

References:
[Waters Xevo G2-XS QTof Mass Spectrometer User Guide](https://www.waters.com/webassets/cms/support/docs/71500123505ra.pdf)

## Configuration
Configuration sample showing all possible parameters:

```toml
[device.my-ms]  # This is the 'device' identifier
type = "WatersMS"

# Optional paramters (default shown)
path_to_AutoLynxQ = "PATH/TO/AutoLynx/" # Path to the AutoLynx queue folder.
ms_exp_file = ""  # Name of the MS experiment method file.
tune_file = ""  # Name of the tune method file.
inlet_method  = "inlet_method"  # Name of the inlet method file.
```

