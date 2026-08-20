"""Executor module."""

import importlib
import inspect
import logging
import pkgutil
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import cache
from typing import Any

from ..utils import is_empty

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExecutorOption:
    """Describes an executor configuration option.

    Attributes:
        description: A human-readable description of the option.
        type: The expected type of the option value.
        default: The default value when the options is not specified
        required: Whether the option is required.
        positional: Whether the option is a positional command-line argument.
    """

    description: str
    type: type
    default: Any = None
    required: bool = False
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
    def get_options(cls) -> dict[str, ExecutorOption]:
        """Return executor options."""
        return {}

    def __init__(self, config: dict | None = None, no_check: bool = False):
        """Initialize the executor.

        Args:
            config: Optional configuration.
        """
        config = config or {}
        opts = self.get_options()

        self.config = {}
        self.metadata = {}

        for key, val in config.items():
            if key not in opts:
                logger.debug("Invalid configuration option: %s=%s", key, val)
                continue
            # TODO: Add validation
            self.config[key] = val

        self.prepare_config()

        if no_check:
            return

        for key, opt in opts.items():
            if opt.required and is_empty(self.config.get(key)):
                raise ValueError(f"Missing configuration option: {key}")

    def prepare_config(self):
        """Complete and validate the configuration options."""

    @abstractmethod
    def execute(self, arguments: dict | None = None) -> int:
        """Start execution.

        Args:
            arguments: Optional arguments.

        Returns:
            Process id.
        """

    @abstractmethod
    def wait(self):
        """Wait until execution ends."""


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
