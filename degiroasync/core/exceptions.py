class DegiroAsyncException(Exception):
    "Base Exception for degiroasync module"


class ResponseError(DegiroAsyncException):
    "Raised when bad response has been received from server."


class BadCredentialsError(ResponseError):
    """
    Error raised when web API returns a badCredentials error.
    This is a specialized class of ReponseError."""
