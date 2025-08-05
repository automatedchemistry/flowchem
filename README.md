# Welcome to flowchem

![github-actions](https://github.com/cambiegroup/flowchem/actions/workflows/python-app.yml/badge.svg)
[![Documentation Status](https://readthedocs.org/projects/flowchem/badge/?version=latest)](https://flowchem.readthedocs.io/en/latest/?badge=latest)
[![PyPI version fury.io](https://badge.fury.io/py/flowchem.svg)](https://pypi.org/project/flowchem/)
[![MIT license](https://img.shields.io/badge/License-MIT-blue.svg)](https://lbesson.mit-license.org/)
[![DOI](https://zenodo.org/badge/300656785.svg)](https://zenodo.org/badge/latestdoi/300656785)

![Flowchem logo](https://raw.githubusercontent.com/cambiegroup/flowchem/main/docs/_static/flowchem_logo.svg)

Flowchem is an application to simplify the control of instruments and devices commonly found in chemistry labs.
Flowchem acts as unifying layer exposing devices using different command syntax and protocols under a single API.

## Overview
Using flowchem is simple.
You just need to create a configuration file with the connection details for your devices and run `flowchem`.
The flowchem app then:
1. reads the configuration file with the devices to be controlled and their settings;
2. creates connections with each device and ensures a reproducible state at start-up;
3. provides access to the capabilities of each device (such as pumping, heating etc...) via a web interface.

![Flowchem software architecture](https://raw.githubusercontent.com/cambiegroup/flowchem/main/docs/_static/architecture_v1.svg)

Since flowchem leverages web technologies, flowchem devices can be controlled directly with a web browser or by clients
written in different languages and from almost any operative system, including Android and iOS.
A set of python clients interfacing with the flowchem API are also provided and used in examples.

## Supported devices
Currently, the following instruments are supported:
 - Pumps (Knauer P2.1, Harvard Apparatus Elite 11, Hamilton ML600)
 - Valves (ViciValco and Knauer)
 - Thermostat (Huber)
 - Analytical instruments (Magritek Spinsolve benchtop NMR and Mettler Toledo FlowIR)
 - General purpose sensors from Phidgets
 - ... and more!
We are open to contributions!
 - If you want to [add support for a new device](https://flowchem.readthedocs.io/en/latest/add_new_device_type.html),
read how to do that in the documentation.

## Install flowchem
To install `flowchem`, ensure you have Python >= 3.10 installed, then run:
```shell
pip install flowchem
```

## Documentation
You can find more information on installation and use in the documentation online at [ReadTheDocs.io](https://flowchem.readthedocs.io/en/latest/).

## License
This project is released under the terms of the MIT License: a short and simple permissive license with conditions only
requiring preservation of copyright and license notices.
Licensed works, modifications, and larger works may be distributed under different terms and without source code.

<!--
TODO: add ref to paper once out here and in the docs root.
## Citation
If you use flowchem for your paper, please remember to cite it!
-->

## Questions
For questions about this project, fell free to [open an issue on GitHub](https://github.com/cambiegroup/flowchem/issues/new),
or reach out [by email](mailto:2422614+dcambie@users.noreply.github.com).
