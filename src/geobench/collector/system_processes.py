"""System processes collector module."""

import psutil

from . import CollectorInfo, SystemCollector


class SystemProcessesCollector(SystemCollector):
    """Collector for process metrics for all processes system-wide."""

    def get_info() -> CollectorInfo:
        """Return collector information."""
        return CollectorInfo(
            code="system_processes",
            name="System Processes Collector",
            description="Collector for process metrics for all processes system-wide.",
        )

    def __init__(self, config: dict | None = None):
        attrs = [
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
        self.attrs = []
        process = psutil.Process()
        for name in attrs:
            if getattr(process, name, None):
                self.attrs.append(name)

    def collect(self) -> dict:
        """Collect system processes metrics.

        Returns:
            Dictionary containing system processes metrics.
        """
        out = {
            "processes": {
                process.pid: process.info for process in psutil.process_iter(self.attrs)
            }
        }

        return out

    def postprocess(self, data: list[dict]):
        """Postprocess collected data.

        Args:
            data: Collected data.
        """
        for item in data:
            for id, info in item["processes"].items():
                item["processes"][id] = {
                    "id": info["pid"],
                    "parent_id": info["ppid"],
                    "name": info["name"],
                    "create_time": info["create_time"],
                    "username": info["username"],
                    "status": info["status"],
                    "command": {
                        "executable": info["exe"],
                    },
                    "cpu": {
                        "user_time": info["cpu_times"].user,
                        "system_time": info["cpu_times"].system,
                        "num": info.get("cpu_num"),
                    },
                    "memory": {
                        "rss": info["memory_info"].rss,
                        "vms": info["memory_info"].vms,
                    },
                    "io": {
                        "read_bytes": info["io_counters"].read_bytes,
                        "write_bytes": info["io_counters"].write_bytes,
                        "other_bytes": getattr(info["io_counters"], "other_bytes"),
                    }
                    if info["io_counters"]
                    else {},
                    "resources": {
                        "num_threads": info["num_threads"],
                        "num_handles": info.get("num_handles"),
                        "num_fds": info.get("num_fds"),
                    },
                }

        super().postprocess(data)
