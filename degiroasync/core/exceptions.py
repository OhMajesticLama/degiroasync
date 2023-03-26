class DegiroAsyncException(Exception):
    "Base Exception for degiroasync module"


class ResponseError(DegiroAsyncException):
    "Raised when bad response has been received from server."


class ContextError(DegiroAsyncException):
    """
    Raised when unexpected or incorrect context is detected.

    Example: when some required Session attributes are missing.
    """


class BadCredentialsError(ResponseError):
    """
    Error raised when web API returns a badCredentials error.
    This is a specialized class of ReponseError.
    """
