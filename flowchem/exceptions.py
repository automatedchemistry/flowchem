class DeviceError(BaseException):
    """ Generic DeviceError """
    pass


class InvalidConfiguration(DeviceError):
    """ The configuration provided is not valid, e.g. no connection w/ device obtained """
    pass
