import platform
import psutil
import statistics
import time


def get_system_info():
    """Returns system information."""
    # OS information
    system_info = {
        "os": {
            "system": platform.system(),
            "node": platform.node(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor()
        }
    }

    # CPU information
    system_info["cpu"] = {
        "physical_cores": psutil.cpu_count(logical=False),
        "total_cores": psutil.cpu_count(logical=True),
        "max_frequency": psutil.cpu_freq().max,
        "min_frequency": psutil.cpu_freq().min,
        "current_frequency": psutil.cpu_freq().current,
        "usage": psutil.cpu_percent(interval=1)
    }

    # Memory information
    svmem = psutil.virtual_memory()
    system_info["memory"] = {
        "total": svmem.total // (1024 * 1024),
        "available": svmem.available // (1024 * 1024),
        "used": svmem.used // (1024 * 1024),
        "percentage": svmem.percent
    }

    # Disk information
    disk_info = []
    partitions = psutil.disk_partitions()
    for partition in partitions:
        partition_info = {
            "device": partition.device,
            "mountpoint": partition.mountpoint,
            "fstype": partition.fstype
        }
        try:
            partition_usage = psutil.disk_usage(partition.mountpoint)
            partition_info.update({
                "total_size": partition_usage.total // (1024 * 1024),
                "used": partition_usage.used // (1024 * 1024),
                "free": partition_usage.free // (1024 * 1024),
                "percentage": partition_usage.percent
            })
        except PermissionError:
            # this can be caught due to the disk that isn't ready
            partition_info.update({
                "total_size": "PermissionError",
                "used": "PermissionError",
                "free": "PermissionError",
                "percentage": "PermissionError"
            })
        disk_info.append(partition_info)

    system_info["disk"] = disk_info

    return system_info


def _record_process_info(duration: int=30, interval: int=1):
    """Records process information."""
    process_info = {}

    for _ in range(int(duration / interval)):
        for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'status']):
            try:
                proc_info = proc.info
                pid = proc_info['pid']
                name = proc_info['name']
                cpu_usage = proc_info['cpu_percent']
                memory_usage = proc_info['memory_percent']

                # Disk usage (I/O)
                try:
                    io_counters = proc.io_counters()
                    read_bytes = io_counters.read_bytes // (1024 * 1024)  # Convert bytes to MB
                    write_bytes = io_counters.write_bytes // (1024 * 1024)  # Convert bytes to MB
                except (psutil.AccessDenied, AttributeError):
                    read_bytes = write_bytes = 0

                if pid not in process_info:
                    process_info[pid] = {
                        'name': name,
                        'cpu_usage': [],
                        'memory_usage': [],
                        'read_bytes': [],
                        'write_bytes': [],
                        'username': proc_info.get('username', 'N/A')
                    }

                if cpu_usage is not None:
                    process_info[pid]['cpu_usage'].append(cpu_usage)
                if memory_usage is not None:
                    process_info[pid]['memory_usage'].append(memory_usage)
                if read_bytes is not None:
                    process_info[pid]['read_bytes'].append(read_bytes)
                if write_bytes is not None:
                    process_info[pid]['write_bytes'].append(write_bytes)

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        time.sleep(interval)

    return process_info


def _calculate_average_usage(process_info: dict):
    average_info = []

    for pid, info in process_info.items():
        avg_cpu = statistics.mean(info['cpu_usage']) if info['cpu_usage'] else 0
        avg_memory = statistics.mean(info['memory_usage']) if info['memory_usage'] else 0
        avg_read_bytes = statistics.mean(info['read_bytes']) if info['read_bytes'] else 0
        avg_write_bytes = statistics.mean(info['write_bytes']) if info['write_bytes'] else 0

        average_info.append({
            'pid': pid,
            'name': info['name'],
            'avg_cpu_usage': avg_cpu,
            'avg_memory_usage': avg_memory,
            'avg_read_bytes': avg_read_bytes,
            'avg_write_bytes': avg_write_bytes,
            'username': info['username'],
        })

    # Sort by average CPU usage in descending order
    average_info.sort(key=lambda x: x['avg_cpu_usage'], reverse=True)

    return average_info


def record_all_process_info(duration: int=30, interval: int=1):
    """Records all running processes for specific duration, then calculates the
       average CPU and memory usage"""
    process_info = _record_process_info(duration, interval)
    average_info = _calculate_average_usage(process_info)

    return average_info


def monitor_baseline(duration: int=15):
    """Performs baseline monitoring for a specific duration.

    The function returns the average CPU and memory usage.
    """
    cpu_usage = []
    mem_usage = []

    start_time = time.time()
    while time.time() - start_time < duration:
        cpu_usage.append(psutil.cpu_percent(interval=1))
        mem_usage.append(psutil.virtual_memory().percent)
        time.sleep(0.1)

    results = {}
    results["avg_cpu"] = statistics.mean(cpu_usage) if cpu_usage else 0
    results["avg_mem"] = statistics.mean(mem_usage) if mem_usage else 0

    return results