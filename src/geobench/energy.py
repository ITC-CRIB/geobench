"""Energy monitoring module with support for multiple energy sensors."""

import logging
import platform
import os
import glob
import subprocess
import shutil
from abc import ABC, abstractmethod
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class EnergyReader(ABC):
    """Abstract base class for energy readers."""
    
    def __init__(self):
        """Initialize energy reader."""
        self.available = False
    
    @abstractmethod
    def read_energy(self) -> Optional[Dict[str, int]]:
        """Read current energy metrics.
        
        Returns:
            Dictionary containing energy readings, or None if not available.
        """
        pass
    
    @staticmethod
    @abstractmethod
    def is_available() -> bool:
        """Check if this energy reader is available on the current system.
        
        Returns:
            True if the energy reader can be used, False otherwise.
        """
        pass


class RAPLReader(EnergyReader):
    """Reader for RAPL energy metrics."""
    
    def __init__(self):
        """Initialize RAPL reader."""
        super().__init__()
        self.domains = {}
        self._init_energy_reading()
    
    @staticmethod
    def is_available() -> bool:
        """Check if RAPL is available on the current system.
        
        Returns:
            True if RAPL interface is available, False otherwise.
        """
        if platform.system() != 'Linux':
            return False
        
        rapl_base = '/sys/class/powercap/intel-rapl'
        if not os.path.exists(rapl_base):
            return False
        
        # Check if we can find at least one valid RAPL domain
        all_paths = []
        all_paths.extend(glob.glob(f'{rapl_base}/intel-rapl:*'))
        all_paths.extend(glob.glob(f'{rapl_base}/intel-rapl:*/intel-rapl:*'))
        
        for domain_path in all_paths:
            energy_file = os.path.join(domain_path, 'energy_uj')
            if os.path.exists(energy_file):
                try:
                    with open(energy_file, 'r') as f:
                        f.read()
                    return True
                except (IOError, PermissionError):
                    continue
        
        return False
    
    def _init_energy_reading(self):
        """Initialize RAPL interface based on the operating system."""
        system = platform.system()
        
        if system == 'Linux':
            self._init_linux_rapl()
        else:
            logger.warning(f"RAPL is not supported on {system}")
    
    def _init_linux_rapl(self):
        """Initialize RAPL for Linux systems via sysfs."""
        rapl_base = '/sys/class/powercap/intel-rapl'
        
        if not os.path.exists(rapl_base):
            logger.warning("RAPL interface not found at /sys/class/powercap/intel-rapl")
            return
        
        # Find all RAPL domains (including subdomains like DRAM, CPU cores)
        # Pattern matches both intel-rapl:X and intel-rapl:X:Y
        all_paths = []
        all_paths.extend(glob.glob(f'{rapl_base}/intel-rapl:*'))
        all_paths.extend(glob.glob(f'{rapl_base}/intel-rapl:*/intel-rapl:*'))
        
        for domain_path in all_paths:
            try:
                # Read domain name
                name_file = os.path.join(domain_path, 'name')
                if not os.path.exists(name_file):
                    continue
                    
                with open(name_file, 'r') as f:
                    domain_name = f.read().strip()
                
                # Get energy file path
                energy_file = os.path.join(domain_path, 'energy_uj')
                max_energy_file = os.path.join(domain_path, 'max_energy_range_uj')
                
                if not os.path.exists(energy_file):
                    continue
                
                # Read max energy range if available
                max_energy = None
                if os.path.exists(max_energy_file):
                    try:
                        with open(max_energy_file, 'r') as f:
                            max_energy = int(f.read().strip())
                    except (IOError, ValueError):
                        pass
                
                domain_id = os.path.basename(domain_path)
                self.domains[domain_id] = {
                    'name': domain_name,
                    'energy_file': energy_file,
                    'max_energy': max_energy,
                }
                
                logger.info(f"Found RAPL domain: {domain_name} ({domain_id})")
                
            except (IOError, PermissionError) as e:
                logger.warning(f"Cannot access RAPL domain {domain_path}: {e}")
                continue
        
        if self.domains:
            self.available = True
            logger.info(f"RAPL initialized with {len(self.domains)} domains")
        else:
            logger.warning("No RAPL domains found")
    
    def read_energy(self) -> Optional[Dict[str, int]]:
        """Read current energy counters from all RAPL domains.
        
        Returns:
            Dictionary mapping domain IDs to energy values in microjoules (μJ),
            or None if RAPL is not available.
        """
        if not self.available:
            return None
        
        energy_readings = {}
        
        for domain_id, domain_info in self.domains.items():
            try:
                with open(domain_info['energy_file'], 'r') as f:
                    energy_uj = int(f.read().strip())
                    rapl_domain_name = domain_info['name']
                    energy_readings[rapl_domain_name] = energy_uj
            except (IOError, ValueError) as e:
                print(f"Failed to read energy from {domain_id}: {e}")
                continue
        
        return {"energy": energy_readings} if energy_readings else None


