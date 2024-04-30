import requests
import re
import time
import threading
import subprocess
import signal

stop_flag = False
exporter_process_list = []

def fetch_metrics(node_exporter_url='http://localhost:9100/metrics'):
    """
    Fetch metrics from Node Exporter directly.

    Args:
        node_exporter_url (str): The URL where Node Exporter exposes its metrics.

    Returns:
        dict: A dictionary with metric names as keys and their values as lists.
    """
    # Fetch the metrics from Node Exporter
    response = requests.get(node_exporter_url)
    response.raise_for_status()  # Raise an error if the request fails

    # Parse the metrics into a dictionary
    metrics = {}
    lines = response.text.split('\n')

    for line in lines:
        # Skip comments and empty lines
        if line.startswith('#') or not line.strip():
            continue

        # Match metric name and value
        match = re.match(r'([a-zA-Z_:]+)\{?(.*?)\}?\s+(\d+(\.\d+)?)', line)
        if match:
            metric_name = match.group(1)
            metric_value = float(match.group(3))

            # If there are labels, create a composite key
            labels = match.group(2)
            if labels:
                metric_name += "{" + labels + "}"

            # Add to the metrics dictionary
            if metric_name not in metrics:
                metrics[metric_name] = []
            metrics[metric_name].append(metric_value)

    return metrics

def query_metrics_periodically():
    """Function to continuously query metrics every 30 seconds."""
    while not stop_flag:
        try: 
            print("Fetching metrics from Node Exporter...")
            metrics = fetch_metrics()

            # Print some example metrics
            for metric, values in metrics.items():
                print(f"{metric}: {values}")
        except requests.RequestException as e:
            print(f"Error: Unable to reach Node Exporter. Try to reconnect.")
        # Wait for 30 seconds before the next query
        time.sleep(30)

def run_node_exporter():
    """Function to start Node Exporter as a subprocess."""
    print("Running node exporter locally...")
    process = subprocess.Popen(["./node_exporter"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    global exporter_process_list
    exporter_process_list.append(process)
    stdout, stderr = process.communicate()
    return process

def signal_handler(signum, frame, exporter_thread):
    """Handles Ctrl+C signal to terminate both the querying thread and Node Exporter process."""
    print("Signal received. Preparing to stop...")

    global stop_flag
    stop_flag = True
    
    # Terminate all exporter processes
    global exporter_process_list
    for exporter_process in exporter_process_list:
        if exporter_process:
            exporter_process.terminate()
            exporter_process.wait()

    print("Exiting.")
    exit(0)

def main():
    # Start Node Exporter process
    # exporter_process = run_node_exporter()
    exporter_thread = threading.Thread(target=run_node_exporter)
    exporter_thread.start()

    # # Set up signal handler for Ctrl+C
    signal.signal(signal.SIGINT, lambda signum, frame: signal_handler(signum, frame, exporter_thread))

    # Sleep 15s to wait the reachability
    print("Waiting for the exporter severs to initiate...")
    time.sleep(15)

    # Run periodic metrics query
    query_metrics_periodically()

if __name__ == "__main__":
    main()
