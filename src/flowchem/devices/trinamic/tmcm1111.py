"""Control a TMCM-1111 StepRocker as a linear fraction collector."""

from __future__ import annotations

from flowchem.devices.trinamic.tmcl import (
    TMCL_FRAME_SIZE,
    TMCL_STATUS_MESSAGES,
    MVPType,
    RFSType,
    TMCLCommandNumber,
    TMCLReply,
    TMCLRequest,
    TMCLSerialIO,
    decode_tmcl_reply,
    tmcl_checksum,
)
from flowchem.devices.trinamic.tmcm1111_component import TMCM1111FractionCollector
from flowchem.devices.trinamic.tmcm_base import AxisParameter, TMCMStepRockerBase

__all__ = [
    "TMCL_FRAME_SIZE",
    "TMCL_STATUS_MESSAGES",
    "AxisParameter",
    "MVPType",
    "RFSType",
    "TMCLCommandNumber",
    "TMCLReply",
    "TMCLRequest",
    "TMCM1111",
    "TMCM1111IO",
    "TMCM1111_MOTOR",
    "decode_tmcl_reply",
    "tmcl_checksum",
]

# Backward-compatible aliases: the TMCL transport and single-motor constant
# are now shared across the whole StepRocker family (see tmcl.py /
# tmcm_base.py), but existing code/tests import them from this module.
TMCM1111IO = TMCLSerialIO
TMCM1111_MOTOR = 0


class TMCM1111(TMCMStepRockerBase):
    """TMCM-1111 single-axis controller (TMC4361-based) used as a linear fraction collector."""

    MODEL_NAME = "1111"
    MODEL_DISPLAY_NAME = "TMCM-1111 StepRocker"
    COMPONENT_CLASS = TMCM1111FractionCollector
