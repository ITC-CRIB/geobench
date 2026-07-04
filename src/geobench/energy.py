"""Energy monitoring module with support for multiple energy sensors."""

import asyncio
import glob
import os
import platform
import shutil
import socket
import subprocess
import time
from typing import Optional, Dict, List

try:
    import aiohttp

    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

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
            logger.warning(f"RAPL is not supported on {system}")

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

                logger.info(f"Found RAPL domain: {domain_name} ({domain_id})")

            except (IOError, PermissionError) as e:
                logger.warning(f"Cannot access RAPL domain {domain_path}: {e}")
                continue

        if self.domains:
            self.available = True
            logger.info(f"RAPL initialized with {len(self.domains)} domains")

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
                    # logger.debug(f"Stored initial reading for {domain_name}: {energy_uj} μJ at {timestamp}")
            except (IOError, ValueError) as e:
                logger.warning(f"Failed to read initial energy from {domain_id}: {e}")
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
                                    f"Counter wraparound detected for {domain_name}"
                                )
                            else:
                                energy_delta = current_energy_uj - prev_energy

                            # Convert from μJ to J and calculate power in watts
                            energy_joules = energy_delta / 1_000_000
                            power_watts = energy_joules / time_delta
                            power_readings[domain_name] = power_watts

                            # logger.debug(
                            #     f"{domain_name}: ΔE={energy_delta}μJ, Δt={time_delta:.3f}s, P={power_watts:.3f}W"
                            # )

                    # Update previous reading for next calculation
                    self.previous_readings[domain_name] = (
                        current_energy_uj,
                        current_timestamp,
                    )

            except (IOError, ValueError) as e:
                logger.warning(f"Failed to read energy from {domain_id}: {e}")
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
        if platform.system() != "Darwin":
            logger.warning("PowerMetrics is only supported on macOS")
            return

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
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.warning(f"Failed to initialize powermetrics: {e}")

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
                logger.warning(f"powermetrics failed: {result.stderr}")
                return None

            # Parse the output to extract energy metrics
            energy_readings = self._parse_powermetrics_output(result.stdout)

            if energy_readings:
                self.last_reading = energy_readings
                return {"energy": energy_readings}
            else:
                return None

        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.warning(f"Failed to read energy from powermetrics: {e}")
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


class HTTPAPIReader(MetricsReader):
    """Reader for energy metrics from HTTP API endpoint."""

    def __init__(self, api_url: str, timeout: float = 5.0):
        """Initialize HTTP API reader.

        Args:
            api_url: Full URL to the energy API endpoint (e.g., "http://server_ip:port/device/<hostname>")
            timeout: Request timeout in seconds (default: 5.0)
        """
        super().__init__(reader_type="external")
        self.api_url = api_url
        self.timeout = timeout
        self._init_energy_reading()

    @staticmethod
    def is_available() -> bool:
        """Check if aiohttp is available.

        Returns:
            True if aiohttp is installed, False otherwise.
        """
        return AIOHTTP_AVAILABLE

    def _init_energy_reading(self):
        """Initialize HTTP API reader."""
        if not AIOHTTP_AVAILABLE:
            logger.warning(
                "aiohttp is not installed. Install it with: pip install aiohttp"
            )
            return

        # Replace <hostname> placeholder in URL if present
        if "<hostname>" in self.api_url:
            hostname = socket.gethostname()
            self.api_url = self.api_url.replace("<hostname>", hostname)
            logger.info(f"Resolved hostname in API URL to: {self.api_url}")

        self.available = True
        logger.info(f"HTTP API energy reader initialized with URL: {self.api_url}")

    def read_metrics(self) -> Optional[Dict]:
        """Read current energy metrics from HTTP API.

        Returns:
            Dictionary containing power readings in watts from the API,
            or None if the API is not available or request fails.
        """
        if not self.available:
            return None

        try:
            # Run async function in event loop
            return asyncio.run(self._fetch_energy())
        except Exception as e:
            logger.warning(f"Failed to read energy from HTTP API: {e}")
            return None

    async def _fetch_energy(self) -> Optional[Dict[str, int]]:
        """Async method to fetch energy data from HTTP API.

        Returns:
            Dictionary containing power readings, or None if request fails.
        """
        try:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(self.api_url) as response:
                    if response.status != 200:
                        logger.warning(
                            f"HTTP API returned status {response.status}: {await response.text()}"
                        )
                        return None

                    data = await response.json()

                    # The API returns power in watts
                    if "power" in data:
                        return {"smart_plug_power": data}
                    else:
                        logger.warning(f"No 'power' field in API response: {data}")
                        return None

        except aiohttp.ClientError as e:
            logger.warning(f"HTTP API request failed: {e}")
            return None
        except asyncio.TimeoutError:
            logger.warning(f"HTTP API request timed out after {self.timeout}s")
            return None
        except Exception as e:
            logger.warning(f"Unexpected error fetching energy from HTTP API: {e}")
            return None


