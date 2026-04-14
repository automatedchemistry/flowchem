"""Exceptions used in the flowchem module."""


class DeviceError(Exception):
    """Generic DeviceError.

    Inherits from Exception (not BaseException) so that broad
    ``except Exception`` handlers can catch it, and so it does not
    accidentally suppress KeyboardInterrupt / SystemExit.
    """


class InvalidConfigurationError(DeviceError):
    """The configuration provided is not valid, e.g. no connection w/ device obtained."""
