"""PowerMetrics collector module."""

import shutil
import subprocess

from . import Collector, CollectorInfo

import logging

logger = logging.getLogger(__name__)


class PowerMetricsCollector(Collector):
    """Collector for macOS powermetrics energy metrics."""

    @classmethod
    def get_info(cls) -> CollectorInfo:
        """Return collector information."""
        return CollectorInfo(
            code="powermetrics",
            name="PowerMetrics Energy Collector",
            description="Energy metrics using PowerMetrics on macOS.",
            category="energy",
        )
    
    def __init__(self, config: dict | None = None):
        """Initialize PowerMetrics collector."""
        super().__init__(config)

        # Raise exception if powermetrics is not available
        if shutil.which("powermetrics") is None:
            raise RuntimeError("powermetrics is not available")

        # Raise exception if cannot run powermetrics
        try:
            result = subprocess.run(
                ["powermetrics", "--help"], capture_output=True, timeout=5, check=False
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"powermetrics failed with return code: {result.returncode}"
                )

        except (subprocess.TimeoutExpired, FileNotFoundError):
            raise RuntimeError("Cannot execute powermetrics")

        self.last_reading = None

    def read_metrics(self) -> dict:
        """Read current energy metrics using powermetrics.

        Returns:
            Dictionary containing energy metrics in microjoules (μJ).
        """
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
                return {}

            # Parse the output to extract energy metrics
            energy_readings = self._parse_output(result.stdout)

            if energy_readings:
                self.last_reading = energy_readings
                return {"energy": energy_readings}
            else:
                return {}

        except (subprocess.TimeoutExpired, FileNotFoundError) as err:
            logger.warning("Failed to read energy from powermetrics: %s", err)
            return {}

    def _parse_output(self, output: str) -> dict:
        """Parse powermetrics output to extract energy metrics.

        Args:
            output: Raw output from powermetrics command.

        Returns:
            Dictionary mapping metric names to energy values in microjoules.
        """
        out = {}

        for line in output.split("\n"):
            line = line.strip()

            if "CPU Power" in line or "GPU Power" in line or "ANE Power" in line:
                parts = line.split(":")
                if len(parts) >= 2:
                    name = parts[0].strip()
                    value = parts[1].strip().split()[0]
                    try:
                        # Convert to microjoules (assuming powermetrics reports in mW)
                        # This is a simplified parsing - real implementation may need more robust parsing
                        value = float(value)
                        # Convert mW to microjoules (mW * 1000 = μW, for 100ms sample)
                        energy_uj = int(value * 100)
                        out[name] = energy_uj
                    except (ValueError, IndexError):
                        continue

        return out
