"""Battery metrics collector module."""

import logging

import psutil

from . import CollectorMetadata, SystemCollector

logger = logging.getLogger(__name__)


class BatteryMetricsCollector(SystemCollector):
    """Collector for battery metrics."""

    @classmethod
    def get_metadata(cls) -> CollectorMetadata:
        """Return metadata describing the collector."""
        return CollectorMetadata(
            code="battery",
            name="Battery Metrics Collector",
            description="System-wide battery metrics.",
        )

    def _collect(self) -> dict:
        """Collect a data sample.

        Returns:
            Collected data sample.
        """
        return psutil.sensors_battery()

    def _process(self, sample) -> dict:
        """Process a collected data sample.

        Args:
            sample: Collected data sample.

        Returns:
            Processed data sample.
        """
        return {} if not sample else {
            "battery_percent": sample.percent,
            "battery_power_plugged": sample.power_plugged,
        }
