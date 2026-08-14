# Vapourtec eBPR
```{admonition} Additional software needed!
:class: attention

To control the Vapourtec eBPR, a set of serial commands are required.
These cannot be provided with flowchem as they were provided under the terms of an NDA.
You can contact your Vapourtec representative for further help on this matter.
```

The Vapourtec eBPR is an electronic back pressure regulator, controlled via a serial (RS-232) interface.
It exposes a single pressure-control component that allows setting the target back pressure, reading the
current pressure, and switching the pressure control on or off.

```{note} Serial connection parameters
Note, further parameters for the serial connections (i.e. those accepted by `serial.Serial`) such as `baudrate`,
`parity`, `stopbits` and `bytesize` can be specified.
However, it should not be necessary as the following values (which are the default for the instrument) are
automatically used:
* timeout 1.0s
* baudrate 9600
* parity none
* stopbits 1
* bytesize 8
```

## API methods
See the [device API reference](../../api/ebpr/api.md) for a description of the available methods.
