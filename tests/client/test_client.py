from flowchem.client.async_client import (
    async_get_all_flowchem_devices,
)
from flowchem.client.client import get_all_flowchem_devices
from flowchem.client.component_client import FlowchemComponentClient
from flowchem.client.device_client import FlowchemDeviceClient


def test_get_all_flowchem_devices(flowchem_test_instance):
    dev_dict = get_all_flowchem_devices()
    assert "test-device" in dev_dict

    test_device = dev_dict["test-device"]
    assert isinstance(test_device, FlowchemDeviceClient)
    assert len(test_device.components) == 2

    test_component = test_device["FakeSpecificComponent"]
    assert test_component is dev_dict["test-device"]["FakeSpecificComponent"]
    assert isinstance(test_component, FlowchemComponentClient)
    assert test_component.component_info.name == "FakeSpecificComponent"
    assert test_component.get("fake_receive_data").json() == 0.5


async def test_async_get_all_flowchem_devices(flowchem_test_instance):
    dev_dict = await async_get_all_flowchem_devices()
    assert "test-device" in dev_dict
