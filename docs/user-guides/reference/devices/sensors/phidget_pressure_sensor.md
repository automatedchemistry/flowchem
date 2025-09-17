# Phidgets
```{admonition} Additional software needed!
:class: attention

To control the Phidget devices you need to install their software first.
Visit the [phidget website](https://www.phidgets.com/docs/Main_Page) for more details.
```

## Introduction
[Phidgets](https://www.phidgets.com/docs/What_is_a_Phidget%3F) are building-blocks for sensing and control and enable
software application to interact with the physical world.
Phidgets arose out of a research project directed by Saul Greenberg at the Department of Computer Science,
University of Calgary and are described in [this paper](https://doi.org/10.1145/502348.502388).

## Pressure Sensor
The only application of phidgets currently implemented in flowchem is the use of a
[Versatile Input Phidget](https://www.phidgets.com/?tier=3&catid=49&pcid=42&prodid=961) whose 4..20mA interface is
connected to a Swagelock Pressure Transducer.
This example PressureModule object can serve as blueprint for further applications of phidgets in lab settings.

## API methods
See the [pressure sensor API reference](../../api/phidget_p_sensor/api.md) for a description of the available methods.
