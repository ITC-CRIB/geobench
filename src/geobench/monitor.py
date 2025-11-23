import platform
import psutil
import statistics
import threading
import time
import queue

from .energy import get_energy_reader
from .metrics import get_metrics_readers_for_source

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def get_system_info() -> dict:
    """Returns system information."""
    out = {}

    # OS information
    out['os'] = {
        'system': platform.system(),
        'node': platform.node(),
        'release': platform.release(),
        'version': platform.version(),
        'machine': platform.machine(),
        'processor': platform.processor(),
    }

    # CPU information
    out['cpu'] = {
        'physical_count': psutil.cpu_count(logical=False),
        'logical_count': psutil.cpu_count(logical=True),
        'max_frequency': psutil.cpu_freq().max,
        'min_frequency': psutil.cpu_freq().min,
        'frequency': psutil.cpu_freq().current,
        'percent': psutil.cpu_percent(interval=0.1, percpu=True),
    }

    # Memory information
    out['memory'] = psutil.virtual_memory()._asdict()

    # Disk information
    out['disk'] = []
    for partition in psutil.disk_partitions():
        info = {
            'device': partition.device,
            'mountpoint': partition.mountpoint,
            'fstype': partition.fstype,
        }
        try:
            info.update(psutil.disk_usage(partition.mountpoint)._asdict())

        except PermissionError:
            pass

        out['disk'].append(info)

    return out


def get_process_info(process) -> dict:
    """Returns process information.

    Args:
        process: Process.

    Returns:
        Dictionary of process information.
    """
    return {
        'pid': process.pid,
        'parent_pid': process.ppid(),
        'name': process.name(),
        'executable': process.exe(),
        'command': process.cmdline(),
        'environment': process.environ(),
        'create_time': process.create_time(),
        'metrics': [],
    }


def monitor_system(duration: float=10.0, interval: float=1.0):
    """Performs system monitoring for a specific duration.

    Args:
        duration (int): Monitoring duration (s) (default = 10).
        interval (int): Interval between each sample (s) (default = 1)

    Returns:
        Dictionary of system monitoring results.
    """
    timestamps = []
    cpu_percents = []
    memory_percents = []
    processes = []
    summary = {}

    start_time = time.time()
    while True:
        now = time.time()
        if (now - start_time) >= duration:
            break

        timestamps.append(now)
        cpu_percents.append(psutil.cpu_percent())
        memory_percents.append(psutil.virtual_memory().percent)

        data = []
        for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'status']):
            try:
                info = proc.info

                try:
                    io_counters = proc.io_counters()
                    read_bytes = io_counters.read_bytes
                    write_bytes = io_counters.write_bytes

                except (psutil.AccessDenied, AttributeError):
                    read_bytes = None
                    write_bytes = None

                pid = info['pid']

                if pid not in summary:
                    summary[pid] = {
                        'pid': pid,
                        'name': info['name'],
                        'username': info.get('username'),
                        'data': [],
                    }

                item = {
                    'pid': pid,
                    'cpu_percent': info['cpu_percent'] if info['cpu_percent'] is not None else 0.0,
                    'memory_percent': info['memory_percent'] if info['memory_percent'] is not None else 0.0,
                    'read_bytes': read_bytes if read_bytes is not None else 0,
                    'write_bytes': write_bytes if write_bytes is not None else 0,
                }

                data.append(item)
                summary[pid]['data'].append(item)

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        processes.append(data)

        time.sleep(interval)

    for item in summary.values():
        data = item['data']
        # Only include non-None values for calculating average CPU and memory 
        cpu_percent_list = [item['cpu_percent'] for item in data if item['cpu_percent'] is not None]
        if cpu_percent_list:
            item['avg_cpu_percent'] = statistics.mean(cpu_percent_list)
        memory_percent_list = [item['memory_percent'] for item in data if item['memory_percent'] is not None]
        if memory_percent_list:
            item['avg_memory_percent'] = statistics.mean(memory_percent_list)
        # Check if read/write bytes are available at the first and last data points
        if len(data) > 0:
            # Calculate read/write bytes if the values are not None
            if data[-1]['read_bytes'] and data[0]['read_bytes']:
                item['read_bytes'] = data[-1]['read_bytes'] - data[0]['read_bytes']
            # Calculate read/write bytes if the values are not None
            if data[-1]['write_bytes'] and data[0]['write_bytes']:
                item['write_bytes'] = data[-1]['write_bytes'] - data[0]['write_bytes']
        del item['data']

    summary = list(summary.values())
    summary.sort(key=lambda item: item['avg_cpu_percent'], reverse=True)

    return {
        'duration': duration,
        'interval': interval,
        'start_time': timestamps[0],
        'end_time': timestamps[-1],
        'avg_cpu_percent': statistics.mean(cpu_percents) if cpu_percents else None,
        'avg_memory_percent': statistics.mean(memory_percents) if memory_percents else None,
        'process_summary': summary,
        'timestamps': timestamps,
        'cpu_percents': cpu_percents,
        'memory_percents': memory_percents,
        'processes': processes,
    }


