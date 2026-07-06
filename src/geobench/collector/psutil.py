"""psutil collector module."""

import psutil

from . import Collector, CollectorInfo

import logging

logger = logging.getLogger(__name__)


class PsutilsCollector(Collector):
    """Collector for system metrics via psutil."""

    @classmethod
    def get_info(cls) -> CollectorInfo:
        """Return collector information."""
        return CollectorInfo(
            type="psutil",
            name="psutil Collector",
            description="CPU, memory, IO, and network metrics using psutil.",
        )

    def read_metrics(self) -> dict:
        """Read system metrics using psutil.

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
        """Postprocess collected metrics data.

        Args:
            metrics: Collected metrics data.
        """
        super().postprocess(data)

        for item in data:
            item["cpu_times"] = [val._asdict() for val in item["cpu_times"]]
            item["cpu_freq"] = [val._asdict() for val in item["cpu_freq"]]
            item["memory_usage"] = item["memory_usage"]._asdict()
            item["swap_usage"] = item["swap_usage"]._asdict()
