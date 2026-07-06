"""Metrics collector module."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import cache
import importlib
import inspect
import pkgutil

import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CollectorInfo:
    """Metadata describing a collector."""

    type: str
    name: str
    description: str


class Collector(ABC):
    """Abstract base class for metrics collectors."""

    def __init__(self, config: dict | None = None):
        """Initialize metrics collector."""
        self.config = config or {}

    @classmethod
    @abstractmethod
    def get_info(cls) -> CollectorInfo:
        """Return collector information."""

    @abstractmethod
    def read_metrics(self) -> dict:
        """Read current metrics.

        Returns:
            Dictionary containing metric readings.
        """

    def postprocess(self, data: list[dict]):
        """Postprocess collected metrics data.

        Args:
            metrics: Collected metrics data.
        """
        pass


@cache
def get_collectors() -> dict[str, Collector]:
    """Return dictionary of available collectors."""
    collectors = {}

    for _, name, _ in pkgutil.iter_modules([__path__[0]]):
        module = importlib.import_module(f".{name}", f"{Collector.__module__}")
        for name, cls in inspect.getmembers(module, inspect.isclass):
            if issubclass(cls, Collector) and cls is not Collector:
                if not cls.__abstractmethods__:
                    type = cls.get_info().type
                    collectors[type] = cls
                else:
                    logger.debug(f"{cls} has abstract methods, skipping")

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