class DummyEnergyReader(MetricsReader):
    """Dummy energy reader for systems without energy monitoring support."""

    def __init__(self):
        """Initialize dummy reader."""
        super().__init__()
        self.available = False
        logger.info("No energy monitoring available on this system")

    @staticmethod
    def is_available() -> bool:
        """Always returns True as a fallback option.

        Returns:
            True (dummy reader is always available as fallback).
        """
        return False

    def read_metrics(self) -> Optional[Dict]:
        """Return None as no energy metrics are available.

        Returns:
            None
        """
        return None


def get_energy_reader(config: Optional[Dict] = None) -> List[MetricsReader]:
    """Factory function to get the appropriate energy readers for the current system.

    This function detects the operating system and available energy monitoring
    sensors, then returns a list of appropriate energy reader instances.
    The list can contain both external readers (HTTP API for external power meters)
    and internal readers (RAPL, PowerMetrics for system-level energy monitoring).

    Priority order for internal readers:
    1. RAPL (Linux with Intel CPUs)
    2. PowerMetrics (macOS)
    3. DummyEnergyReader (fallback for unsupported systems)

    External readers (if configured):
    - HTTP API (for external power measurement devices)

    Args:
        config: Optional configuration dictionary. Supported keys:
            - energy_api_url: URL for HTTP API energy reader
              (e.g., "http://server_ip:port/device/<hostname>")
            - energy_api_timeout: Request timeout in seconds (default: 5.0)

    Returns:
        List[MetricsReader]: List of energy reader instances. Can contain multiple
                            readers (e.g., both external HTTP API and internal RAPL).
    """
    config = config or {}
    system = platform.system()
    logger.info(f"Detecting energy readers for {system}")

    readers = []

    # Try HTTP API for external power measurement (if configured)
    if "energy_api_url" in config:
        if HTTPAPIReader.is_available():
            api_url = config["energy_api_url"]
            timeout = config.get("energy_api_timeout", 5.0)
            logger.info(f"Adding HTTP API energy reader (external) with URL: {api_url}")
            readers.append(HTTPAPIReader(api_url, timeout))
        else:
            logger.warning(
                "HTTP API energy reader requested but aiohttp is not installed"
            )

    # Try internal readers based on platform
    # Try RAPL (Linux)
    if RAPLReader.is_available():
        logger.info("Adding RAPL energy reader (internal)")
        readers.append(RAPLReader())
    # Try PowerMetrics (macOS)
    elif PowerMetricsReader.is_available():
        logger.info("Adding PowerMetrics energy reader (internal)")
        readers.append(PowerMetricsReader())
    else:
        # Fallback to dummy reader for internal monitoring
        logger.warning(
            f"No internal energy monitoring available for {system}, using dummy reader"
        )
        readers.append(DummyEnergyReader())

    return readers
