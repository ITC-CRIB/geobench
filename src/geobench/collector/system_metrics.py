"""System metrics collector module."""

import psutil

from . import CollectorInfo, SystemCollector

import logging

logger = logging.getLogger(__name__)


class SystemMetricsCollector(SystemCollector):
    """Collector for system metrics."""

    @classmethod
    def get_info(cls) -> CollectorInfo:
        """Return collector information."""
        return CollectorInfo(
            code="system_metrics",
            name="System Metrics Collector",
            description="System-wide CPU, memory, IO, and network metrics.",
        )

    def collect(self) -> dict:
        """Collect system metrics.

        Returns:
            Dictionary containing system metrics.
        """
        return {
            "cpu_times": psutil.cpu_times(percpu=True),
            "cpu_freqs": psutil.cpu_freq(percpu=True),
            "memory_virtual": psutil.virtual_memory(),
            "memory_swap": psutil.swap_memory(),
            "network": psutil.net_io_counters(),
            "disk": psutil.disk_io_counters(),
        }

    def process_item(self, item: dict):
        """Process collected data item.

        Args:
            item: Data item to be processed.
        """
        item["cpu_times"] = [
            {"user": item.user, "system": item.system, "idle": item.idle}
            for item in item["cpu_times"]
        ]
        item["cpu_freqs"] = [val._asdict() for val in item["cpu_freqs"]],
        
        virtual = item.pop("memory_virtual")
        item["memory_virtual_used"] = virtual.used
        item["memory_virtual_free"] = virtual.free

        swap = item.pop("memory_swap")
        item["memory_swap_used"] = swap.used
        item["memory_swap_free"] = swap.free

        network = item.pop("network")
        item["network_sent"] = network.bytes_sent
        item["network_received"] = network.bytes_recv

        disk = item.pop("disk")
        item["disk_read"] = getattr(disk, "read_bytes", None)
        item["disk_write"] = getattr(disk, "write_bytes", None)

        super().process_item(item)

    def process_data(self, data: list[dict]) -> dict:
        super().process_data(data)

        return self.reduce(
            data,
            {
                "timestamp": "pair",
                "cpu_times:user": "diff",
                "cpu_times:system": "diff",
                "cpu_times:idle": "diff",
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
