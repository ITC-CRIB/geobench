class MissingParameterError(Exception):
    pass

class WrongQGISCommandError(Exception):
    pass


class GeobenchError(Exception):
    """Base class for exceptions in this module."""
    pass


class GeobenchCommandError(GeobenchError):
    """Base class for command-related errors in Geobench."""
    pass


class ExecutableNotFoundError(GeobenchCommandError):
    """Raised when a required executable is not found."""
    pass


class SoftwareConfigurationError(GeobenchCommandError):
    """Raised when there's an error configuring software (e.g., QGIS version check)."""
    pass


class ScriptNotFoundError(GeobenchCommandError):
    """Raised when a script file (Python, shell) is not found."""
    pass


class TemplateFileNotFoundError(GeobenchCommandError):
    """Raised when a Jinja2 template file is not found."""
    pass


class ParameterEncodingError(GeobenchCommandError):
    """Raised when there's an error encoding command parameters."""
    pass


class UnsupportedCommandTypeError(GeobenchCommandError):
    """Raised when an unsupported command type is specified."""
    pass