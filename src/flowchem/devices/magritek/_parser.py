"""Functions related to instrument response parsing."""

import warnings
from enum import Enum

from lxml import etree


class StatusNotification(Enum):
    """Represent the type of the status notification."""

    STARTED = 1  # <State status="Ready"> received, starting protocol
    RUNNING = 2  # All good, <Progress> received, protocol is running
    STOPPING = 3  # Abort called, waiting for current scan end
    FINISHING = 4  # Upon <State status="Ready": acquisition over, processing ongoing
    COMPLETED = 5  # Upon <Completed>: with this also processing/saving data is over
    ERROR = 6  # If an error occurs
    UNKNOWN = 7


def parse_status_notification(xml_message: etree._Element):
    """Parse a status notification reply."""
    status_notification = xml_message.find(".//StatusNotification")
    assert status_notification is not None, "a StatusNotification tree is needed"

    # StatusNotification child can be <State> (w/ submsg), <Progress>, <Completed> or <Error>
    match status_notification[0].tag, status_notification[0].get("status"):
        case ["State", "Running"]:
            status = StatusNotification.STARTED
        case ["State", "Ready"]:
            status = StatusNotification.FINISHING
        case ["State", "Stopping"]:
            status = StatusNotification.STOPPING
        case ["Progress", None]:
            status = StatusNotification.RUNNING
        case ["Completed", None]:
            status = StatusNotification.COMPLETED
        case ["Error", None]:
            status = StatusNotification.ERROR
        case _:
            warnings.warn("Could not recognize StatusNotification state!")
            status = StatusNotification.UNKNOWN

    return status, status_notification[0].get("dataFolder")