class DataCollector(threading.Thread):
    """Thread-based data collector for system metrics from different sources."""
    
    def __init__(self, name: str, interval: float, readers: list, 
                 process, stop_event: threading.Event, source_type: str = 'internal'):
        """Initialize data collector thread.
        
        Args:
            name: Name identifier for this data source
            interval: Collection interval in seconds
            readers: List of MetricsReader instances to collect data from
            process: Process being monitored
            stop_event: Event to signal thread to stop
        """
        super().__init__(daemon=True)
        self.name = name
        self.interval = interval
        self.readers = readers
        self.process = process
        self.stop_event = stop_event
        self.collected_metrics = []
        self.initial_readings = {}
        
        # Store initial readings from all readers
        self._store_initial_readings()
        
    def _store_initial_readings(self):
        """Store initial readings from all metrics readers."""
        for reader in self.readers:
            initial = reader.read_metrics()
            if initial:
                self.initial_readings.update(initial)
    
    def _collect_metrics_from_readers(self) -> dict:
        """Collect metrics from all configured readers.
        
        Returns:
            Dictionary containing all metrics from all readers, with prefixed keys.
        """
        metrics = {}
        
        for reader in self.readers:
            current_metrics = reader.read_metrics()
            if current_metrics:
                metrics.update(current_metrics)
        
        return metrics
    
    def run(self):
        """Run the data collection loop."""
        step = 0
        
        logger.info(f"[{self.name}] Data collector started (interval={self.interval}s)")
        
        while not self.stop_event.is_set():
            step += 1
            
            # Check if process is still running
            if type(self.process) is psutil.Process:
                if not self.process.is_running():
                    break
            else:
                if self.process.poll() is not None:
                    break
            
            # Collect timestamp
            metric = {
                'step': step,
                'timestamp': time.time()
            }
            
            # Collect metrics from all readers
            metric.update(self._collect_metrics_from_readers())
            
            self.collected_metrics.append(metric)
            
            # Sleep for the specified interval
            time.sleep(self.interval)
        
        logger.info(f"[{self.name}] Data collector stopped ({len(self.collected_metrics)} samples)")
    
    def get_metrics(self) -> list:
        """Get collected metrics.
        
        Returns:
            List of collected metric dictionaries
        """
        return self.collected_metrics


