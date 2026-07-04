"""Metrics collector module."""

from abc import ABC, abstractmethod


class Collector(ABC):
    """Abstract base class for metrics collectors."""

    def __init__(self):
        """Initialize metrics collector."""
        self.available = False

    @abstractmethod
    def read_metrics(self) -> dict | None:
        """Read current metrics.

        Returns:
            Dictionary containing metric readings, or None if not available.
        """

    @staticmethod
    @abstractmethod
    def is_available() -> bool:
        """Check if this metrics collector is available on the current system.

        Returns:
            True if the metrics collector can be used, False otherwise.
        """
