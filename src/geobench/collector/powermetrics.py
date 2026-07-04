"""PowerMetrics collector module."""

import platform
import shutil
import subprocess

from . import Collector

import logging

logger = logging.getLogger(__name__)


class PowerMetricsCollector(Collector):
    """Collector for macOS powermetrics energy metrics."""

    def __init__(self):
        """Initialize PowerMetrics collector."""
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
                logger.debug("PowerMetrics initialized successfully")
            else:
                logger.warning("powermetrics is not accessible (may need sudo)")
        except (subprocess.TimeoutExpired, FileNotFoundError) as err:
            logger.warning("Failed to initialize powermetrics: %s", err)

    def read_metrics(self) -> dict | None:
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

    def _parse_powermetrics_output(self, output: str) -> dict:
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
