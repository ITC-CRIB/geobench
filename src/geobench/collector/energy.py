"""Energy collector module."""

from . import Collector, CollectorInfo
from .powermetrics import PowermetricsCollector
from .rapl import RAPLCollector

import logging

logger = logging.getLogger(__name__)


class EnergyCollector(Collector):
    """Collector for energy metrics."""

    @classmethod
    def get_info(cls) -> CollectorInfo:
        """Return collector information."""
        return CollectorInfo(
            type="energy",
            name="Energy Metrics Collector",
            description="Energy consumption metrics using RAPL or powermetrics.",
        )

    def __init__(self, config: dict | None = None):
        """Initialize energy metrics collector.

        Raises:
            RuntimeError: If no suitable energy metrics collector found.
        """
        super().__init__(config)

        # Check if RAPL collector is available
        try:
            self.collector = RAPLCollector(config)
            return

        except Exception:
            pass

        # Check if powermetrics collector is available
        try:
            self.collector = PowermetricsCollector(config)
            return

        except Exception:
            pass

        raise RuntimeError("No suitable energy metrics collector found")

    def read_metrics(self) -> dict:
        """Read energy consumption metrics.

        Returns:
            Dictionary containing energy consumption metrics.
        """
        out = self.collector.read_metrics()
        return out
