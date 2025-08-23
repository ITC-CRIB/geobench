import psutil
import time


import logging
logger = logging.getLogger(__name__)


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
