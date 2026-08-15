"""System information collector module."""

import platform

import psutil

from . import CollectorMetadata, SystemCollector


class SystemInfoCollector(SystemCollector):
    """Collector for system information."""

    @classmethod
    def get_metadata(cls) -> CollectorMetadata:
        """Return metadata describing the collector."""
        return CollectorMetadata(
            code="system_info",
            name="System Information Collector",
            description="Collects OS, CPU, memory, disk, and network information.",
        )

    def _collect(self) -> dict:
        """Collect a data sample.

        Returns:
            Collected data sample.
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

    def _process(self, sample: dict) -> dict:
        """Process a collected data sample.

        Args:
            sample: Collected data sample.

        Returns:
            Processed data sample.
        """
        return {
            "machine_type": sample["machine_type"],
            "machine_processor": sample["machine_processor"],
            "machine_name": sample["machine_name"],
            "system_name": sample["system_name"],
            "system_release": sample["system_release"],
            "system_version": sample["system_version"],
            "cpu_count_physical": sample["cpu_count_physical"],
            "cpu_count_logical": sample["cpu_count_logical"],
            "cpu_freqs_min": [val.min for val in sample["cpu_freqs"]],
            "cpu_freqs_max": [val.max for val in sample["cpu_freqs"]],
            "memory_virtual": sample["memory_virtual"],
            "memory_swap": sample["memory_swap"],
            "network": {
                name: [item._asdict() for item in info]
                for name, info in sample["network"].items()
            },
            "disk": [
                partition._asdict() | {"size": size} if size is not None else {}
                for partition, size in sample["disk"]
            ],
        }
