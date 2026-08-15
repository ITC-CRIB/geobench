"""System metrics collector module."""

import logging

import psutil

from . import CollectorMetadata, CollectorRule, SystemCollector

logger = logging.getLogger(__name__)


class SystemMetricsCollector(SystemCollector):
    """Collector for system metrics."""

    @classmethod
    def get_metadata(cls) -> CollectorMetadata:
        """Return metadata describing the collector."""
        return CollectorMetadata(
            code="system_metrics",
            name="System Metrics Collector",
            description="System-wide CPU, memory, IO, and network metrics.",
        )

    def _collect(self) -> dict:
        """Collect a data sample.

        Returns:
            Collected data sample.
        """
        return {
            "cpu_times": psutil.cpu_times(percpu=True),
            "cpu_freqs": psutil.cpu_freq(percpu=True),
            "memory_virtual": psutil.virtual_memory(),
            "memory_swap": psutil.swap_memory(),
            "network": psutil.net_io_counters(),
            "disk": psutil.disk_io_counters(),
        }

    def _process(self, sample: dict) -> dict:
        """Process a collected data sample.

        Args:
            sample: Collected data sample.

        Returns:
            Processed data sample.
        """
        return {
            "cpu_times_user": [val.user for val in sample["cpu_times"]],
            "cpu_times_system": [val.system for val in sample["cpu_times"]],
            "cpu_times_idle": [val.idle for val in sample["cpu_times"]],
            "cpu_freqs": [val._asdict() for val in sample["cpu_freqs"]],
            "memory_virtual_used": sample["memory_virtual"].used,
            "memory_virtual_free": sample["memory_virtual"].free,
            "memory_swap_used": sample["memory_swap"].used,
            "memory_swap_free": sample["memory_swap"].free,
            "network_sent": sample["network"].bytes_sent,
            "network_received": sample["network"].bytes_recv,
            "disk_read": getattr(sample["disk"], "read_bytes", None),
            "disk_write": getattr(sample["disk"], "write_bytes", None),
        }

    def _postprocess(self, data: list[dict]) -> dict:
        """Postprocess a data series containing processed samples.

        Args:
            data: Data series containing processed samples.

        Returns:
            Reference data for the processed samples.
        """
        return CollectorRule.apply_rules(
            data,
            {
                "cpu_times_user": "diff",
                "cpu_times_system": "diff",
                "cpu_times_idle": "diff",
                "memory_virtual_used": "diff",
                "memory_virtual_free": "diff",
                "memory_swap_used": "diff",
                "memory_swap_free": "diff",
                "network_sent": "diff",
                "network_received": "diff",
                "disk_read": "diff",
                "disk_write": "diff",
            },
        )
