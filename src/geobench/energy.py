"""Energy monitoring module using RAPL (Running Average Power Limit)."""

import logging
import platform
import os
import glob
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

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
                    rapl_domain_name = domain_info['name']
                    energy_readings[rapl_domain_name] = energy_uj
            except (IOError, ValueError) as e:
                print(f"Failed to read energy from {domain_id}: {e}")
                continue
        
        return {"energy": energy_readings} if energy_readings else None


def get_rapl_reader() -> EnergyReader:
    """Get a RAPL reader instance.
    
    Returns:
        RAPLReader instance
    """
    return EnergyReader()