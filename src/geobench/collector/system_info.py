"""System information collector module."""

import platform

import psutil

from . import CollectorInfo, SystemCollector


class SystemInfoCollector(SystemCollector):
    """Collector for system information."""

    @classmethod
    def get_info(cls) -> CollectorInfo:
        """Return collector information."""
        return CollectorInfo(
            code="system_info",
            name="System Information Collector",
            description="Collects OS, CPU, memory, disk, and network information.",
        )

    def collect(self) -> dict:
        """Collect system information.

        Returns:
            Dictionary containing system information.
        """
        out = {}

        # OS information
        out["os"] = {
            "machine": platform.machine(),
            "processor": platform.processor(),
            "node": platform.node(),
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
        }

        # CPU information
        out["cpu"] = {
            "physical_count": psutil.cpu_count(logical=False),
            "logical_count": psutil.cpu_count(logical=True),
            "frequency": [
                {"min": freq.min, "max": freq.max}
                for freq in psutil.cpu_freq(percpu=True)
            ],
        }

        # Memory information
        out["memory"] = psutil.virtual_memory().total
        out["swap"] = psutil.swap_memory().total

        # Disk information
        out["disk"] = []
        for partition in psutil.disk_partitions():
            info = partition._asdict()
            try:
                info["size"] = psutil.disk_usage(partition.mountpoint).total

            except PermissionError:
                pass

            out["disk"].append(info)

        # Network information
        out["network"] = {
            name: [
                {key: val for key, val in item._asdict().items() if val is not None}
                for item in info
            ]
            for name, info in psutil.net_if_addrs().items()
        }

        return out
