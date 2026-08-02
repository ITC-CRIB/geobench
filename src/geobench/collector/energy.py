"""Energy system collector module."""

import logging

from . import CollectorMetadata, SystemCollector
from .powermetrics import PowermetricsCollector
from .rapl import RAPLCollector

logger = logging.getLogger(__name__)


class EnergyCollector(SystemCollector):
    """Collector for system energy metrics."""

    @classmethod
    def get_metadata(cls) -> CollectorMetadata:
        """Return metadata describing the collector."""
        return CollectorMetadata(
            code="energy",
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
            logger.debug("RAPL energy collector not found")

        # Check if powermetrics collector is available
        try:
            self.collector = PowermetricsCollector(config)
            return

        except Exception:
            logger.debug("Powermetric energy collector not found")

        raise RuntimeError("No suitable energy metrics collector found")

    def _collect(self) -> dict:
        """Collect current data.

        Returns:
            Dictionary containing collected data sample.
        """
        return self.collector._collect()

    def _process(self, item: dict) -> dict:
        """Process collected data sample.

        Args:
            data: Collected data sample.

        Returns:
            Dictionary containing processed data sample.
        """
        return self.collector._process(item)

    def _postprocess(self, data: list[dict]):
        """Postprocess data series of processed samples.

        Args:
            data: Data series to postprocess.
        """
        self.collector._postprocess(data)
