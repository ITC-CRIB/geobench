"""Benchmark module."""

import copy
import json
import logging
import os
import shutil
import threading
import time
from collections.abc import Callable

from .cache import clear_cache
from .monitor import Monitor
from .utils import get_abs_path

logger = logging.getLogger(__name__)


class Benchmark:
    """Benchmark class."""

    def __init__(
        self,
        wait: float = 5.0,
        monitor: float | None = None,
        telemetry: dict | None = None,
        inputs: list | None = None,
        outputs: list | None = None,
        archive: str = "output",
        clear_outdir: bool = False,
        clear_outputs: bool = True,
        clear_cache: bool = True,
        workdir: str | None = None,
        basedir: str | None = None,
        outdir: str | None = None,
        metadata: dict | None = None,
    ):
        """Initialize benchmark.

        Args:
            wait: Idle wait time before the run, in seconds.
            monitor: Monitoring duration before and after the run, in seconds.
            telemetry: Optional telemetry configuration.
            inputs: Optional list of input files.
            outputs: Optional list of output files.
            archive: File types to archive. Options are 'none', 'both', 'input', 'output'.
            clear_outdir: If True, clear the output directory before the run.
            clear_outputs: If True, clear output files at the end of the run.
            clear_cache: If True, clear system caches before the run.
            workdir: Working directory path. It is also used as the root path of the input files.
                Defaults to the current working directory.
            basedir: Base directory path. It is used as the root path of the output directory, if is it not an absolute path.
                Defaults to the current working directory.
            outdir: Output directory path. Defaults to 'benchmark'.
            metadata: Optional metadata.

        """
        self.wait = wait or 0.0
        self.monitor = monitor
        self.telemetry = self.get_telemetry(telemetry, duration=monitor)
        self.archive = archive or "none"
        self.clear_outdir = clear_outdir
        self.clear_outputs = clear_outputs
        self.clear_cache = clear_cache
        self.metadata = metadata or {}

        self.workdir = get_abs_path(workdir)
        if not os.path.isdir(self.workdir):
            raise ValueError(f"Invalid working directory: {workdir}")

        self.basedir = get_abs_path(basedir)
        if not os.path.isdir(self.basedir):
            raise ValueError(f"Invalid base directory: {basedir}")

        self.outdir = get_abs_path(outdir or "benchmark", root=self.basedir)

        self.inputs = [get_abs_path(path, self.workdir) for path in inputs or []]
        self.outputs = [get_abs_path(path, self.workdir) for path in outputs or []]

        self.result = None

    @classmethod
    def get_default_telemetry(cls) -> dict:
        """Return default telemetry."""
        return {
            "init": {
                "collectors": ["system_info"],
            },
            "baseline": {
                "duration": 5.0,
                "interval": 1.0,
                "collectors": ["system_metrics"],
            },
            "main": {
                "interval": 1.0,
                "collectors": ["process_metrics"],
            },
            "endline": {
                "duration": 5.0,
                "interval": 1.0,
                "collectors": ["system_metrics"],
            },
            "wrap": {
                "collectors": ["system_metrics", "system_processes"],
            },
        }

    @classmethod
    def get_telemetry(
        cls, telemetry: dict | None = None, duration: float | None = None
    ) -> dict:
        """Return customized telemetry considering default telemetry.

        Args:
            telemetry: Custom telemetry.
            duration: Optional monitoring duration, in seconds.

        Returns:
            Customized telemetry.
        """
        out = cls.get_default_telemetry()

        for key, val in (telemetry or {}).items():
            if key not in out:
                out[key] = val
            else:
                out[key] |= val

        if duration is not None:
            for key, val in out.items():
                if "duration" in val:
                    val["duration"] = duration

        return out

    @classmethod
    def get_related_files(cls, path: str) -> list[str]:
        """Return paths of the related files.

        Args:
            path: Path of the reference file.

        Returns:
            Paths of related files, including the reference file.
        """
        paths = [path]

        base, ext = os.path.splitext(path)
        if ext == ".shp":
            for ext in [
                ".cpg",
                ".dbf",
                ".prj",
                ".sbn",
                ".sbx",
                ".shp.xml",
                ".shx",
            ]:
                paths.append(base + ext)

        return paths

    def _save(self):
        """Save benchmarking results."""
        path = os.path.join(self.outdir, "result.json")
        with open(path, "w", encoding="utf-8") as file:
            json.dump(self.result, file, ensure_ascii=False, indent=2)

    def _save_files(self, files: list[str]):
        """Save files in the output directory, including the related files."""
        for file in files:
            if not os.path.exists(file):
                logger.debug("File not found: %s", file)
                continue
            logger.info("Archiving file: %s", file)
            for related_file in self.get_related_files(file):
                if not os.path.exists(related_file):
                    logger.debug("Related file not found: %s", related_file)
                    continue
                try:
                    shutil.copy(related_file, self.outdir)
                except shutil.SameFileError:
                    pass
                except OSError as err:
                    logger.error(
                        "Error copying output file %s to %s: %s",
                        related_file,
                        self.outdir,
                        err,
                    )

    def _remove_files(self, files: list[str]):
        """Remove files and their related files."""
        for file in files:
            if not os.path.exists(file):
                logger.debug("File not found: %s", file)
                continue
            logger.info("Removing file: %s", file)
            for related_file in self.get_related_files(file):
                if not os.path.exists(related_file):
                    logger.debug("Related file not found: %s", file)
                    continue
                try:
                    os.remove(related_file)
                except OSError as err:
                    logger.error("Error removing file %s: %s", related_file, err)

    def start(self, process_factory: Callable | None = None):
        """Start benchmarking.

        The following operations are performed:
            - Set up output directory.
            - Collect and save initial information.
            - Clear output files*
            - Clear system caches*.
            - Idle wait*.
            - Perform and save baseline monitoring*.
            - Start process to be monitored*.
            - Start monitors.

        Args:
            process_factory: Optional callback to create process to be monitored.
        """
        self.result = copy.deepcopy(self.metadata)

        # Set up output directory
        print(f"Setting up output directory: {self.outdir}")
        if os.path.exists(self.outdir):
            if os.path.isdir(self.outdir):
                if not self.clear_outdir:
                    raise RuntimeError("Output directory exists")
                else:
                    logger.debug("Removing existing output directory: %s", self.outdir)
                    shutil.rmtree(self.outdir)
            else:
                raise RuntimeError("Invalid output directory")
        logger.debug("Creating output directory: %s", self.outdir)
        os.makedirs(self.outdir)

        # Store initial information
        print("Storing initial information.")
        self.result["init"] = {}
        for collector in self.telemetry.get("init", {}).get("collectors", []):
            collector = Monitor.get_collector(collector)
            collector.collect()
            data, refs = collector.get_data()
            self.result["init"][collector.code] = {
                "refs": refs,
                "data": data,
            }
        self._save()

        # Clear output files, if required
        if self.clear_outputs:
            print("Clearing output files")
            self._remove_files(self.outputs)

        # Clear system caches, if required
        if self.clear_cache:
            print("Clearing system caches.")
            clear_cache()

        # Idle wait, if required
        if self.wait:
            print(f"Waiting for {self.wait} s.")
            time.sleep(self.wait)

        # Perform baseline monitoring, if required
        baseline = self.telemetry.get("baseline", {})
        duration = (
            self.monitor if self.monitor is not None else baseline.get("duration")
        )
        if baseline and duration:
            print(f"Baseline monitoring for {duration} s.")
            monitor = Monitor(
                name="baseline",
                collectors=baseline.get("collectors", []),
                duration=duration,
                interval=baseline.get("interval"),
            )
            monitor.run()
            self.result["baseline"] = monitor.get_data()
            self._save()

        # Collect initial information of wrappers, if required
        self.wrappers = []
        if self.telemetry.get("wrap"):
            print("Collecting initial information of wrappers.")
            for item in self.telemetry["wrap"].get("collectors", []):
                self.wrappers.append(Monitor.get_collector(item))
            for collector in self.wrappers:
                collector.collect()

        # Start monitors
        print("Starting monitoring.")

        self.monitors = []
        self.stop_event = threading.Event()

        self.result["pid"] = process_factory() if process_factory else os.getpid()

        for code, item in self.telemetry.items():
            if code in ["init", "wrap", "baseline", "endline"]:
                continue
            monitor = Monitor(
                name=code,
                collectors=item.get("collectors", []),
                interval=item.get("interval"),
                process=self.result["pid"],
                stop_event=self.stop_event,
            )
            self.monitors.append(monitor)
            monitor.start()

    def stop(self):
        """Stop benchmarking.

        The following operations are performed:
            - Stop all monitors.
            - Collect final information of the wrappers*.
            - Get results of all monitors.
            - Save the results.
            - Perform endline monitoring*.
            - Store input files*.
            - Store output files*.
            - Clear output files*.
        """
        print("Stopping monitoring.")

        # Signal all monitors to stop
        self.stop_event.set()

        # Wait for all monitors to finish
        for monitor in self.monitors:
            monitor.join(timeout=monitor.interval)

        # Collect final information of wrappers, if required
        if self.wrappers:
            print("Collecting final information of wrappers.")
            self.result["wrap"] = {}
            for collector in self.wrappers:
                collector.collect()
                data, refs = collector.get_data()
                self.result["wrap"][collector.code] = {
                    "refs": refs,
                    "data": data,
                }

        # Aggregate results from all monitors
        for monitor in self.monitors:
            self.result[monitor.name] = monitor.get_data()

        # Save results
        self._save()

        # Perform endline monitoring, if required
        endline = self.telemetry.get("endline", {})
        duration = self.monitor if self.monitor is not None else endline.get("duration")
        if endline and duration:
            print(f"Endline monitoring for {duration} s.")
            monitor = Monitor(
                name="endline",
                collectors=endline.get("collectors", []),
                duration=duration,
                interval=endline.get("interval"),
            )
            monitor.run()
            self.result["endline"] = monitor.get_data()
            self._save()

        # Store input files in the output directory, if required
        if self.archive in ["both", "input"]:
            print("Saving input files")
            self._save_files(self.inputs)

        # Store output files in the output directory, if required
        if self.archive in ["both", "output"]:
            print("Saving output files")
            self._save_files(self.outputs)

        # Clear output files, if required
        if self.clear_outputs:
            print("Clearing output files")
            self._remove_files(self.outputs)