class PowerMetricsReader(EnergyReader):
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
        if platform.system() != 'Darwin':
            return False
        
        # Check if powermetrics command exists
        if shutil.which('powermetrics') is None:
            return False
        
        # Try to run powermetrics to see if we have permissions
        try:
            result = subprocess.run(
                ['powermetrics', '--help'],
                capture_output=True,
                timeout=5,
                check=False
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _init_energy_reading(self):
        """Initialize powermetrics interface."""
        if platform.system() != 'Darwin':
            logger.warning("PowerMetrics is only supported on macOS")
            return
        
        if not shutil.which('powermetrics'):
            logger.warning("powermetrics command not found")
            return
        
        # Test if we can run powermetrics
        try:
            result = subprocess.run(
                ['powermetrics', '--help'],
                capture_output=True,
                timeout=5,
                check=False
            )
            if result.returncode == 0:
                self.available = True
                logger.info("PowerMetrics initialized successfully")
            else:
                logger.warning("powermetrics is not accessible (may need sudo)")
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.warning(f"Failed to initialize powermetrics: {e}")
    
    def read_energy(self) -> Optional[Dict[str, int]]:
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
                ['powermetrics', '-n', '1', '-i', '100', '--samplers', 'tasks'],
                capture_output=True,
                timeout=5,
                text=True,
                check=False
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
        for line in output.split('\n'):
            line = line.strip()
            
            # Look for energy-related metrics
            if 'CPU Power' in line or 'GPU Power' in line or 'ANE Power' in line:
                parts = line.split(':')
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


class DummyEnergyReader(EnergyReader):
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
    
    def read_energy(self) -> Optional[Dict[str, int]]:
        """Return None as no energy metrics are available.
        
        Returns:
            None
        """
        return None


def get_energy_reader() -> EnergyReader:
    """Factory function to get the appropriate energy reader for the current system.
    
    This function detects the operating system and available energy monitoring
    sensors, then returns an instance of the appropriate energy reader class.
    
    Priority order:
    1. RAPL (Linux with Intel CPUs)
    2. PowerMetrics (macOS)
    3. DummyEnergyReader (fallback for unsupported systems)
    
    Returns:
        EnergyReader: An instance of the appropriate energy reader class.
    
    Examples:
        >>> reader = get_energy_reader()
        >>> if reader.available:
        ...     energy = reader.read_energy()
        ...     print(f"Energy: {energy}")
    """
    system = platform.system()
    logger.info(f"Detecting energy reader for {system}")
    
    # Try RAPL first (Linux)
    if RAPLReader.is_available():
        logger.info("Using RAPL energy reader")
        return RAPLReader()
    
    # Try PowerMetrics (macOS)
    if PowerMetricsReader.is_available():
        logger.info("Using PowerMetrics energy reader")
        return PowerMetricsReader()
    
    # Fallback to dummy reader
    logger.warning(f"No energy monitoring available for {system}, using dummy reader")
    return DummyEnergyReader()