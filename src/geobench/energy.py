"""Energy monitoring module with support for multiple energy sensors."""

from typing import Optional, Dict, List
import glob
import os
import platform
import shutil
import subprocess
import time

from .metrics import MetricsReader

import logging

logger = logging.getLogger(__name__)


class RAPLReader(MetricsReader):
    """Reader for RAPL energy metrics."""

    def __init__(self):
        """Initialize RAPL reader."""
        super().__init__()
        self.domains = {}
        self.previous_readings = {}  # Store previous energy readings with timestamps
        self._init_energy_reading()

    @staticmethod
    def is_available() -> bool:
        """Check if RAPL is available on the current system.

        Returns:
            True if RAPL interface is available, False otherwise.
        """
        if platform.system() != "Linux":
            return False

        rapl_base = "/sys/class/powercap/intel-rapl"
        if not os.path.exists(rapl_base):
            return False

        # Check if we can find at least one valid RAPL domain
        all_paths = []
        all_paths.extend(glob.glob(f"{rapl_base}/intel-rapl:*"))
        all_paths.extend(glob.glob(f"{rapl_base}/intel-rapl:*/intel-rapl:*"))

        for domain_path in all_paths:
            energy_file = os.path.join(domain_path, "energy_uj")
            if os.path.exists(energy_file):
                try:
                    with open(energy_file, "r") as f:
                        f.read()
                    return True
                except (IOError, PermissionError):
                    continue

        return False

    def _init_energy_reading(self):
        """Initialize RAPL interface based on the operating system."""
        system = platform.system()

        if system == "Linux":
            self._init_linux_rapl()
        else:
            logger.warning("RAPL is not supported on %s", system)

    def _init_linux_rapl(self):
        """Initialize RAPL for Linux systems via sysfs."""
        rapl_base = "/sys/class/powercap/intel-rapl"

        if not os.path.exists(rapl_base):
            logger.warning("RAPL interface not found at /sys/class/powercap/intel-rapl")
            return

        # Find all RAPL domains (including subdomains like DRAM, CPU cores)
        # Pattern matches both intel-rapl:X and intel-rapl:X:Y
        all_paths = []
        all_paths.extend(glob.glob(f"{rapl_base}/intel-rapl:*"))
        all_paths.extend(glob.glob(f"{rapl_base}/intel-rapl:*/intel-rapl:*"))

        for domain_path in all_paths:
            try:
                # Read domain name
                name_file = os.path.join(domain_path, "name")
                if not os.path.exists(name_file):
                    continue

                with open(name_file, "r") as f:
                    domain_name = f.read().strip()

                # Get energy file path
                energy_file = os.path.join(domain_path, "energy_uj")
                max_energy_file = os.path.join(domain_path, "max_energy_range_uj")

                if not os.path.exists(energy_file):
                    continue

                # Read max energy range if available
                max_energy = None
                if os.path.exists(max_energy_file):
                    try:
                        with open(max_energy_file, "r") as f:
                            max_energy = int(f.read().strip())
                    except (IOError, ValueError):
                        pass

                domain_id = os.path.basename(domain_path)
                self.domains[domain_id] = {
                    "name": domain_name,
                    "energy_file": energy_file,
                    "max_energy": max_energy,
                }

                logger.info("Found RAPL domain: %s (%s)", domain_name, domain_id)

            except (IOError, PermissionError) as err:
                logger.warning("Cannot access RAPL domain %s: %s", domain_path, err)
                continue

        if self.domains:
            self.available = True
            logger.info("RAPL initialized with %d domains", len(self.domains))

            # Store initial energy readings for power calculation
            self._store_initial_readings()
        else:
            logger.warning("No RAPL domains found")

    def _store_initial_readings(self):
        """Store initial energy readings with timestamp for power calculation."""
        timestamp = time.time()

        for domain_id, domain_info in self.domains.items():
            try:
                with open(domain_info["energy_file"], "r") as f:
                    energy_uj = int(f.read().strip())
                    domain_name = domain_info["name"]

                    # Store as flat dictionary: {domain_name: (energy_uj, timestamp)}
                    self.previous_readings[domain_name] = (energy_uj, timestamp)
            except (IOError, ValueError) as err:
                logger.warning(
                    "Failed to read initial energy from %s: %s", domain_id, err
                )
                continue

    def read_metrics(self) -> Optional[Dict]:
        """Read current energy counters from all RAPL domains and calculate power.

        Returns:
            Dictionary containing:
            - 'energy': mapping domain names to energy values in microjoules (μJ)
            - 'power': mapping domain names to power values in watts (W)
            or None if RAPL is not available.
        """
        if not self.available:
            return None

        current_timestamp = time.time()
        energy_readings = {}
        power_readings = {}

        for domain_id, domain_info in self.domains.items():
            try:
                with open(domain_info["energy_file"], "r") as f:
                    current_energy_uj = int(f.read().strip())
                    domain_name = domain_info["name"]
                    energy_readings[domain_name] = current_energy_uj

                    # Calculate power if we have a previous reading
                    if domain_name in self.previous_readings:
                        prev_energy, prev_timestamp = self.previous_readings[
                            domain_name
                        ]

                        time_delta = current_timestamp - prev_timestamp

                        if time_delta > 0:
                            # Handle counter wraparound
                            max_energy = domain_info.get("max_energy")
                            if max_energy and current_energy_uj < prev_energy:
                                # Counter wrapped around
                                energy_delta = (
                                    max_energy - prev_energy
                                ) + current_energy_uj
                                logger.debug(
                                    "Counter wraparound detected for %s", domain_name
                                )
                            else:
                                energy_delta = current_energy_uj - prev_energy

                            # Convert from μJ to J and calculate power in watts
                            energy_joules = energy_delta / 1_000_000
                            power_watts = energy_joules / time_delta
                            power_readings[domain_name] = power_watts

                    # Update previous reading for next calculation
                    self.previous_readings[domain_name] = (
                        current_energy_uj,
                        current_timestamp,
                    )

            except (IOError, ValueError) as err:
                logger.warning("Failed to read energy from %s: %s", domain_id, err)
                continue

        result = {}
        if energy_readings:
            result["rapl_energy"] = energy_readings
        if power_readings:
            result["rapl_power"] = power_readings

        return result if result else None


