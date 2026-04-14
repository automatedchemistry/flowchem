from flowchem.devices.list_known_device_type import autodiscover_device_classes


def test_device_finder():

    dev_found = autodiscover_device_classes()
    # Check all devices implement base API
    for name, device in dev_found.items():
        assert hasattr(device, "initialize")
        assert hasattr(device, "repeated_task")
