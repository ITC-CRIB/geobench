from typing import Any, Callable
import json
import os
import statistics
import threading
import time
import traceback

import psutil

from .cache import clear_cache
from .monitor import get_system_info, monitor_process, monitor_system
from .report import calculate_run_summary, generate_html_report

import logging

logger = logging.getLogger(__name__)


class Geobench:
    """Class for benchmarking code execution in Jupyter notebooks."""

    def __init__(
        self,
        name: str,
        outdir: str = None,
        run_wait: float = 2.0,
        run_monitor: float = 2.0,
        system_monitor: float = 2.0,
        clean: bool = False,
    ):
        """Initialize the JupyterBenchmark.

        Args:
            name (str): Benchmark name (used for output directory).
            outdir (str): Output directory path (default = generated from name).
            run_wait (float): Idle wait time before and after each run (s) (default = 2.0)
            run_monitor (float): Monitoring time before and after each run (s) (default = 2.0).
            system_monitor (float): Monitoring time before and after all runs (s) (default = 2.0)
            clean (bool): Set True to clean the output directory, if exists.
        """
        self.name = name
        self.run_wait = run_wait
        self.run_monitor = run_monitor
        self.system_monitor = system_monitor

        self._stop_event = threading.Event()  # Replace is_monitoring

        cwd = os.getcwd()

        if outdir is None:
            import re

            outdir = re.sub(r"-+", "-", re.sub(r"[^\w-]", "-", name.lower())).strip("-")

        self.outdir = outdir if os.path.isabs(outdir) else os.path.join(cwd, outdir)

        # Setup output directory
        if os.path.exists(self.outdir):
            if os.path.isdir(self.outdir):
                if clean:
                    logger.debug("Removing existing output directory: %s", self.outdir)
                    import shutil

                    shutil.rmtree(self.outdir)
                    os.makedirs(self.outdir)
                # If not clean, we'll keep using the existing directory
            else:
                raise ValueError(f"Invalid output directory: {self.outdir}")
        else:
            os.makedirs(self.outdir)

        self.result = {
            "run": name,
            "start_time": None,
            "end_time": None,
            "system": None,
            "baseline": None,
            "endline": None,
            "runs": [],
        }

        self._current_run = None
        self._save_result()

    def _save_result(self):
        """Save current result to the output directory."""
        result_path = os.path.join(self.outdir, "result.json")
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(self.result, f, ensure_ascii=False, indent=2)

    def _monitor_while_running(self, process):
        out = monitor_process(
            process=process,
            stop_event=self._stop_event,  # Pass the threading.Event
        )
        self._current_run.update(out)

    def start(self, run_name: str = None):
        """Start benchmarking.

        Args:
            run_name (str, optional): Name for this run. If not provided, will be auto-generated.

        Returns:
            self: For method chaining.
        """
        self._stop_event.clear()  # Reset the event
        if self._current_run is not None:
            logger.warning("Already in a benchmark run, call finish() first")
            return self

        if run_name is None:
            run_name = f"run_{len(self.result['runs']) + 1}"

        print(f"Starting benchmark: {run_name}")

        # Create run directory
        run_dir = os.path.join(self.outdir, run_name.replace(" ", "_").lower())
        os.makedirs(run_dir, exist_ok=True)

        # Store system information only at first run
        if self.result["system"] is None:
            print("Storing system information.")
            self.result["system"] = get_system_info()
            self._save_result()

        # Perform system cleanup
        print("Clearing system caches.")
        clear_cache()

        # Record first run start
        if self.result["start_time"] is None:
            self.result["start_time"] = time.time()

        # Idle wait before the run, if required
        if self.run_wait:
            print(f"Waiting {self.run_wait} s before the run.")
            time.sleep(self.run_wait)

        # Create run data structure
        self._current_run = {
            "run": run_name,
            "directory": run_dir,
            "start_time": time.time(),
            "success": False,
            "system": [],
            "processes": {},
            "arguments": {},  # Can be set manually by user if needed
            "pid": os.getpid(),  # Store the current process ID
        }

        # Perform baseline monitoring before the run, if required
        if self.run_monitor:
            print(f"Baseline monitoring for {self.run_monitor} s.")
            self._current_run["baseline"] = monitor_system(self.run_monitor)

        # Set up and start the process monitoring in a background thread
        current_process = psutil.Process()
        self._monitoring_thread = threading.Thread(
            target=self._monitor_while_running, args=(current_process,)
        )
        self._monitoring_thread.start()

        print("Process monitoring started.")

        # Store partial run data
        run_path = os.path.join(run_dir, "result.json")
        with open(run_path, "w", encoding="utf-8") as f:
            json.dump(self._current_run, f, ensure_ascii=False, indent=2)

        return self

    def stop(self, success: bool = True):
        """Finish benchmarking.

        Args:
            success (bool): Whether the benchmark run was successful.

        Returns:
            dict: Summary of the run results.
        """
        if self._current_run is None:
            logger.warning("No benchmark run in progress, call start() first")
            return {}

        self._stop_event.set()  # Signal to stop
        self._monitoring_thread.join(timeout=2.0)
        print("Process monitoring stopped.")

        # Set success status and end time if not already set
        self._current_run["end_time"] = time.time()
        self._current_run["success"] = success
        self._current_run["finished"] = True

        # Idle wait after the run, if required
        if self.run_wait:
            print(f"Waiting {self.run_wait} s after the run.")
            time.sleep(self.run_wait)

        # Perform endline monitoring after the run, if required
        if self.run_monitor:
            print(f"Endline monitoring for {self.run_monitor} s.")
            self._current_run["endline"] = monitor_system(self.run_monitor)

        # Store run data in run directory
        run_path = os.path.join(self._current_run["directory"], "result.json")
        with open(run_path, "w", encoding="utf-8") as f:
            json.dump(self._current_run, f, ensure_ascii=False, indent=2)

        # Calculate run summary and append to results
        run_summary = calculate_run_summary(self._current_run)
        summary_path = os.path.join(self._current_run["directory"], "summary.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(run_summary, f, ensure_ascii=False, indent=2)

        # Update overall results
        self.result["runs"].append(self._current_run)
        if (
            self.result["end_time"] is None
            or self.result["end_time"] < self._current_run["end_time"]
        ):
            self.result["end_time"] = self._current_run["end_time"]

        # If this is the last run, perform final system monitoring
        if self.system_monitor:
            if self.result["baseline"] is None:
                self.result["baseline"] = monitor_system(self.system_monitor)
            self.result["endline"] = monitor_system(self.system_monitor)

        self._save_result()

        # Get run results and reset current run
        run_result = self._current_run
        self._current_run = None

        print(
            f"Benchmark completed in {run_result['end_time'] - run_result['start_time']:.2f} s."
        )

        return run_summary

    def benchmark(self, func: Callable, *args, **kwargs) -> Any:
        """Run a function with benchmarking.

        Args:
            func (callable): The function to benchmark.
            *args: Arguments to pass to the function.
            **kwargs: Keyword arguments to pass to the function.

        Returns:
            Any: The return value of the function.
        """
        # Start benchmarking (this will start the monitoring thread)
        self.start(getattr(func, "__name__", "function_call"))

        # Run the function (monitoring is already happening from start())
        try:
            print("Executing the function with process monitoring.")

            # Execute the function
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()

            # Update timing information
            self._current_run["function_start_time"] = start_time
            self._current_run["function_end_time"] = end_time

            success = True

        except Exception as err:
            logger.error("Error during benchmark: %s", err)
            traceback.print_exc()
            result = None
            success = False

        # Finish benchmarking (this will stop the monitoring thread)
        self.stop(success)

        self.generate_report()

        return result

    def generate_report(self):
        """Generate HTML report for all benchmark runs.

        Returns:
            str: Path to the generated report.
        """
        # Prepare set summary data structure expected by generate_html_report
        set_summaries = []

        # Group runs by their set (assuming each run is its own set for now)
        for i, run in enumerate(self.result["runs"]):
            set_id = i + 1
            run_summaries = [calculate_run_summary(run)]

            # Calculate statistics for the set
            total_runs = len(run_summaries)
            success_rate = (
                (
                    sum(1 for run_summary in run_summaries if run_summary["success"])
                    / total_runs
                )
                if total_runs > 0
                else 0
            )

            # Calculate average and standard deviation of execution time for all runs in a set
            run_time_list = [
                run_summary["run_time"]
                for run_summary in run_summaries
                if "run_time" in run_summary
            ]
            avg_run_time = statistics.mean(run_time_list) if run_time_list else 0
            stdev_run_time = (
                statistics.stdev(run_time_list) if len(run_time_list) > 1 else 0
            )

            set_summary = {
                "set": set_id,
                "arguments": run.get("arguments", {}),
                "total": total_runs,
                "success": success_rate,
                "avg_run_time": avg_run_time,
                "stdev_run_time": stdev_run_time,
                "runs": run_summaries,
            }
            set_summaries.append(set_summary)

        # Generate HTML report
        report_path = os.path.join(self.outdir, "report.html")
        generate_html_report(
            system_data=self.result,
            set_summaries=set_summaries,
            output_path=report_path,
        )

        return report_path


def geobench(name: str | None = None, **kwargs) -> callable:
    """Create a decorator that benchmarks the execution of a function.

    Args:
        name: Optional name of the benchmark. If None, the name of the decorated function is used.
        **kwargs: Additional keyword arguments passed to the Geobench constructor.

    Returns:
        A decorator that wraps the function and benchmarks its execution.
    """

    def decorator(func):
        bench = Geobench(name or func.__name__, **kwargs)

        def wrapper(*args, **kwargs):
            return bench.benchmark(func, *args, **kwargs)

        return wrapper

    return decorator