class PowerMetricsReader(MetricsReader):
    """Reader for macOS powermetrics energy metrics."""

    def __init__(self):
        """Initialize PowerMetrics reader."""
        super().__init__()
        self.last_reading = None
        self._init_energy_reading()

    @staticmethod
    def is_available() -> bool:
        """Check if powermetrics is available on the current system.

        Returns:
            True if powermetrics is available, False otherwise.
        """
        if platform.system() != "Darwin":
            return False

        # Check if powermetrics command exists
        if shutil.which("powermetrics") is None:
            return False

        # Try to run powermetrics to see if we have permissions
        try:
            result = subprocess.run(
                ["powermetrics", "--help"], capture_output=True, timeout=5, check=False
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _init_energy_reading(self):
        """Initialize powermetrics interface."""
        if not shutil.which("powermetrics"):
            logger.warning("powermetrics command not found")
            return

        # Test if we can run powermetrics
        try:
            result = subprocess.run(
                ["powermetrics", "--help"], capture_output=True, timeout=5, check=False
            )
            if result.returncode == 0:
                self.available = True
                logger.info("PowerMetrics initialized successfully")
            else:
                logger.warning("powermetrics is not accessible (may need sudo)")
        except (subprocess.TimeoutExpired, FileNotFoundError) as err:
            logger.warning("Failed to initialize powermetrics: %s", err)

    def read_metrics(self) -> Optional[Dict]:
        """Read current energy metrics using powermetrics.

        Returns:
            Dictionary containing energy readings in microjoules (μJ),
            or None if powermetrics is not available.
        """
        if not self.available:
            return None

        try:
            # Run powermetrics for a short sample
            # Note: This requires sudo privileges
            result = subprocess.run(
                ["powermetrics", "-n", "1", "-i", "100", "--samplers", "tasks"],
                capture_output=True,
                timeout=5,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                logger.warning("powermetrics failed: %s", result.stderr)
                return None

            # Parse the output to extract energy metrics
            energy_readings = self._parse_powermetrics_output(result.stdout)

            if energy_readings:
                self.last_reading = energy_readings
                return {"energy": energy_readings}
            else:
                return None

        except (subprocess.TimeoutExpired, FileNotFoundError) as err:
            logger.warning("Failed to read energy from powermetrics: %s", err)
            return None

    def _parse_powermetrics_output(self, output: str) -> Dict[str, int]:
        """Parse powermetrics output to extract energy metrics.

        Args:
            output: Raw output from powermetrics command.

        Returns:
            Dictionary mapping metric names to energy values in microjoules.
        """
        energy_readings = {}

        # Parse CPU energy
        for line in output.split("\n"):
            line = line.strip()

            # Look for energy-related metrics
            if "CPU Power" in line or "GPU Power" in line or "ANE Power" in line:
                parts = line.split(":")
                if len(parts) >= 2:
                    name = parts[0].strip()
                    value_str = parts[1].strip().split()[0]  # Get first token (number)
                    try:
                        # Convert to microjoules (assuming powermetrics reports in mW)
                        # This is a simplified parsing - real implementation may need more robust parsing
                        value = float(value_str)
                        # Convert mW to microjoules (mW * 1000 = μW, for 100ms sample)
                        energy_uj = int(value * 100)  # 100ms sample period
                        energy_readings[name] = energy_uj
                    except (ValueError, IndexError):
                        continue

        return energy_readings


def get_energy_reader() -> List[MetricsReader]:
    """Factory function to get the appropriate energy readers for the current system.

    This function detects the operating system and available energy monitoring
    sensors, then returns a list of appropriate energy reader instances.
    The list can contain both external readers (HTTP API for external power meters)
    and internal readers (RAPL, PowerMetrics for system-level energy monitoring).

    Priority order for internal readers:
    1. RAPL (Linux with Intel CPUs)
    2. PowerMetrics (macOS)

    Returns:
        List[MetricsReader]: List of energy reader instances.
    """
    system = platform.system()
    logger.info("Detecting energy readers for %s", system)

    readers = []

    if RAPLReader.is_available():
        logger.info("Adding RAPL energy reader")
        readers.append(RAPLReader())

    elif PowerMetricsReader.is_available():
        logger.info("Adding PowerMetrics energy reader")
        readers.append(PowerMetricsReader())

    return readers
