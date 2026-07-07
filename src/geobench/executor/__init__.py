"""Executor module."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import cache
import importlib
import inspect
import pkgutil
import subprocess

import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExecutorInfo:
    """Metadata describing a collector."""

    type: str
    name: str
    description: str


class Executor(ABC):
    """Executor class."""

    @classmethod
    @abstractmethod
    def get_info(cls) -> ExecutorInfo:
        """Return executor information."""

    def __init__(self, config: dict | None = None):
        """Initialize the executor.

        Args:
            config: Optional configuration.
        """
        self.config = self.get_config(config or {})

    @abstractmethod
    def get_config(self, args: dict) -> dict:
        """Return executor configuration considering the arguments."""

    @abstractmethod
    def execute(self, command, args: dict | None = None) -> subprocess.Popen:
        """Execute command with the specified arguments."""

    def get_help(self, command) -> str:
        """Return help content for the command."""
        return f"Help not found for: {command}"


@cache
def get_executors() -> dict[str, Executor]:
    """Return dictionary of available collectors."""
    executors = {}

    for _, name, _ in pkgutil.iter_modules([__path__[0]]):
        module = importlib.import_module(f".{name}", f"{Executor.__module__}")
        for name, cls in inspect.getmembers(module, inspect.isclass):
            if issubclass(cls, Executor) and cls is not Executor:
                if not cls.__abstractmethods__:
                    type = cls.get_info().type
                    executors[type] = cls
                else:
                    logger.debug("%s has abstract methods, skipping", cls)

    return executors
