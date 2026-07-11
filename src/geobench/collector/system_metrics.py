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
        out = {}

        try:
            # CPU metrics
            out["cpu_times"] = psutil.cpu_times(percpu=True)
            out["cpu_freq"] = psutil.cpu_freq(percpu=True)

            # Memory metrics
            out["memory_usage"] = psutil.virtual_memory()
            out["swap_usage"] = psutil.swap_memory()

            # Network I/O
            net_io = psutil.net_io_counters()
            out["net_bytes_sent"] = net_io.bytes_sent
            out["net_bytes_recv"] = net_io.bytes_recv

            # Disk I/O
            disk_io = psutil.disk_io_counters()
            if disk_io:
                out["disk_bytes_read"] = disk_io.read_bytes
                out["disk_bytes_write"] = disk_io.write_bytes

        except Exception as err:
            logger.error("Error reading psutil metrics: %s", err)
            out = {"error": str(err)}

        return out

    def postprocess(self, data: list[dict]):
        """Postprocess collected data.

        Args:
            data: Collected data.
        """
        super().postprocess(data)

        for item in data:
            item["cpu_times"] = [val._asdict() for val in item["cpu_times"]]
            item["cpu_freq"] = [val._asdict() for val in item["cpu_freq"]]
            item["memory_usage"] = item["memory_usage"]._asdict()
            item["swap_usage"] = item["swap_usage"]._asdict()
