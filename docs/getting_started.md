# Getting started
This guide will help you with the installation of flowchem.

## Overview
In a typical scenario, flowchem:
1. reads a configuration file listing the devices to be controlled and their settings;
2. creates connections with each device and ensures a reproducible state at start-up;
3. provides access to the capabilities of each device (such as pumping, heating etc...) via a web interface.

:::{figure-md} flowchem-architecture
<img src="./_static/architecture_v1.svg" alt="Flowchem software architecture (devices/config/server)" class="bg-primary mb-1" width="100%">

**Figure 1** Schematic representation of flowchem software architecture.
An heterogeneous collection of devices is physically connected to a control PC.
The configuration file in TOML format specifies the connection parameters for each device.
After running flowchem with that configuration, a web server is started to control each device via a single API.
:::
![Flowchem software architecture](./_static/architecture_v1.svg | width=100%)

Since flowchem leverages web technologies, flowchem devices can be controlled directly with a web browser or by clients
written in different languages and from almost any operative system, including Android and iOS.
A set of python clients interfacing with the flowchem API are also provided and used in examples.

## Install flowchem
To use it, you need to have Python installed. Flowchem requires a Python version of 3.10 or later.

To get started with flowchem run:
```shell
pip install flowchem
```
or install it with `pipx`:
```shell
pip install pipx
pipx ensurepath
pipx install flowchem
```

The use of `pipx` is the recommended way because it will:
* install flowchem in a virtualenv, without interfering with other packages installed globally
* ensure that the `flowchem` and `flowchem-autodiscover` commands are available system-wide, by adding the pipx binary
  folder to the system PATH.

If you don’t have Python yet, you can download it from [python.org](https://www.python.org/downloads/).

To verify the installation has been completed successfully you can run `flowchem --version`.

## Generate configuration file
To autogenerate a flowchem configuration file, run the autodiscover tool:
```shell
flowchem-autodiscover
```
This will auto-detect a variety of devices connected to your computer and generate a `flowchem_config.toml` file with a
configuration stub for all the devices detected.
Complete the missing information (if any) in this file, and then you will be ready to use flowchem!

```{note}
`flowchem_config.toml` is written in [TOML format](https://en.wikipedia.org/wiki/TOML),
the syntax of this language is intuitive and designed to be human-editable.
If you follow this guide you will not need to learn anything about the TOML syntax, but you can just copy and modify the
examples provided.
```

:::{note}
Not all the devices supported by flowchem can be auto discovered, so you might need to edit the configuration
file manually for some device types.
:::

## Run flowchem
With flowchem installed and a configuration file created, you are ready to start your flowchem server.

Run `flowchem` followed by the location of the configuration file:
```shell
flowchem flowchem_config.toml
```

In your terminal, you will see some debug information, ending with a line like this one:
```shell
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

This means that the flowchem server has been started correctly.
You can visit [http://127.0.0.1:8000](http://127.0.0.1:8000) to see a list of commands available for the device you
configured.

For every request sent to the flowchem server, you will see some diagnostic output in the terminal.
While you can normally ignore this output, it can provide useful information in case of errors.
