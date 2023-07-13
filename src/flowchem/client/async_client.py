import asyncio

from loguru import logger
from zeroconf import Zeroconf
from zeroconf.asyncio import AsyncZeroconf, AsyncServiceBrowser, AsyncServiceInfo

from flowchem.client.client import FlowchemCommonDeviceListener
from flowchem.client.common import (
    FLOWCHEM_TYPE,
    device_name_to_zeroconf_name,
    device_url_from_service_info,
    zeroconf_name_to_device_name,
    flowchem_devices_from_url_dict,
)
from flowchem.client.device_client import FlowchemDeviceClient


class FlowchemAsyncDeviceListener(FlowchemCommonDeviceListener):
    async def _resolve_service(self, zc: Zeroconf, type_: str, name: str):
        # logger.debug(f"MDNS resolving device '{name}'")
        service_info = AsyncServiceInfo(type_, name)
        await service_info.async_request(zc, 3000)
        if service_info:
            device_name = zeroconf_name_to_device_name(name)
            if url := device_url_from_service_info(service_info, device_name):
                self.flowchem_devices[device_name] = url
        else:
            logger.warning(f"No info for service {name}!")

    def _save_device_info(self, zc: Zeroconf, type_: str, name: str) -> None:
        asyncio.ensure_future(self._resolve_service(zc, type_, name))


async def async_get_flowchem_device_by_name(
    device_name, timeout: int = 10000
) -> FlowchemDeviceClient | None:
    """
    Given a flowchem device name, search for it via mDNS and return its URL if found.

    Args:
        timeout: timout for search in ms (at least 2 seconds needed)
        device_name: name of the device

    Returns: URL object, empty if not found
    """
    zc = AsyncZeroconf()
    service_info = await zc.async_get_service_info(
        type_=FLOWCHEM_TYPE,
        name=device_name_to_zeroconf_name(device_name),
        timeout=timeout,
    )
    if service_info:
        if url := device_url_from_service_info(service_info, device_name):
            FlowchemDeviceClient(url)
    return None


async def async_get_all_flowchem_devices(
    timeout: float = 10000,
) -> dict[str, FlowchemDeviceClient]:
    """
    Search for flowchem devices and returns them in a dict (key=name, value=IPv4Address)
    """
    listener = FlowchemAsyncDeviceListener()
    browser = AsyncServiceBrowser(Zeroconf(), FLOWCHEM_TYPE, listener)
    await asyncio.sleep(timeout / 1000)
    await browser.async_cancel()

    return flowchem_devices_from_url_dict(listener.flowchem_devices)


if __name__ == "__main__":

    async def main():
        dev = await async_get_flowchem_device_by_name("test-device")
        print(dev)

        dev_info = await async_get_all_flowchem_devices()
        print(dev_info)

    asyncio.run(main())
