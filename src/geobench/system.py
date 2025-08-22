import platform
import psutil
import statistics
import time


def get_system_info():
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
        'physical_cores': psutil.cpu_count(logical=False),
        'total_cores': psutil.cpu_count(logical=True),
        'max_frequency': psutil.cpu_freq().max,
        'min_frequency': psutil.cpu_freq().min,
        'current_frequency': psutil.cpu_freq().current,
        'usage': psutil.cpu_percent(interval=1),
    }

    # Memory information
    mem = psutil.virtual_memory()
    out['memory'] = {
        'total': mem.total,
        'available': mem.available,
        'percentage': mem.percent,
        'used': mem.used,
        'free': mem.free,
    }

    # Disk information
    out['disk'] = []
    for partition in psutil.disk_partitions():
        info = {
            'device': partition.device,
            'mountpoint': partition.mountpoint,
            'fstype': partition.fstype,
        }
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            info.update({
                'total_size': usage.total,
                'used': usage.used,
                'free': usage.free,
                'percentage': usage.percent,
            })

        except PermissionError:
            pass

        out['disk'].append(info)

    return out


def monitor_system(duration: float=10.0, interval: float=1.0):
    """Performs system monitoring for a specific duration.

    Args:
        duration (int): Monitoring duration (s) (default = 10).
        interval (int): Interval between each sample (s) (default = 1)

    Returns:
        Dictionary of system monitoring results.
    """
    timestamps = []
    cpu_usages = []
    mem_usages = []
    processes = []
    summary = {}

    start_time = time.time()
    while True:
        now = time.time()
        if (now - start_time) >= duration:
            break

        timestamps.append(now)
        cpu_usages.append(psutil.cpu_percent())
        mem_usages.append(psutil.virtual_memory().percent)

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
                    'cpu_usage': info['cpu_percent'],
                    'memory_usage': info['memory_percent'],
                    'read_bytes': read_bytes,
                    'write_bytes': write_bytes,
                }

                data.append(item)
                summary[pid]['data'].append(item)

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        processes.append(data)

        time.sleep(interval)

    for item in summary.values():
        data = item['data']
        item['avg_cpu_usage'] = statistics.mean([item['cpu_usage'] for item in data])
        item['avg_memory_usage'] = statistics.mean([item['memory_usage'] for item in data])
        item['read_bytes'] = data[-1]['read_bytes'] - data[0]['read_bytes']
        item['write_bytes'] = data[-1]['write_bytes'] - data[0]['write_bytes']
        del item['data']

    summary = list(summary.values())
    summary.sort(key=lambda item: item['avg_cpu_usage'], reverse=True)

    return {
        'duration': duration,
        'interval': interval,
        'start_time': timestamps[0],
        'end_time': timestamps[-1],
        'avg_cpu_usage': statistics.mean(cpu_usages) if cpu_usages else None,
        'avg_mem_usage': statistics.mean(mem_usages) if mem_usages else None,
        'process_summary': summary,
        'timestamps': timestamps,
        'cpu_usages': cpu_usages,
        'mem_usages': mem_usages,
        'processes': processes,
    }
