# Vapourtec R4 heating module
```{admonition} Additional software needed!
:class: attention

To control the Vapourtec R2 reactor, a set of serial commands are required.
These cannot be provided with flowchem as they were provided under the terms of an NDA.
You can contact your Vapourtec representative for further help on this matter.
```

The Vapourtec R4 module can be used both as a standalone reactor temperature control unit or as a part of an R2 assembly.
Here the former case is assumed, for a description of the R2 reactor visit the [R2 reactor](../misc/r2_reactor.md) page.

```{note} Serial connection parameters
Note, further parameters for the serial connections (i.e. those accepted by `serial.Serial`) such as `baudrate`,
`parity`, `stopbits` and `bytesize` can be specified.
However, it should not be necessary as the following values (which are the default for the instrument) are
automatically used:
* timeout 0.1s
* baudrate 19200
* parity none
* stopbits 1
* bytesize 8
```

## API methods
See the [device API reference](../../api/r4_heater/api.md) for a description of the available methods.
