"""Reachability status enum for FlowchemComponent.is_reachable()."""

from enum import Enum


class ReachabilityStatus(str, Enum):
    ONLINE = "online"    # probe succeeded — device responded
    OFFLINE = "offline"  # probe failed with exception — device didn't respond
    UNKNOWN = "unknown"  # no probe available — status cannot be determined
