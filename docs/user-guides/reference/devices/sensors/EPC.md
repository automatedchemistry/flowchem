# Bronkhorst El-Pressure controller

## Introduction

Bronkhorst El-Pressure controller controller (EPC) device driver.

More information about the device can be found in the supplier platform [Bronkhorst](https://www.bronkhorst.com/en-gb/).

## Electronic pressure controller



## Configuration
Configuration sample showing all possible parameters:

```toml
[device.my-EPC]  # This is the MFC identifier
port = "COM4"    # Access port (serial)
channel = 1      # The communication channel of the EPC device.
address = 0x80   # The address of the EPC device.  
max_pressure = 9 # The maximum pressure of the EPC device in bar.
```

The class was built base on the package of the 
[manufacturer](https://bronkhorst-propar.readthedocs.io/en/latest/introduction.html).

## API methods
See the [pressure sensor API reference](../../api/bronkhorst_EPC/api.md) for a description of the available methods.
