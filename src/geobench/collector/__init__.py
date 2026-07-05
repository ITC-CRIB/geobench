"""Metrics collector module."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class CollectorInfo:
    """Metadata describing a collector."""

    code: str
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
