"""FastAPI server for devices control."""
from importlib.metadata import metadata, version
from fastapi import APIRouter, FastAPI
from loguru import logger
from starlette.responses import RedirectResponse

from flowchem.components.device_info import DeviceInfo
from flowchem.devices.flowchem_device import RepeatedTaskInfo
from flowchem.vendor.repeat_every import repeat_every


class FastAPIServer:
    def __init__(
        self, filename: str = "", host: str = "127.0.0.1", port: int = 8000
    ) -> None:
        # Create FastAPI app
        self.app = FastAPI(
            title=f"Flowchem - {filename}",
            description=metadata("flowchem")["Summary"],
            version=version("flowchem"),
            license_info={
                "name": "MIT License",
                "url": "https://opensource.org/licenses/MIT",
            },
        )
        self.base_url = rf"http://{host}:{port}"
        self.configuration_dict: dict = {}

        self._add_root_redirect()
        self._add_configuration_retrive()

        logger.debug("HTTP ASGI server app created")

    def _add_root_redirect(self) -> None:
        @self.app.route("/")
        def home_redirect_to_docs(request):
            """Redirect root to `/docs` to enable interaction w/ API."""
            return RedirectResponse(url="/docs")

    def _add_configuration_retrive(self) -> None:
        @self.app.get(
            "/config",
            tags=["system"],
        )
        def config():
            return self.configuration_dict

    def add_background_tasks(self, repeated_tasks: RepeatedTaskInfo):
        """Schedule repeated tasks to run upon server startup."""
        seconds_delay, task = repeated_tasks
        @self.app.on_event("startup")
        @repeat_every(seconds=seconds_delay)
        async def my_task():
            logger.debug(f"Running repeated task {task.__name__} every time...")
            await task()

    def add_device(self, device):
        """Add device to server."""
        # Add components URL to device_info
        components_w_url = {
            component.name: f"{self.base_url}/{device.name}/{component.name}"
            for component in device.components
        }
        device.device_info.components = components_w_url

        # Base device endpoint
        device_root = APIRouter(prefix=f"/{device.name}", tags=[device.name])
        device_root.add_api_route(
            "/",
            device.get_device_info,
            methods=["GET"],
            response_model=DeviceInfo,
        )
        self.app.include_router(device_root)

        # Add repeated tasks for device if any
        if tasks := device.repeated_task():
            self.add_background_tasks(tasks)

        # add device components
        logger.debug(f"Device '{device.name}' has {len(device.components)} components")
        for component in device.components:
            self.app.include_router(component.router, tags=component.router.tags)
            logger.debug(f"Router <{component.router.prefix}> added to app!")
