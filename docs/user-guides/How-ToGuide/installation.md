# Installation guidance

## Install flowchem

Flowchem requires a Python version of 3.10 or later.
You can get the latest version of Python from [python.org](https://www.python.org/downloads/).

To get started with flowchem run in the terminal (preferably in a dedicated 
[virtual environment](https://peps.python.org/pep-0405/)):
```shell
pip install flowchem
```
or install it with [pipx](https://pypa.github.io/pipx/), a tool to install and run python applications in isolated
environments:
```shell
pip install pipx
pipx ensurepath
pipx install flowchem
```
Another way to install the package can be done through the Anaconda. 

```shell
conda install flowchem
```
<!--
The use of `pipx` is recommended because it:
* installs flowchem in a virtualenv, without interfering with other packages installed globally;
* ensure that the `flowchem` and `flowchem-autodiscover` commands are available system-wide, by adding the pipx binary
  folder to the system PATH (the `pipx ensurepath` step).-->

The user can install the development version, available in the [github](https://github.com/cambiegroup/flowchem.git).
It can be install from the GitHub repository running:
```shell
pip install git+https://github.com/cambiegroup/flowchem.git
```

```{note}
The development version is not guaranteed to be safe or stable. 
```

To verify the installation has been completed successfully you can run `flowchem --version`.