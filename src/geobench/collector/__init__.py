"""Collector module."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import cache
import importlib
import inspect
import pkgutil
import subprocess

import psutil

import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CollectorInfo:
    """Metadata describing a collector."""

    code: str
    name: str
    description: str


class Collector(ABC):
    """Abstract base class for collectors."""

    def __init__(self, config: dict | None = None):
        """Initialize collector."""
        self.config = config or {}

    @classmethod
    @abstractmethod
    def get_info(cls) -> CollectorInfo:
        """Return collector information."""

    @abstractmethod
    def collect(self) -> dict:
        """Collect current data.

        Returns:
            Dictionary containing collected data.
        """

    def cleanup(self, item: dict):
        """Clean empty data item attributes.

        Args:
            item: Data item to be cleaned.
        """
        remove = []
        for key, val in item.items():
            if val is None or val == -1:
                remove.append(key)
            if isinstance(val, dict):
                self.cleanup(val)
        for key in remove:
            del item[key]

    def transform(self, item: dict):
        """Perform transformation operations on the data item.

        Args:
            item: Data item to be transformed.
        """
        self.cleanup(item)

    def postprocess(self, data: list[dict]):
        """Postprocess collected data.

        Args:
            data: Collected data.
        """
        for item in data:
            self.transform(item)


class SystemCollector(Collector):
    """Abstract base class for system collectors."""


class ProcessCollector(Collector):
    """Abstract base class for process collectors."""

    def __init__(
        self,
        process: int | subprocess.Popen | psutil.Process,
        config: dict | None = None,
    ):
        """Initialize process collector."""
        super().__init__(config)

        if not isinstance(process, psutil.Process):
            if isinstance(process, subprocess.Popen):
                id = process.pid
            elif isinstance(process, int):
                id = process
            else:
                raise ValueError("Invalid process: %s", process)
            process = psutil.Process(id)

        self.process = process


@cache
def get_collectors() -> dict[str, Collector]:
    """Return dictionary of available collectors."""
    collectors = {}

    for _, name, _ in pkgutil.iter_modules([__path__[0]]):
        module = importlib.import_module(f".{name}", f"{Collector.__module__}")
        for name, cls in inspect.getmembers(module, inspect.isclass):
            if issubclass(cls, Collector) and cls is not Collector:
                if not cls.__abstractmethods__:
                    code = cls.get_info().code
                    collectors[code] = cls
                else:
                    logger.debug("%s has abstract methods, skipping", cls)

    return collectors


def get_collector(type: str, config: dict | None = None) -> Collector:
    """Return collector with the specified type and configuration.

    Args:
        type: Collector type.
        config: Optional configuration.

    Returns:
        Collector with the specified type and configuration.

    Raises:
        ValueError: If invalid collector type.
    """
    collector = get_collectors().get(type)
    if not collector:
        raise ValueError(f"Invalid collector type: {type}")
    return collector(config)
