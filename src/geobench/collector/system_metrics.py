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
            # CPU information
            out["cpu"] = {
                "times": psutil.cpu_times(percpu=True),
                "freqs": psutil.cpu_freq(percpu=True),
            }

            # Memory information
            out["memory"] = {
                "virtual": psutil.virtual_memory(),
                "swap": psutil.swap_memory(),
            }

            # Network information
            net_io = psutil.net_io_counters()
            out["net"] = {
                "sent": net_io.bytes_sent,
                "received": net_io.bytes_recv,
            }

            # Disk information
            disk_io = psutil.disk_io_counters()
            if disk_io:
                out["disk"] = {
                    "read": disk_io.read_bytes,
                    "write": disk_io.write_bytes,
                }

        except Exception as err:
            logger.error("Error reading psutil metrics: %s", err)
            out = {"error": str(err)}

        return out

    def process_item(self, item: dict):
        """Process collected data item.

        Args:
            item: Data item to be processed.
        """
        item["cpu"] = {
            "times": [
                {"user": item.user, "system": item.system, "idle": item.idle}
                for item in item["cpu"]["times"]
            ],
            "freqs": [val._asdict() for val in item["cpu"]["freqs"]],
        }
        item["memory"] = {
            "virtual": {
                "used": item["memory"]["virtual"].used,
                "free": item["memory"]["virtual"].free,
            },
            "swap": {
                "used": item["memory"]["swap"].used,
                "free": item["memory"]["swap"].free,
            },
        }

        super().process_item(item)
