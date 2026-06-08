from typing import TYPE_CHECKING

from pydantic import AnyHttpUrl

if TYPE_CHECKING:
    from flowchem.client.device_client import FlowchemDeviceClient
from flowchem.components.component_info import ComponentInfo


class FlowchemComponentClient:
    def __init__(self, url: AnyHttpUrl, parent: "FlowchemDeviceClient") -> None:
        self.base_url = str(url)
        self._parent = parent
        self._session = parent._session
        self.component_info = ComponentInfo.model_validate_json(self.get("").text)

    def get(self, url, **kwargs):
        """Send a GET request. Returns :class:`Response` object."""
        return self._session.get(self.base_url + "/" + url, **kwargs)

    def post(self, url, data=None, json=None, **kwargs):
        """Send a POST request. Returns :class:`Response` object."""
        return self._session.post(
            self.base_url + "/" + url, data=data, json=json, **kwargs
        )

    def put(self, url, data=None, **kwargs):
        """Send a PUT request. Returns :class:`Response` object."""

        # Inspect the keyword arguments type to avoid problems with arguments of list type which must be handed to fastapi as str
        for key, arg in kwargs.get("params", {}).items():
            if type(arg) is list:
                kwargs["params"][key] = str(arg)

        return self._session.put(self.base_url + "/" + url, data=data, **kwargs)
