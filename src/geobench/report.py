#%%
import json
import statistics

def calculate_run_summary(run_result: dict) -> dict:
    """Calculate summary statistics from single run result.

    Args:
        run_result (dict): The run result data.

    Returns:
        dict: A dictionary containing the summary statistics.
    """
    summary = {
        "avg_system_cpu": {},
        "avg_system_memory": {},
        "process": {}
    }
    # Calculate Average per-core system CPU usage
    system_per_cpu_dict = {}
    if run_result["system"]:
        for system_data in run_result["system"]:
            for i, cpu_percent in enumerate(system_data["cpu_percent"]):
                if i not in system_per_cpu_dict:
                    system_per_cpu_dict[i] = []
                if cpu_percent is not None:
                    system_per_cpu_dict[i].append(cpu_percent)
        for i, cpu_usage in system_per_cpu_dict.items():
            avg_cpu = statistics.mean(cpu_usage) if cpu_usage else 0.0
            summary["avg_system_cpu"][i] = avg_cpu

    # Calculate Average per-type system memory usage
    system_memory_dict = {}
    if run_result["system"]:
        for system_data in run_result["system"]:
            for type, mem_usage in system_data["memory_usage"].items():
                if type not in system_memory_dict:
                    system_memory_dict[type] = []
                if mem_usage is not None:
                    system_memory_dict[type].append(mem_usage)
        for type, mem_usage in system_memory_dict.items():
            avg_mem = statistics.mean(mem_usage) if mem_usage else 0.0
            summary["avg_system_memory"][type] = avg_mem

    process_stats = {}
    if run_result["processes"]:
        for pid, process_info in run_result["processes"].items():
            process_metrics = process_info["metrics"]
            del process_info["metrics"]
            process_stats[pid] = {
                **process_info,
            "avg_cpu_percent": statistics.mean(
                [m["cpu_percent"] for m in process_metrics if m["cpu_percent"] is not None]
            )
            if process_metrics
            else 0.0,
            "avg_memory_percent": statistics.mean(
                [m["memory_percent"] for m in process_metrics if m["memory_percent"] is not None]
            )
            if process_metrics  
            else 0.0,
            "max_num_threads": max(
                [m["num_threads"] for m in process_metrics if m["num_threads"] is not None]
            )
            if process_metrics
            else 0,
        }
        summary["process"] = process_stats

    return summary

#%%

if __name__ == "__main__":
    with open("set_1/run_1/result.json", "r") as f:
        report = json.load(f)

    summary = calculate_run_summary(report)
    print(summary)