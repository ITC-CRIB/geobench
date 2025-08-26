import platform
import psutil
import statistics
import time


import logging
logger = logging.getLogger(__name__)


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


def monitor_process(process, interval: float=1.0):
    """Monitors process and system metrics while process is running.

    Args:
        process: Process to be monitored.
        interval (float): Interval between each sample (s) (default = 1.0).
    """
    step = 0
    system_metrics = []
    process_metrics = {process.pid: get_process_info(process)}

    # Initialize metrics
    psutil.cpu_percent()
    process.cpu_percent()

    # Monitoring loop
    while True:
        step += 1

        # Stop if process has terminated
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
        system_metrics.append({
            'step': step,
            'timestamp': time.time(),
            'cpu_percent': psutil.cpu_percent(percpu=True),
            'memory_usage': psutil.virtual_memory()._asdict(),
        })

        # Get process metrics
        for p in processes:
            try:
                with p.oneshot():
                    process_metrics[p.pid]['metrics'].append({
                        'step': step,
                        'timestamp': time.time(),
                        'cpu_percent': p.cpu_percent(),
                        'memory_percent': p.memory_percent(),
                        'num_threads': p.num_threads(),
                    })

            except psutil.NoSuchProcess:
                pass

    out = {
        'system': system_metrics,
        'processes': process_metrics,
    }

    return out
