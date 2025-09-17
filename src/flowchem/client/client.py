import time

import requests
from loguru import logger
from pydantic import AnyHttpUrl
from pydantic.type_adapter import TypeAdapter
from zeroconf import ServiceBrowser, Zeroconf

from flowchem.client.common import (
    FLOWCHEM_TYPE,
    FlowchemCommonDeviceListener,
    device_url_from_service_info,
    flowchem_devices_from_url_dict,
    zeroconf_name_to_device_name,
)
from flowchem.client.device_client import FlowchemDeviceClient


class FlowchemDeviceListener(FlowchemCommonDeviceListener):
    """Listener for Zeroconf service browser."""
    def _save_device_info(self, zc: Zeroconf, type_: str, name: str, active_ips: list | None = None) -> None:
        if service_info := zc.get_service_info(type_, name):
            device_name = zeroconf_name_to_device_name(name)
            if url := device_url_from_service_info(service_info, device_name, active_ips):
                self.flowchem_devices[device_name] = url
        else:
            logger.warning(f"No info for service {name}!")


def get_all_flowchem_devices(timeout: float = 3000) -> dict[str, FlowchemDeviceClient]:
    """Search for flowchem devices and returns them in a dict (key=name, value=IPv4Address)."""
    listener = FlowchemDeviceListener()
    browser = ServiceBrowser(Zeroconf(), FLOWCHEM_TYPE, listener)
    time.sleep(timeout / 1000)
    browser.cancel()

    return flowchem_devices_from_url_dict(listener.flowchem_devices)


def get_flowchem_devices_from_url(url: str, timeout: int = 5) -> dict[str, FlowchemDeviceClient]:
    """
    Fetch Flowchem device clients from a FastAPI server exposing the OpenAPI spec.

    Args:
        url (str): The base URL of the FastAPI server (e.g., "http://localhost:8000").
        timeout (int): Timeout in seconds for the request.

    Returns:
        Dict[str, FlowchemDeviceClient]: A dictionary mapping device names to their client instances.

    Raises:
        requests.RequestException: If the request fails.
        ValueError: If the OpenAPI spec is invalid or missing expected paths.
    """
    # Ensure URL ends cleanly without trailing slash
    if url.endswith("/"):
        url = url[:-1]

    # Build the OpenAPI URL and make the request
    openapi_url = f"{url}/openapi.json"
    try:
        response = requests.get(openapi_url, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to fetch OpenAPI spec from {openapi_url}") from e

    try:
        data = response.json()
    except ValueError as e:
        raise ValueError("Response is not valid JSON.") from e

    # Parse paths and extract unique devices
    flowchem_devices: dict[str, FlowchemDeviceClient] = {}
    for path in data.get("paths", {}):
        parts = path.strip("/").split("/")
        if parts:
            device = parts[0]
            if device not in flowchem_devices:
                flowchem_devices[device] = FlowchemDeviceClient(url=TypeAdapter(AnyHttpUrl).validate_python(f"{url}/{device}"))

    return flowchem_devices

if __name__ == "__main__":
    flowchem_devices: dict[str, FlowchemDeviceClient] = get_all_flowchem_devices()
    print(flowchem_devices)
