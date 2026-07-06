"""RAPL collector module."""

import glob
import os

from . import Collector, CollectorInfo

import logging

logger = logging.getLogger(__name__)


class RAPLCollector(Collector):
    """Collector for RAPL energy metrics."""

    @classmethod
    def get_info(cls) -> CollectorInfo:
        """Return collector information."""
        return CollectorInfo(
            type="rapl",
            name="RAPL Energy Metrics Collector",
            description="Energy metrics using RAPL.",
        )

    def __init__(self, config: dict | None = None):
        """Initialize RAPL collector."""
        super().__init__(config)

        self.domains = {}

        rapl_base = "/sys/class/powercap/intel-rapl"
        if not os.path.exists(rapl_base):
            raise RuntimeError(f"RAPL interface not found at {rapl_base}")

        # Check if we can find at least one valid RAPL domain
        paths = []
        paths.extend(glob.glob(f"{rapl_base}/intel-rapl:*"))
        paths.extend(glob.glob(f"{rapl_base}/intel-rapl:*/intel-rapl:*"))

        for path in paths:
            try:
                id = os.path.basename(path)
                domain = {}

                filename = os.path.join(path, "name")
                if not os.path.exists(filename):
                    continue
                with open(filename, "r") as file:
                    domain["name"] = file.read().strip()

                filename = os.path.join(path, "max_energy_range_uj")
                if os.path.exists(filename):
                    try:
                        with open(filename, "r") as file:
                            domain["max_energy"] = int(file.read().strip())
                    except (IOError, ValueError):
                        pass

                domain["energy_file"] = os.path.join(path, "energy_uj")

                self.domains[id] = domain
                logger.debug("Found RAPL domain: %s, %s", id, domain["name"])

            except (IOError, PermissionError) as err:
                logger.warning("Cannot access RAPL domain %s: %s", path, err)
                continue

        if not self.domains:
            raise RuntimeError("No RAPL domain found")

    def read_metrics(self) -> dict:
        """Read current energy counters from all RAPL domains.

        Returns:
            Dictionary containing `energy` with mapping domain names to energy
            values in microjoules (μJ).
        """
        out = {
            "energy": {},
        }

        for id, domain in self.domains.items():
            try:
                with open(domain["energy_file"], "r") as file:
                    energy_uj = int(file.read().strip())
                    out["energy"][id] = energy_uj

            except (IOError, ValueError) as err:
                logger.warning("Failed to read energy from %s: %s", id, err)
                continue

        return out

    def postprocess(self, data: list[dict]):
        """Postprocess collected metrics data.

        Args:
            metrics: Collected metrics data.
        """
        super().postprocess(data)

        prev_item = None

        for item in data:
            if prev_item:
                item["power"] = {}
                d_time = item["timestamp"] - prev_item["timestamp"]
                if d_time < 0:
                    continue
                for id, domain in self.domains.items():
                    d_energy = item["energy"][id] - prev_item["energy"][id]
                    max_energy = domain.get("max_energy")
                    if max_energy and d_energy < 0:
                        d_energy += max_energy
                        logger.debug("Counter wraparound detected for %s", id)

                    power_watts = d_energy / 1_000_000 / d_time
                    item["power"][id] = power_watts

            prev_item = item
