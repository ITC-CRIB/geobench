"""Energy monitoring module using RAPL (Running Average Power Limit)."""

import logging
import platform
import os
import glob
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)


class EnergyReader:
    """Reader for RAPL energy metrics."""
    
    def __init__(self):
        """Initialize RAPL reader."""
        self.available = False
        self.domains = {}
        self._init_energy_reading()
    
    def _init_energy_reading(self):
        """Initialize RAPL interface based on the operating system."""
        system = platform.system()
        
        if system == 'Linux':
            self._init_linux_rapl()
        elif system == 'Darwin':  # macOS
            self._init_macos_powermetrics()
        else:
            logger.warning(f"RAPL is not supported on {system}")
    
    def _init_linux_rapl(self):
        """Initialize RAPL for Linux systems via sysfs."""
        rapl_base = '/sys/class/powercap/intel-rapl'
        
        if not os.path.exists(rapl_base):
            logger.warning("RAPL interface not found at /sys/class/powercap/intel-rapl")
            return
        
        # Find all RAPL domains
        for domain_path in glob.glob(f'{rapl_base}/intel-rapl:*'):
            if ':' not in os.path.basename(domain_path):
                continue
                
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
    
    def _init_macos_powermetrics(self):
        """Initialize RAPL for macOS systems.
        
        Note: macOS requires special tools like powermetrics (requires sudo)
        or Intel Power Gadget API. This is a placeholder for future implementation.
        """
        logger.warning("RAPL on macOS requires powermetrics or Intel Power Gadget")
        logger.info("Consider using 'sudo powermetrics' for energy measurements on macOS")
        # For now, mark as unavailable
        self.available = False
    
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
                    energy_readings[domain_id] = {
                        'name': domain_info['name'],
                        'energy_uj': energy_uj,
                        'max_energy_uj': domain_info['max_energy'],
                    }
            except (IOError, ValueError) as e:
                logger.debug(f"Failed to read energy from {domain_id}: {e}")
                continue
        
        return energy_readings if energy_readings else None
    
    def calculate_energy_diff(self, 
                             start_reading: Dict[str, int], 
                             end_reading: Dict[str, int]) -> Dict[str, float]:
        """Calculate energy consumption between two readings.
        
        Args:
            start_reading: Initial energy reading
            end_reading: Final energy reading
        
        Returns:
            Dictionary mapping domain names to energy consumed in Joules,
            handling counter wraparound if necessary.
        """
        energy_consumed = {}
        
        for domain_id in start_reading.keys():
            if domain_id not in end_reading:
                continue
            
            start_uj = start_reading[domain_id]['energy_uj']
            end_uj = end_reading[domain_id]['energy_uj']
            max_uj = start_reading[domain_id]['max_energy_uj']
            name = start_reading[domain_id]['name']
            
            # Handle counter wraparound
            if end_uj < start_uj and max_uj is not None:
                # Counter wrapped around
                diff_uj = (max_uj - start_uj) + end_uj
            else:
                diff_uj = end_uj - start_uj
            
            # Convert microjoules to joules
            energy_consumed[name] = diff_uj / 1_000_000.0
        
        return energy_consumed


def get_rapl_reader() -> EnergyReader:
    """Get a RAPL reader instance.
    
    Returns:
        RAPLReader instance
    """
    return EnergyReader()


def collect_energy_metrics(rapl_reader: EnergyReader) -> Optional[Dict]:
    """Collect current energy metrics from RAPL.
    
    Args:
        rapl_reader: Initialized RAPLReader instance
    
    Returns:
        Dictionary containing energy readings, or None if not available
    """
    if not rapl_reader or not rapl_reader.available:
        return None
    
    readings = rapl_reader.read_energy()
    
    if not readings:
        return None
    
    # Format for storage
    metrics = {
        'timestamp': None,  # Will be set by caller
        'domains': readings,
    }
    
    return metrics
