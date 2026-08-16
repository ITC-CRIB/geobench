"""Executor module."""

import importlib
import inspect
import logging
import pkgutil
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import cache
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExecutorOption:
    """Describes a configuration option supported by an executor.

    Attributes:
        description: A human-readable description of the option.
        type: The expected type of the option value.
        default: The default value when the options is not specified
        required: Whether the option is required.
        action: The argparse action to use.
        nargs: The number of command-line argument to consume.
        positional: Whether the option is a positional command-line argument.
    """

    description: str
    type: type
    default: Any = None
    required: bool = False
    action: str | None = None
    nargs: str | int | None = None
    positional: bool = False


@dataclass(frozen=True)
class ExecutorInfo:
    """Metadata describing a collector."""

    code: str
    name: str
    description: str


class Executor(ABC):
    """Executor class."""

    @classmethod
    @abstractmethod
    def get_info(cls) -> ExecutorInfo:
        """Return executor information."""

    @classmethod
    @abstractmethod
    def get_options(self) -> dict[str, ExecutorOption]:
        """Return executor options."""

    @staticmethod
    def _is_empty(val: Any) -> bool:
        return (
            val is None
            or (isinstance(val, str) and not val.strip())
            or (isinstance(val, (dict, list, set)) and not val)
        )

    def __init__(self, config: dict | None = None):
        """Initialize the executor.

        Args:
            config: Optional configuration.
        """
        opts = self.get_options()
        args = {}

        for key, val in config.items():
            if key not in opts:
                logger.debug("Invalid configuration option: %s=%s", key, val)
                continue
            # TODO: Add validation
            args[key] = val

        self.prepare_config(args)

        for key, opt in opts.items():
            if opt.required and self._is_empty(args.get(key)):
                raise ValueError(f"Missing configuration option: {key}")

        self.config = args

    def prepare_config(self, config: dict) -> None:
        """Complete the configuration options."""

    @abstractmethod
    def execute(self, command, args: dict | None = None) -> int:
        """Execute command with the specified arguments.

        Returns:
            Process id.
        """

    @abstractmethod
    def wait(self):
        """Wait until command execution ends."""

    def get_help(self, command) -> str:
        """Return help content for the command."""
        return f"Help not found for: {command}"


@cache
def get_executors() -> dict[str, type[Executor]]:
    """Return dictionary of available collector classes."""
    executors = {}

    for _, name, _ in pkgutil.iter_modules([__path__[0]]):
        module = importlib.import_module(f".{name}", f"{Executor.__module__}")
        for name, cls in inspect.getmembers(module, inspect.isclass):
            if issubclass(cls, Executor) and cls is not Executor:
                if not cls.__abstractmethods__:
                    code = cls.get_info().code
                    executors[code] = cls
                else:
                    logger.debug("%s has abstract methods, skipping", cls)

    return executors
