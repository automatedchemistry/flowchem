# Add new device as external plugin

The support of external plugins by flowchem enables to create local packages to extend the functionalities of flowchem.
This approach has advantages as you can be directly in control of the code relative to your device, but comes with
additional complexity, so it is only suggested to experienced pythonistas.

Python [entry points](https://setuptools.pypa.io/en/latest/userguide/entry_point.html) are used to discover the
installed plugins from flowchem, so any new plugin must use the entry point `flowchem.devices`.

You can start forking the [flowchem-test](https://github.com/cambiegroup/flowchem-test) to have a template for a
flowchem plugin repo.

If you are using a `pyproject.toml` file the configuration looks something like this:

```toml
[project.entry-points."flowchem.devices"]
test-device = "flowchem_test:fakedevice"
```
