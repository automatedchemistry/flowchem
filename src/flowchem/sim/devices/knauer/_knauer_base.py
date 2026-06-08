"""Shared simulated Knauer Ethernet transport layer."""

from __future__ import annotations

import asyncio
from typing import cast

from loguru import logger


class SimulatedKnauerEthernetDevice:
    """
    Drop-in replacement for ``KnauerEthernetDevice`` transport.

    Subclasses override ``_handle_command(message)`` to return the
    appropriate response string.  The lock and reader/writer attributes
    are created here so that the real device __init__ (which calls
    ``super().__init__(ip, mac, **kwargs)``) still works.
    """

    def __init__(self, ip_address=None, mac_address=None, **kwargs):
        # Accept (and ignore) ip/mac — no network needed.
        super().__init__(  # type: ignore[call-arg]
            ip_address="127.0.0.1", mac_address=None, **kwargs
        )
        self._lock = asyncio.Lock()
        # Fake reader/writer so attribute access never raises.
        self._reader = cast(asyncio.StreamReader, None)
        self._writer = cast(asyncio.StreamWriter, None)

    # ------------------------------------------------------------------
    # Override only the two network primitives used by the real classes
    # ------------------------------------------------------------------

    async def initialize(self):
        """Skip TCP connection; subclass calls super().initialize() to run device-level init."""
        logger.info(f"[SIM] {self.__class__.__name__} '{self.name}' — skipping TCP connection.")  # type: ignore[attr-defined]

    async def _send_and_receive(self, message: str) -> str:
        """Intercept every ASCII message and return a simulated reply."""
        async with self._lock:
            reply = self._handle_command(message)
            logger.debug(f"[SIM] {message!r} → {reply!r}")
            return reply

    # ------------------------------------------------------------------
    # Override in subclasses
    # ------------------------------------------------------------------

    def _handle_command(self, message: str) -> str:  # pragma: no cover
        raise NotImplementedError
