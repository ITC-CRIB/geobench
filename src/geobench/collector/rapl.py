"""RAPL collector module."""

import glob
import os
import time

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
        self.previous_readings = None

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
        """Read current energy counters from all RAPL domains and calculate power.

        Returns:
            Dictionary containing:
            - 'energy': mapping domain names to energy values in microjoules (μJ)
            - 'power': mapping domain names to power values in watts (W)
        """
        if not self.previous_readings:
            timestamp = time.time()
            for id, domain in self.domains.items():
                try:
                    with open(domain["energy_file"], "r") as file:
                        self.previous_readings[id] = (
                            int(file.read().strip()),
                            timestamp,
                        )

                except (IOError, ValueError) as err:
                    logger.warning("Failed to read initial energy from %s: %s", id, err)
                    continue

        timestamp = time.time()
        energy_data = {}
        power_data = {}

        for id, domain in self.domains.items():
            try:
                with open(domain["energy_file"], "r") as file:
                    energy_uj = int(file.read().strip())
                    energy_data[id] = energy_uj

                    # Calculate power if we have a previous reading
                    if id in self.previous_readings:
                        prev_energy_uj, prev_timestamp = self.previous_readings[id]

                        time_delta = timestamp - prev_timestamp
                        if time_delta > 0:
                            # Handle counter wraparound
                            max_energy = domain.get("max_energy")
                            if max_energy and energy_uj < prev_energy_uj:
                                # Counter wrapped around
                                d_energy = max_energy - prev_energy_uj + energy_uj
                                logger.debug("Counter wraparound detected for %s", id)
                            else:
                                d_energy = energy_uj - prev_energy_uj

                            # Convert from μJ to J and calculate power in watts
                            power_watts = d_energy / 1_000_000 / time_delta
                            power_data[id] = power_watts

                    # Update previous reading for next calculation
                    self.previous_readings[id] = (
                        energy_uj,
                        timestamp,
                    )

            except (IOError, ValueError) as err:
                logger.warning("Failed to read energy from %s: %s", id, err)
                continue

        out = {}
        if energy_data:
            out["rapl_energy"] = energy_data
        if power_data:
            out["rapl_power"] = power_data

        return out
