import asyncio
from typing import Any

from loguru import logger
from zeroconf import Zeroconf
from zeroconf.asyncio import AsyncServiceBrowser, AsyncServiceInfo

from flowchem.client.client import FlowchemCommonDeviceListener
from flowchem.client.common import (
    FLOWCHEM_TYPE,
    device_url_from_service_info,
    flowchem_devices_from_url_dict,
    zeroconf_name_to_device_name,
)
from flowchem.client.device_client import FlowchemDeviceClient


class FlowchemAsyncDeviceListener(FlowchemCommonDeviceListener):
    bg_tasks: set[Any] = set()

    async def _resolve_service(self, zc: Zeroconf, type_: str, name: str):
        service_info = AsyncServiceInfo(type_, name)
        await service_info.async_request(zc, 3000)
        if service_info:
            device_name = zeroconf_name_to_device_name(name)
            if url := device_url_from_service_info(service_info, device_name):
                self.flowchem_devices[device_name] = url
        else:
            logger.warning(f"No info for service {name}!")

    def _save_device_info(
        self, zc: Zeroconf, type_: str, name: str, active_ips=None
    ) -> None:
        task = asyncio.ensure_future(self._resolve_service(zc, type_, name))
        self.bg_tasks.add(task)
        task.add_done_callback(self.bg_tasks.discard)


async def async_get_all_flowchem_devices(
    timeout: float = 3000,
) -> dict[str, FlowchemDeviceClient]:
    """Search for flowchem devices and returns them in a dict (key=name, value=IPv4Address)."""
    listener = FlowchemAsyncDeviceListener()
    browser = AsyncServiceBrowser(Zeroconf(), FLOWCHEM_TYPE, listener)
    await asyncio.sleep(timeout / 1000)
    await browser.async_cancel()

    return flowchem_devices_from_url_dict(listener.flowchem_devices)


if __name__ == "__main__":

    async def main():
        dev_info = await async_get_all_flowchem_devices()
        print(dev_info)

    asyncio.run(main())
