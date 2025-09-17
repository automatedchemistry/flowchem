# Mattler Toledo iCIR
```{admonition} Additional software needed!
:class: attention

To use iCIR-supported devices via flowchem, you must run iCIR installed with the additional module "iC OPC UA Server"!
```
## Introduction
Both the ReactIR and the FlowIR from Mettler-Toledo can be controlled by the proprietary software iCIR.
iCIR has an optional module, available from the manufacturer website, that starts an [OPC UA](https://en.wikipedia.org/wiki/OPC_Unified_Architecture)
server that can be used to control the spectrometer.

As for all `flowchem` devices, a iCIR object can be instantiated via a configuration file that generates an openAPI endpoint.

## Configuration
A valid iCIR template name must be specified!
The template can be created in iCIR and includes all the acquisition/processing options so
that the flowchem configuration is simpler.
An experiment based on the template will be automatically started on flowchem initialization.
This is to ensure the validity of the configuration provided.
```{note}
For a template to be available via remote control it must be saved in the
`C:\ProgramData\METTLER TOLEDO\iC OPC UA Server\1.2\Templates` folder.
```

```toml
[device.my-icir-spectometer]
type = "IcIR"
url = "opc.tcp://localhost:62552/iCOpcUaServer"  # Default, optional
template = "30sec_2days.iCIRTemplate"  # See note above
```


## API methods
See the [device API reference](../../api/icir/api.md) for a description of the available methods.

## Further information
The iC OPC UA Server needed to use iCIR spectrometer in flowchem is a complimentary application provided
by Mettler-Toledo and available on its autochem website.
