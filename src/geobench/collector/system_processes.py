"""System processes collector module."""

import psutil

from . import CollectorMetadata, SystemCollector
from .process_metrics import ProcessMetricsCollector


class SystemProcessesCollector(SystemCollector):
    """Collector for process metrics for all processes system-wide."""

    def get_metadata() -> CollectorMetadata:
        """Return metadata describing the collector."""
        return CollectorMetadata(
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

    def _collect(self) -> dict:
        """Collect current data.

        Returns:
            Dictionary containing collected data sample.
        """
        return {
            "processes": {
                process.pid: process.info for process in psutil.process_iter(self.attrs)
            }
        }

    def _process(self, sample: dict) -> dict:
        """Process collected data sample.

        Args:
            data: Collected data sample.

        Returns:
            Dictionary containing processed data sample.
        """
        return {
            "processes": {
                pid: ProcessMetricsCollector.process_info(info)
                for pid, info in sample["processes"].items()
            }
        }
