from flowchem.components.flowchem_component import FlowchemComponent
from flowchem.devices.flowchem_device import FlowchemDevice
from typing import Dict, Optional
from loguru import logger
import asyncio
import threading
import time


class SensorBase(FlowchemComponent):
    """
    SensorBase is a component for monitoring and triggering actions based on specific conditions
    from hardware sensors. It periodically checks values from specified methods and verifies if they
    fall within the defined boundaries.

    Inherits from:
        FlowchemComponent: A base class representing a flowchem component.

    Attributes:
        _sample_time (float): Interval in seconds for sampling the watched methods. Default is 2.0.
        _lock (threading.Lock): Ensures thread-safe operations on `_methods`.
        threading (Optional[threading.Thread]): Thread running the monitoring loop.
        _methods (Dict[str, Dict[str, Optional[float]]]): Dictionary holding methods to watch and their
            conditions (`greater_than` and `less_than`).
        _loop (bool): Controls the monitoring loop.

    API Endpoints:
        /watch (PUT): Starts watching a method with specified conditions.
        /stop-watch (PUT): Stops the monitoring loop.

    Methods:
        watch(api: str, greater_than: Optional[float], less_than: Optional[float], sample_time: float):
            Asynchronously starts watching a method and checks if its output is within the specified limits.

        stop_watch():
            Asynchronously stops the monitoring loop.

        __run_loop():
            Internal method that runs the monitoring loop in a separate thread.

        __inspect(value: float, greater: Optional[float], less: Optional[float]) -> bool:
            Checks if the value violates the conditions (greater_than or less_than).

    Example:
        sensor = SensorBase(name="MySensor", hw_device=my_hw_device)
        await sensor.watch(api="/some-method", greater_than=10.0, less_than=20.0)
        await sensor.stop_watch()

    Notes:
        - The class uses threading to run the monitoring loop without blocking the main event loop.
        - Thread safety is ensured using `_lock` when accessing `_methods`.
        - This class is designed to be used with FastAPI as it registers API routes.
    """
    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:

        super().__init__(name=name, hw_device=hw_device)

        self.add_api_route("/watch", self.watch, methods=["PUT"])

        self.add_api_route("/stop-watch", self.stop_watch, methods=["PUT"])

        self._sample_time: float = 2.0

        self._lock = threading.Lock()

        self.threading: Optional[threading.Thread] = None

        self._methods: Dict[str, Dict[str, Optional[float]]] = {}

        self._loop = True

    async def watch(self,
                    api: str,
                    greater_than: float | None = None,
                    less_than: float | None = None,
                    sample_time: float = 2.0):
        """
        Starts monitoring the specified method and checks its output against the defined conditions.

        Args:

            api (str): The API route or method name to watch.

            greater_than (Optional[float]): Trigger an alert if the method's return value is greater than this.

            less_than (Optional[float]): Trigger an alert if the method's return value is less than this.

            sample_time (float): Time interval in seconds for checking the value. Default is 2.0 seconds.

        Behavior:

            - Stops any existing monitoring loop before starting a new one.

            - Updates the watch conditions for the specified method.

            - Starts a new thread to run the monitoring loop.

        Raises:

            ValueError: If the specified `api` method does not exist.

            RuntimeError: If the monitoring thread cannot be started.

        Example:

            api(str)=some-method, greater_than(float)=10.0, less_than(str)=20.0, sample_time(float)=1.5

        Notes:
            - If the method is already being watched, its configuration will be overwritten.

            - The monitoring loop runs in a separate thread to avoid blocking the event loop.
        """

        if api in self._methods:
            logger.warning(f"Overwriting existing watch configuration for {api}.")

        if self.threading and self.threading.is_alive():
            self._loop = False
            self.threading.join()

        self._sample_time = sample_time

        with self._lock:
            self._methods[api] = {"greater_than": greater_than, "less_than": less_than}

        self.threading = threading.Thread(target=self.__run_loop)
        self.threading.start()

    async def stop_watch(self):

        """
        Stops the monitoring loop for all watched methods.

        Behavior:

            - Sets the `_loop` flag to `False` to terminate the monitoring thread.

            - Ensures that the monitoring thread is properly joined before returning.

        Notes:

            - This method is non-blocking as it uses `async`.
            - It safely stops the monitoring thread, preventing potential race conditions.
        """
        if self.threading and self.threading.is_alive():

            self._loop = False

    def __run_loop(self):

        self._loop = True

        toc = time.perf_counter()

        while self._loop:

            now = time.perf_counter()

            if now - toc >= self._sample_time:

                with self._lock:

                    for method in self._methods:

                        endpoint = self.get_function_by_route(route_path=method)

                        if not endpoint:
                            logger.error(f"Method {method} not found in {self.__class__.__name__}.")
                            continue

                        value = asyncio.run(endpoint())

                        if type(value) not in [float, int]:
                            logger.error(f"The {method} of the component/device: {self.name}/"
                                         f"{self.hw_device.name} return a unexpected value type {type(value)}."
                                         f"The watch approach was implemented only to analise float or int datas."
                                         f"Considering stop the watch.")
                            continue

                        a = self._methods[method]['less_than']
                        b = self._methods[method]['greater_than']

                        if self.__inspect(value, greater=b, less=a):
                            logger.error(f"The {method} of the component/device: {self.name}/"
                                         f"{self.hw_device.name} should obey the rule: "
                                         f"{a}< value <{b}, however it returned: {value}")

                toc = time.perf_counter()

        # After finishe the whatching
        self._methods = {}

    @staticmethod
    def __inspect(value: float, greater: Optional[float] = None, less: Optional[float] = None) -> bool:

        if greater:
            if value > greater:
                return True
        if less:
            if value < less:
                return True
        return False


if __name__ == "__main__":

    from flowchem.devices.fakedevice import FakeDeviceExample

    sensor = SensorBase(name="some", hw_device=FakeDeviceExample(name="dev"))

    asyncio.run(sensor.watch(api="aiomethod", greater_than=1))





