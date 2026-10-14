"""Components of the USB bubble detector."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import HTTPException

from flowchem.components.flowchem_component import FlowchemComponent
from flowchem.components.sensors.photo_sensor import PhotoSensor

if TYPE_CHECKING:
    from .bubble_detector import BubbleDetector


async def _call(coroutine):
    """Turn a device error into an HTTP 503 with the device's message instead of a bare 500."""
    from .bubble_detector import BubbleDetectorError

    try:
        return await coroutine
    except BubbleDetectorError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


class BubbleDetectorControl(FlowchemComponent):
    """Device-wide readings and settings of the bubble detector."""

    def __init__(self, name: str, hw_device: BubbleDetector) -> None:
        super().__init__(name, hw_device)
        self.hw_device: BubbleDetector

        self.add_api_route("/all", self.get_all, methods=["GET"])
        self.add_api_route("/clear-events", self.clear_events, methods=["PUT"])
        self.add_api_route("/info", self.get_info, methods=["GET"])
        self.add_api_route("/interval", self.get_interval, methods=["GET"])
        self.add_api_route("/interval", self.set_interval, methods=["PUT"])
        self.add_api_route("/active-sensors", self.get_active_sensors, methods=["GET"])
        self.add_api_route("/active-sensors", self.set_active_sensors, methods=["PUT"])
        self.add_api_route("/display-time", self.get_display_time, methods=["GET"])
        self.add_api_route("/display-time", self.set_display_time, methods=["PUT"])
        self.add_api_route("/calibration", self.get_calibration, methods=["GET"])
        self.add_api_route("/bubble-thresholds", self.get_bubble_thresholds, methods=["GET"])
        self.add_api_route("/reset", self.reset, methods=["PUT"])

    async def get_all(self) -> dict:
        """State, value and latched events of every active sensor, plus the age of the last frame."""
        return await _call(self.hw_device.get_all())

    async def clear_events(self) -> bool:
        """Reset the latched bubble/empty counters of every sensor."""
        self.hw_device.clear_events()
        return True

    async def get_info(self) -> dict:
        """Firmware version, serial number, baud rate and port."""
        return await _call(self.hw_device.get_info())

    async def get_interval(self) -> int:
        """Send interval of the periodic data frame, in ms."""
        return await _call(self.hw_device.get_interval())

    async def set_interval(self, interval_ms: int) -> int:
        """Set the send interval in ms (state changes are always sent immediately)."""
        return await _call(self.hw_device.set_interval(interval_ms))

    async def get_active_sensors(self) -> int:
        """Number of active sensors (always sensors 1..n)."""
        return await _call(self.hw_device.get_active_sensors())

    async def set_active_sensors(self, n: int) -> int:
        """Set the number of active sensors (1-6). Needs a reset and a flowchem restart."""
        return await _call(self.hw_device.set_active_sensors(n))

    async def get_display_time(self) -> int:
        """Display timeout in seconds."""
        return await _call(self.hw_device.get_display_time())

    async def set_display_time(self, seconds: int) -> int:
        """Set the display timeout in seconds."""
        return await _call(self.hw_device.set_display_time(seconds))

    async def get_calibration(self) -> dict:
        """Fluid and empty calibration values of all 6 sensor slots."""
        return await _call(self.hw_device.get_calibration())

    async def get_bubble_thresholds(self) -> dict:
        """Bubble detection threshold of all 6 sensor slots."""
        thresholds = await _call(self.hw_device.get_bubble_thresholds())
        return {f"sensor-{i + 1}": t for i, t in enumerate(thresholds)}

    async def reset(self) -> bool:
        """Soft-reset the device (needed for setting changes to take effect)."""
        return await _call(self.hw_device.reset())


class BubbleDetectorChannel(PhotoSensor):
    """One optical sensor of the bubble detector."""

    def __init__(self, name: str, hw_device: BubbleDetector, channel: int) -> None:
        super().__init__(name, hw_device)
        self.hw_device: BubbleDetector
        self.channel = channel

        self.add_api_route("/status", self.get_status, methods=["GET"])
        self.add_api_route("/state", self.get_state, methods=["GET"])
        self.add_api_route("/bubble-detected", self.bubble_detected, methods=["GET"])
        self.add_api_route("/events", self.get_events, methods=["GET"])
        self.add_api_route("/clear-events", self.clear_events, methods=["PUT"])
        self.add_api_route("/fluid-calibration", self.get_fluid_calibration, methods=["GET"])
        self.add_api_route("/fluid-calibration", self.set_fluid_calibration, methods=["PUT"])
        self.add_api_route("/empty-calibration", self.get_empty_calibration, methods=["GET"])
        self.add_api_route("/empty-calibration", self.set_empty_calibration, methods=["PUT"])
        self.add_api_route("/bubble-threshold", self.get_bubble_threshold, methods=["GET"])
        self.add_api_route("/bubble-threshold", self.set_bubble_threshold, methods=["PUT"])

    async def get_status(self) -> dict:
        """Everything known about this sensor: state, value, age and latched events."""
        return await _call(self.hw_device.get_channel(self.channel))

    async def acquire_signal(self) -> int:
        """Raw ADC value of the sensor."""
        return (await self.get_status())["value"]

    async def read(self) -> int:
        """Raw ADC value of the sensor."""
        return await self.acquire_signal()

    async def get_state(self) -> dict:
        """State code (1 empty, 2 bubble, 3 liquid) and its name."""
        status = await self.get_status()
        return {"state": status["state"], "state_name": status["state_name"]}

    async def bubble_detected(self) -> bool:
        """True while the sensor currently sees a bubble."""
        return (await self.get_status())["bubble_detected"]

    async def get_events(self) -> dict:
        """Bubbles and empty-tube events counted since the last clear."""
        status = await self.get_status()
        keys = ("bubble_count", "empty_count", "last_bubble_at", "last_empty_at", "events_cleared_at")
        return {k: status[k] for k in keys}

    async def clear_events(self) -> bool:
        """Reset the latched counters of this sensor."""
        self.hw_device.clear_events(self.channel)
        return True

    async def calibrate_zero(self):
        """Not available: the firmware has no factory re-zero. Use fluid-/empty-calibration."""
        raise HTTPException(
            status_code=501,
            detail="Bubble detector has no zero calibration; use /fluid-calibration and /empty-calibration",
        )

    async def get_fluid_calibration(self) -> int:
        """ADC calibration value for a liquid-filled tube."""
        return await _call(self.hw_device.get_fluid_calibration(self.channel))

    async def set_fluid_calibration(self, value: int) -> int:
        """Set the ADC calibration value for a liquid-filled tube."""
        return await _call(self.hw_device.set_fluid_calibration(self.channel, value))

    async def get_empty_calibration(self) -> int:
        """ADC calibration value for an empty tube."""
        return await _call(self.hw_device.get_empty_calibration(self.channel))

    async def set_empty_calibration(self, value: int) -> int:
        """Set the ADC calibration value for an empty tube."""
        return await _call(self.hw_device.set_empty_calibration(self.channel, value))

    async def get_bubble_threshold(self) -> int:
        """Bubble detection threshold of this sensor."""
        thresholds = await _call(self.hw_device.get_bubble_thresholds())
        return thresholds[self.channel - 1]

    async def set_bubble_threshold(self, value: int) -> int:
        """Set the bubble threshold (rejected by firmware 1.0 07.10.2026 - firmware bug)."""
        return await _call(self.hw_device.set_bubble_threshold(self.channel, value))