def monitor_process(process, interval: float=1.0, stop_event=None, energy_config: dict=None, 
                    data_sources: list=None) -> dict:
    """Monitors process and system metrics while process is running.

    Args:
        process: Process to be monitored.
        interval (float): Interval between each sample (s) (default = 1.0).
        stop_event (threading.Event, optional): Event to signal monitoring to stop.
        energy_config (dict, optional): Configuration for energy monitoring (legacy).
            Supported keys:
            - energy_api_url: URL for HTTP API energy reader
            - energy_api_timeout: Timeout for HTTP API requests in seconds
        data_sources (list, optional): List of data source configurations for multi-threaded collection.
            Each source should have:
            - name: Source identifier
            - interval: Collection interval in seconds
            - metrics: List of metrics to collect (e.g., ['psutils', 'energy', {'smart_plug': {...}}])
            
    Returns:
        Dictionary containing:
        - system: List of system metrics (legacy mode) or dict of metrics by source (multi-threaded mode)
        - processes: Process metrics
        - data_sources: List of source names (only in multi-threaded mode)
    """
    process_metrics = {process.pid: get_process_info(process)}
    
    # Determine if we're using multi-threaded mode
    use_multi_threaded = data_sources is not None and len(data_sources) > 0
    
    if use_multi_threaded:
        # Multi-threaded mode with parallel data collection
        logger.info(f"Starting multi-threaded monitoring with {len(data_sources)} data sources")
        
        # Create stop event if not provided
        if stop_event is None:
            stop_event = threading.Event()
        
        # Create and start data collector threads
        collectors = []
        for source_config in data_sources:
            source_name = source_config.get('name', f'source_{len(collectors)}')
            source_interval = source_config.get('interval', interval)
            
            # Get appropriate metrics readers for this source
            readers = get_metrics_readers_for_source(source_config)
            
            if not readers:
                logger.warning(f"No readers available for source '{source_name}', skipping")
                continue
            else:
                logger.info(f"Source '{source_name}' has {len(readers)} readers configured")
            
            collector = DataCollector(
                name=source_name,
                interval=source_interval,
                readers=readers,
                process=process,
                stop_event=stop_event,
            )
            collectors.append(collector)
            collector.start()
        
        # Monitor process and collect process-specific metrics
        step = 0
        psutil.cpu_percent()
        process.cpu_percent()
        
        while True:
            step += 1
            
            # Stop if process has terminated or stop event is set
            if type(process) is psutil.Process:
                if not process.is_running():
                    break
                if stop_event.is_set():
                    break
            else:
                if process.poll() is not None:
                    break
            
            # Get related processes
            processes = [process]
            for child in process.children(recursive=True):
                try:
                    if child.pid not in process_metrics:
                        process_metrics[child.pid] = get_process_info(child)
                    processes.append(child)
                    child.cpu_percent()
                except psutil.NoSuchProcess:
                    pass
            
            # Sleep with the base interval
            time.sleep(interval)
            
            # Collect process metrics
            for p in processes:
                try:
                    with p.oneshot():
                        try:
                            io_counters = p.io_counters()
                            read_bytes = io_counters.read_bytes
                            write_bytes = io_counters.write_bytes
                        except (psutil.AccessDenied, AttributeError):
                            read_bytes = 0
                            write_bytes = 0
                        
                        collected_metric = {
                            'step': step,
                            'timestamp': time.time(),
                            'cpu_percent': p.cpu_percent(),
                            'memory_percent': p.memory_percent(),
                            'num_threads': p.num_threads(),
                            'read_bytes': read_bytes,
                            'write_bytes': write_bytes,
                        }
                        process_metrics[p.pid]['metrics'].append(collected_metric)
                except psutil.NoSuchProcess:
                    pass
        
        # Signal all collectors to stop
        stop_event.set()
        
        # Wait for all collector threads to finish
        for collector in collectors:
            collector.join(timeout=5.0)
        
        # Aggregate results from all collectors
        system_metrics_by_source = {}
        for collector in collectors:
            system_metrics_by_source[collector.name] = collector.get_metrics()
        
        out = {
            'system': system_metrics_by_source,
            'processes': process_metrics
        }
        
    else:
        # Legacy single-threaded mode for backward compatibility
        logger.info("Starting single-threaded monitoring (legacy mode)")
        
        step = 0
        system_metrics = []
        
        # Initialize energy monitoring - get list of readers (can be multiple)
        energy_readers = get_energy_reader(energy_config)
        initial_energy = {}
        
        # Initialize each reader
        for reader in energy_readers:
            if reader.available:
                reader_key = f"{reader.reader_type}_{reader.__class__.__name__}"
                initial = reader.read_energy()
                if initial:
                    initial_energy[reader_key] = initial
                logger.info(f"Energy monitoring enabled for {reader.__class__.__name__} ({reader.reader_type})")
            else:
                logger.info(f"Energy monitoring not available for {reader.__class__.__name__}")
        
        if not initial_energy:
            logger.info("No energy monitoring available")

        # Initialize metrics
        psutil.cpu_percent()
        process.cpu_percent()

        # Monitoring loop
        while True:
            step += 1

            # Stop if process has terminated or stop event is set
            if type(process) is psutil.Process:
                if not process.is_running():
                    break
                if stop_event and stop_event.is_set():
                    break
            else:
                if process.poll() is not None:
                    break

            # Get related processes
            processes = [process]
            for child in process.children(recursive=True):
                try:
                    if child.pid not in process_metrics:
                        process_metrics[child.pid] = get_process_info(child)

                    processes.append(child)
                    child.cpu_percent()

                except psutil.NoSuchProcess:
                    pass

            # Sleep
            time.sleep(interval)

            # Get system metrics
            sys_metric = {
                'step': step,
                'timestamp': time.time(),
                'cpu_percent': psutil.cpu_percent(percpu=True),
                'memory_usage': psutil.virtual_memory()._asdict(),
            }
            try:
                net_io_counters = psutil.net_io_counters()
                sys_net_bytes_sent = net_io_counters.bytes_sent
                sys_net_bytes_recv = net_io_counters.bytes_recv
            except (psutil.AccessDenied, AttributeError):
                sys_net_bytes_sent = 0
                sys_net_bytes_recv = 0
            
            try:
                disk_io_counters = psutil.disk_io_counters()
                sys_disk_bytes_read = disk_io_counters.read_bytes
                sys_disk_bytes_write = disk_io_counters.write_bytes
            except (psutil.AccessDenied, AttributeError):
                sys_disk_bytes_read = 0
                sys_disk_bytes_write = 0

            # Update metrics
            sys_metric.update({
                'net_bytes_sent': sys_net_bytes_sent,
                'net_bytes_recv': sys_net_bytes_recv,
                'disk_bytes_read': sys_disk_bytes_read,
                'disk_bytes_write': sys_disk_bytes_write
            })

            # Collect energy metrics from all available readers
            for reader in energy_readers:
                if reader.available:
                    current_energy = reader.read_energy()
                    if current_energy:
                        # Prefix keys with reader type to distinguish between internal/external
                        reader_key = f"{reader.reader_type}_{reader.__class__.__name__}"
                        for metric_key, metric_value in current_energy.items():
                            prefixed_key = f"{reader_key}_{metric_key}"
                            sys_metric[prefixed_key] = metric_value
            
            system_metrics.append(sys_metric)

            # Get process metrics
            for p in processes:
                try:
                    with p.oneshot():
                        try:
                            io_counters = p.io_counters()
                            read_bytes = io_counters.read_bytes
                            write_bytes = io_counters.write_bytes
                        except (psutil.AccessDenied, AttributeError):
                            read_bytes = 0
                            write_bytes = 0
                        collected_metric = {
                            'step': step,
                            'timestamp': time.time(),
                            'cpu_percent': p.cpu_percent(),
                            'memory_percent': p.memory_percent(),
                            'num_threads': p.num_threads(),
                            'read_bytes': read_bytes,
                            'write_bytes': write_bytes,
                        }

                        process_metrics[p.pid]['metrics'].append(collected_metric)

                except psutil.NoSuchProcess:
                    pass

        out = {
            'system': system_metrics,
            'processes': process_metrics
        }

    return out
