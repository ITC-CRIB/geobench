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
        out = {
            # Machine information
            "machine_type": platform.machine(),
            "machine_processor": platform.processor(),
            "machine_name": platform.node(),
            # OS information
            "system_name": platform.system(),
            "system_release": platform.release(),
            "system_version": platform.version(),
            # CPU information
            "cpu_count_physical": psutil.cpu_count(logical=False),
            "cpu_count_logical": psutil.cpu_count(logical=True),
            "cpu_freqs": psutil.cpu_freq(percpu=True),
            # Memory information
            "memory_virtual": psutil.virtual_memory().total,
            "memory_swap": psutil.swap_memory().total,
            # Network
            "network": psutil.net_if_addrs(),
        }

        # Disk information
        out["disk"] = []
        for partition in psutil.disk_partitions():
            try:
                size = psutil.disk_usage(partition.mountpoint).total
            except PermissionError:
                size = None
            out["disk"].append((partition, size))

        return out

    def process_item(self, item: dict):
        """Process collected data item.

        Args:
            item: Data item to be processed.
        """
        item["cpu_freqs"] = [
            {"min": freq.min, "max": freq.max} for freq in item["cpu_freqs"]
        ]
        item["disk"] = [
            partition._asdict() | {"size": size} if size is not None else {}
            for partition, size in item["disk"]
        ]
        item["network"] = {
            name: [item._asdict() for item in info]
            for name, info in item["network"].items()
        }

        super().process_item(item)
