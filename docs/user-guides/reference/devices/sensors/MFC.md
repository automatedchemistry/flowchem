# Bronkhorst El-flow mass flow controller

## Introduction

Bronkhorst El-flow mass flow controller (MFC) device driver.

More information about the device can be found in the supplier platform [Bronkhorst](https://www.bronkhorst.com/en-gb/).

## mass flow controller



## Configuration
Configuration sample showing all possible parameters:

```toml
[device.my-MFC]  # This is the MFC identifier
type = "MFC"     # Class of the device
port = "COM4"    # Access port (serial)
channel = 1      
address = 0x80
max_flow = 9
```

The class was built base on the package of the 
[manufacturer](https://bronkhorst-propar.readthedocs.io/en/latest/introduction.html).

## API methods
See the [pressure sensor API reference](../../api/bronkhorst_MFC/api.md) for a description of the available methods.
