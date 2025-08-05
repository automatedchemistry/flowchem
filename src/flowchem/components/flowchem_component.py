from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import inspect

from fastapi import APIRouter
from loguru import logger

from flowchem.components.component_info import ComponentInfo

if TYPE_CHECKING:
    from flowchem.devices.flowchem_device import FlowchemDevice


class FlowchemComponent:
    """
    A base class for Flowchem components that integrates with the decomposition of the hardware device.

    This class provides the foundational setup for creating abstract components of hardware devices. It forms the
    foundation to expose API routes for interacting with the hardware through a hierarchical structure.

    Attributes:
    -----------
    name : str
        The name of the component.
    hw_device : FlowchemDevice
        The hardware device instance associated with this component.
    component_info : ComponentInfo
        Metadata about the component.
    _router : APIRouter
        The API router for the component to define HTTP endpoints.

    Methods:
    --------
    add_api_route(path: str, endpoint: Callable, **kwargs):
        Add an API route to the component's router.
    get_component_info() -> ComponentInfo:
        Retrieve the component's metadata.
    """
    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        """
        Initialize the FlowchemComponent with a name and associated hardware device.

        Parameters:
        -----------
        name : str
            The name assigned to this component.
        hw_device : FlowchemDevice
            The hardware device instance associated with this component.
        """
        self.name = name
        self.hw_device = hw_device
        self.component_info = ComponentInfo(
            name=name,
            parent_device=self.hw_device.name,
            corresponding_class=[cls.__name__ for cls in inspect.getmro(self.__class__)]
        )

        # Initialize router
        self._router = APIRouter(
            prefix=f"/{self.component_info.parent_device}/{name}",
            tags=[self.component_info.parent_device],
        )
        self.add_api_route(
            "/",
            self.get_component_info,
            methods=["GET"],
            response_model=ComponentInfo,
        )

    @property
    def router(self):
        """
        Return the API router.

        This serves as a hook for subclasses to add their specific routes.

        Returns:
        --------
        APIRouter
            The API router instance.
        """
        return self._router

    def add_api_route(self, path: str, endpoint: Callable, **kwargs):
        """
        Add an API route to the component's router.

        This method allows subclasses to define their own API endpoints.

        Parameters:
        -----------
        path : str
            The URL path for the API route.
        endpoint : Callable
            The function to be called when the route is accessed.
        kwargs : dict
            Additional arguments to configure the route.
        """
        logger.debug(f"Adding route {path} for router of {self.name}")
        self._router.add_api_route(path, endpoint, **kwargs)

    def get_component_info(self) -> ComponentInfo:
        """
        Retrieve the component's metadata.

        This endpoint provides information about the component, such as its name and associated hardware device.

        Returns:
        --------
        ComponentInfo
            Metadata about the component.
        """
        return self.component_info

    def get_function_by_route(self, route_path: str):
        route_path = f"/{self.component_info.parent_device}/{self.name}/{route_path}"
        for route in self._router.routes:
            if hasattr(route, 'path') and hasattr(route, 'endpoint') and route.path == route_path:
                return route.endpoint
        return None


