"""Process metrics collector module."""

import psutil

from . import CollectorInfo, Process, ProcessCollector


class ProcessMetricsCollector(ProcessCollector):
    """Collector for process metrics."""

    @classmethod
    def get_info(cls) -> CollectorInfo:
        """Return collector information."""
        return CollectorInfo(
            code="process_metrics",
            name="Process Metrics Collector",
            description="Process-specific CPU, memory, and IO metrics.",
        )

    @classmethod
    def get_attrs(cls, attrs: list[str]) -> list[str]:
        """Return supported attributes from the given attributes list."""
        process = psutil.Process()
        return [name for name in attrs if getattr(process, name, None)]

    @classmethod
    def get_default_attrs(cls) -> list[str]:
        return [
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
        ]

    @classmethod
    def process_info(cls, info: dict):
        """Standardize process information.
        
        Process information attributes:
            - io:read_chars = Data requested from OS.
            - io:read_bytes = Data actually read from storage.
            - io:write_chars = Data handed to OS.
            - io:write_bytes = Data actually written to storage.

        Args:
            info: Process information.
        """
        cpu_times = info.pop("cpu_times", {})
        memory_info = info.pop("memory_info", {})
        io_counters = info.pop("io_counters", {})
        info.update(
            {
                "parent_id": info.pop("ppid", None),
                "command": {
                    "cmdline": info.pop("cmdline", None),
                    "executable": info.pop("exe", None),
                    "environment": info.pop("environ", None),
                },
                "cpu": {
                    "affinity": info.pop("cpu_affinity", None),
                    "num": info.pop("cpu_num", None),
                    "user_time": getattr(cpu_times, "user", None),
                    "system_time": getattr(cpu_times, "system", None),
                    "num_ctx_switches": info.pop("num_ctx_switches", None),
                },
                "memory": {
                    "rss": getattr(memory_info, "rss", None),
                    "vms": getattr(memory_info, "vms", None),
                },
                "io": {
                    "read_bytes": getattr(io_counters, "read_bytes", None),
                    "read_chars": getattr(io_counters, "read_chars", None),
                    "write_bytes": getattr(io_counters, "write_bytes", None),
                    "write_chars": getattr(io_counters, "write_chars", None),
                    "other_bytes": getattr(io_counters, "other_bytes", None),
                },
                "resources": {
                    "num_threads": info.pop("num_threads", None),
                    "num_handles": info.pop("num_handles", None),
                    "num_fds": info.pop("num_fds", None),
                },
                "threads": [item._as_dict() for item in info.get("threads", [])],
            }
        )

    def __init__(self, process: Process, config: dict | None = None):
        """Initialize process metrics collector."""
        super().__init__(process, config)

        self.attrs = self.get_attrs(self.config.get("attrs", self.get_default_attrs()))

    def collect(self) -> dict:
        """Collect process metrics.

        Returns:
            Dictionary containing process metrics.
        """
        return self.process.as_dict(self.attrs)

    def process_item(self, item: dict):
        """Process collected data item.

        Args:
            item: Data item to be processed.
        """
        ProcessMetricsCollector.process_info(item)

        super().process_item(item)
