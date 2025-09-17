# tldr (to long don`t read);
```shell
pip install flowchem
```
create config file like `yourfile.toml`:
```shell
[device.test-device]
type = "FakeDevice"
```
run it:
```shell
flowchem yourfile.toml
```
or run the example:
```shell
flowchem example
```