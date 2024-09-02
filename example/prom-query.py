import requests
import time
from prometheus_api_client import PrometheusConnect

# Prometheus endpoint URL
PROMETHEUS_URL = "http://localhost:9090"

prom = PrometheusConnect(url=PROMETHEUS_URL, disable_ssl=True)

def get_cpu_usage():
    # Query to calculate CPU usage percentage
    # Sum of non-idle CPU time divided by total CPU time, multiplied by 100
    query = 'sum(rate(node_cpu_seconds_total{mode!="idle"}[1m])) / count(node_cpu_seconds_total) * 100'
    result = prom.custom_query(query=query)
    if result:
        return float(result[0]['value'][1])
    return None

def get_memory_usage():
    query = '(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100'
    result = prom.custom_query(query=query)
    if result:
        return float(result[0]['value'][1])
    return None

def main():
    while True:
        try:
            cpu_usage = get_cpu_usage()
            memory_usage = get_memory_usage()

            if cpu_usage is not None and memory_usage is not None:
                print(f"CPU Usage: {cpu_usage:.2f}%")
                print(f"Memory Usage: {memory_usage:.2f}%")
            else:
                print("Failed to retrieve metrics")

            print("---")
            time.sleep(5)  # Wait for 5 seconds before the next query

        except requests.exceptions.RequestException as e:
            print(f"Error connecting to Prometheus: {e}")
            time.sleep(10)  # Wait for 10 seconds before retrying
        except Exception as e:
            print(f"An error occurred: {e}")
            time.sleep(10)  # Wait for 10 seconds before retrying

if __name__ == "__main__":
    main()
