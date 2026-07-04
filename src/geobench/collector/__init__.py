"""Metrics collector module."""

from abc import ABC, abstractmethod


class Collector(ABC):
    """Abstract base class for metrics collectors."""

    def __init__(self, config: dict | None = None):
        """Initialize metrics collector."""
        self.config = config or {}

    @abstractmethod
    def read_metrics(self) -> dict:
        """Read current metrics.

        Returns:
            Dictionary containing metric readings.
        """
