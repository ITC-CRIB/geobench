"""Process metrics collector module."""

import psutil

from . import CollectorMetadata, Process, ProcessCollector


class ProcessMetricsCollector(ProcessCollector):
    """Collector for process metrics."""

    @classmethod
    def get_metadata(cls) -> CollectorMetadata:
        """Return metadata describing the collector."""
        return CollectorMetadata(
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
    def process_info(cls, info: dict) -> dict:
        """Standardize a process information.

        Process information attributes:
            - io:read_chars = Data requested from OS.
            - io:read_bytes = Data actually read from storage.
            - io:write_chars = Data handed to OS.
            - io:write_bytes = Data actually written to storage.

        Args:
            info: Process information.

        Returns:
            Standardized process information.
        """
        cpu_times = info.get("cpu_times", {})
        memory_info = info.get("memory_info", {})
        io_counters = info.get("io_counters", {})
        return {
            "pid": info.get("pid"),
            "parent_pid": info.get("ppid"),
            "create_time": info.get("create_time"),
            "name": info.get("name"),
            "username": info.get("username"),
            "status": info.get("status"),
            "executable": info.get("exe"),
            "environment": info.get("environ"),
            "cpu_time_user": getattr(cpu_times, "user", None),
            "cpu_time_system": getattr(cpu_times, "system", None),
            "cpu_num": info.get("cpu_num"),
            "cpu_num_ctx_switches": info.get("num_ctx_switches"),
            "memory_rss": getattr(memory_info, "rss", None),
            "memory_vms": getattr(memory_info, "vms", None),
            "io_read_bytes": getattr(io_counters, "read_bytes", None),
            "io_read_chars": getattr(io_counters, "read_chars", None),
            "io_write_bytes": getattr(io_counters, "write_bytes", None),
            "io_write_chars": getattr(io_counters, "write_chars", None),
            "io_other_bytes": getattr(io_counters, "other_bytes", None),
            "num_fds": info.get("num_fds"),
            "num_handles": info.get("num_handles"),
            "num_threads": info.get("num_threads"),
            "threads": [item._as_dict() for item in info.get("threads", [])],
        }

    def __init__(self, process: Process, config: dict | None = None):
        """Initialize the process metrics collector.

        Args:
            process: Related process.
            config: Optional collector configuration.
        """
        super().__init__(process, config)

        self.attrs = self.get_attrs(self.config.get("attrs", self.get_default_attrs()))

    def _collect(self) -> dict:
        """Collect a data sample.

        Returns:
            Collected data sample.
        """
        sample = {self.process.pid: self.process.as_dict(self.attrs)}

        for process in self.process.children(recursive=True):
            try:
                sample[process.pid] = process.as_dict(self.attrs, ad_value=None)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return sample

    def _process(self, sample: dict) -> dict:
        """Process a collected data sample.

        Args:
            sample: Collected data sample.

        Returns:
            Processed data sample.
        """
        return {key: self.process_info(val) for key, val in sorted(sample.items())}
