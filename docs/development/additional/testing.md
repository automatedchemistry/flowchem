# Tests

The tests are meant to be run with `pytest`.

All tests that do *not* require access to any hardware devices are automatically run for every pull request against the main branch.

Additional device-specific tests can be run with the corresponding marker (e.g., `pytest -m Spinsolve -s`).

All device tests should run with the `-s` option. This option allows for capturing the standard output during the test run, which is useful for interactive and debugging purposes.

The device tests available with their respective markers are described below:

| Marker     | Description                                            |
|------------|--------------------------------------------------------|
| HApump     | Tests requiring a local HA Elite11 connected.          |
| Spinsolve  | Tests requiring a connection to Spinsolve.             |
| FlowIR     | Tests requiring a connection to a FlowIR.              |
| KPump      | Tests for Azura compact.                               |
| FakeDevice | Tests for FakeDevice, just an example how tests works. |
| CVC3000    | Tests requiring a connection to CVC3000                |
| Manson     | Tests requiring a Manson Power Control                 |


```{warning}
The configuration file needs to be changed to match your hardware.
Each configuration file is placed in the folder of the corresponding device.
```

The configuration file used in the test should have specific attributes.

Let's see our FakeDevice example. In the directory `test/devices/Fake_group/fakedevice.toml`:

```toml
[device.test]
type = "FakeDeviceExample"
another_attribute = "786563"
```

The name of the device must be `test`. This is important to link to the test script, in this case, `test_fakedevice.py`.

```python
...
@pytest.fixture(scope="module")
def api_dev(xprocess):
    config_file = Path(__file__).parent.resolve() / "fakedevice.toml" # -> The name mus
                                                                      #    corresponding with  
                                                                      #    the configuration
                                                                      #    file
    ...


@pytest.mark.FakeDevice
def test_fakedevice(api_dev):
    component = api_dev['test']['FakeComponent']  # -> The name of the device must be `test` 
                                                  #    to macht with the key name here!
    ...
```

To run these example the user can write in local prompt:
```shell
pytest ./tests -m FakeDevice -s
```
or 
```shell
pytest tests/devices/Fake_group/test_fakedevice.py -s
```