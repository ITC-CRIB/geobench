"""System processes collector module."""

import psutil

from . import CollectorInfo, SystemCollector
from .process_metrics import ProcessMetricsCollector


class SystemProcessesCollector(SystemCollector):
    """Collector for process metrics for all processes system-wide."""

    def get_info() -> CollectorInfo:
        """Return collector information."""
        return CollectorInfo(
            code="system_processes",
            name="System Processes Collector",
            description="Process metrics for all processes system-wide.",
        )

    def __init__(self, config: dict | None = None):
        """Initialize system processes collector."""
        super().__init__(config)

        self.attrs = ProcessMetricsCollector.get_attrs(
            self.config.get(
                "attrs",
                [
                    "cpu_times",
                    "cpu_num",
                    "create_time",
                    "exe",
                    "io_counters",
                    "memory_info",
                    "name",
                    "num_fds",
                    "num_handles",
                    "num_threads",
                    "pid",
                    "ppid",
                    "status",
                    "username",
                ],
            )
        )

    def collect(self) -> dict:
        """Collect system processes metrics.

        Returns:
            Dictionary containing system processes metrics.
        """
        return {
            "processes": {
                process.pid: process.info for process in psutil.process_iter(self.attrs)
            }
        }

    def process_item(self, item: dict):
        """Process collected data item.

        Args:
            item: Data item to be processed.
        """
        for info in item["processes"]:
            ProcessMetricsCollector.process_info(info)

        super().process_item(item)
