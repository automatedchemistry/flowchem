"""The FlowControl bubble detector channel as a shared BubbleSensor (no hardware needed)."""

import pytest

from flowchem.devices.custom.bubble_detector import (
    STATE_BUBBLE,
    STATE_EMPTY,
    BubbleDetector,
    ChannelStatus,
)
from flowchem.devices.custom.bubble_detector_component import BubbleDetectorChannel

STATE_LIQUID = 3  # firmware state code, see STATE_NAMES


@pytest.fixture
def detector() -> BubbleDetector:
    # The constructor does not open the port: seed one channel as if a frame had arrived
    device = BubbleDetector(port="COM_TEST", name="test-bd")
    device.n_sensors = 1
    device.interval_ms = 20000
    device.channels = [ChannelStatus()]
    device._apply_readings([STATE_LIQUID], [1000])
    return device


@pytest.fixture
def channel(detector) -> BubbleDetectorChannel:
    return BubbleDetectorChannel("sensor-1", detector, channel=1)


def test_channel_is_bubble_sensor(channel):
    # The class list is what the orchestrator matches figures against
    assert "BubbleSensor" in channel.component_info.corresponding_class


def test_bubble_detected_route_registered_once(channel):
    paths = [route.path for route in channel.router.routes]
    assert sum(path.endswith("/bubble-detected") for path in paths) == 1


async def test_bubble_detected_follows_device_state(detector, channel):
    assert await channel.bubble_detected() is False

    detector._apply_readings([STATE_BUBBLE], [3000])
    assert await channel.bubble_detected() is True

    # The board reports an empty tube as its own state, which is not a bubble
    detector._apply_readings([STATE_EMPTY], [3600])
    assert await channel.bubble_detected() is False
