# Vapourtec R2 reactor
```{admonition} Additional software needed!
:class: attention

To control the Vapourtec R2 reactor, a set of serial commands are required.
These cannot be provided with flowchem as they were provided under the terms of an NDA.
You can contact your Vapourtec representative for further help on this matter.
```
The Vapourtec R2 reactor is a complex device that integrates several independent components.

```{note}
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
