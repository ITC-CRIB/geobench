"""Collector module."""

import copy
import importlib
import inspect
import logging
import pkgutil
import subprocess
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import cache, cached_property
from typing import Any, TypeAlias, final

import psutil

logger = logging.getLogger(__name__)


Process: TypeAlias = int | subprocess.Popen | psutil.Process
Operator: TypeAlias = str | Callable[[Any, Any], Any]


@dataclass(frozen=True)
class CollectorMetadata:
    """Metadata describing a collector."""

    code: str
    name: str
    description: str
    config: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class CollectorRule:
    """Rule for combining values in nested data structures."""

    keys: list[str]
    op: Operator

    def _op(self, val: Any, ref_val: Any) -> Any:
        if callable(self.op):
            return self.op(val, ref_val)

        elif self.op == "diff":
            return val - ref_val

        raise ValueError(f"Invalid operator: {self.op}")

    def _apply(self, item: dict, ref_item: dict, idx: int = 0) -> None:
        key = self.keys[idx]
        if key not in item or key not in ref_item:
            raise ValueError(f"Invalid key: {key}")
        parent = item
        item = item[key]
        ref_item = ref_item[key]

        if idx == len(self.keys) - 1:
            if isinstance(item, list) or isinstance(ref_item, list):
                parent[key] = [
                    self._op(val, ref_val)
                    for val, ref_val in zip(item, ref_item, strict=True)
                ]
            else:
                parent[key] = self._op(item, ref_item)

        elif isinstance(item, list) or isinstance(ref_item, list):
            for val, ref_val in zip(item, ref_item, strict=True):
                self._apply(val, ref_val, idx + 1)
        else:
            self._apply(item, ref_item, idx + 1)

    @classmethod
    def get_rules(cls, rules: dict) -> list["CollectorRule"]:
        """Create collector rules from a configuration dictionary.

        Args:
            rules: Rule configuration.

        Returns:
            List of collector rules.
        """
        out = []
        for key, val in rules.items():
            args = {"keys": key.split(":")}
            if isinstance(val, dict):
                args.update(val)
            else:
                args["op"] = val
            out.append(cls(**args))
        return out

    @classmethod
    def apply_rules(cls, data: list[dict], rules: dict | list["CollectorRule"]) -> dict:
        """Apply the rule to the given data."""
        if not data:
            return

        rules = cls.get_rules(rules) if isinstance(rules, dict) else rules

        refs = {}
        for rule in rules:
            if rule.op == "diff":
                key = rule.keys[0]
                refs[key] = copy.deepcopy(data[0][key])

        for rule in rules:
            for i in range(len(data) - 1, -1, -1):
                rule._apply(data[i], data[0], 0)

        return refs


class Collector(ABC):
    """Abstract base class for collectors."""

    def __init__(self, config: dict | None = None):
        """Initialize the collector.

        Args:
            config: Optional collector configuration.
        """
        self.config = self.get_config(config or {})
        self._data = []

    @classmethod
    @abstractmethod
    def get_metadata(cls) -> CollectorMetadata:
        """Return metadata describing the collector."""

    def get_config(self, config: dict[str, Any]) -> dict[str, Any]:
        """Validate and return collector configuration.

        Args:
            config: Collector configuration parameters.

        Returns:
            Validated collector configuration.
        """
        keys = self.metadata.config.keys()
        for key in config:
            if key not in keys:
                raise ValueError(f"Invalid configuration parameter: {key}")

        return config

    def is_supported(self) -> bool:
        """Determine whether the collector is supported."""
        return True

    @final
    @cached_property
    def supported(self) -> bool:
        """Return whether the collector is supported."""
        return self.is_supported()

    @final
    @cached_property
    def metadata(self) -> CollectorMetadata:
        """Return collector metadata."""
        return self.get_metadata()

    @final
    @cached_property
    def code(self) -> str:
        """Return the unique collector identifier."""
        return self.metadata.code

    @abstractmethod
    def _collect(self) -> dict:
        """Collect a data sample.

        Returns:
            Collected data sample.
        """

    @final
    def collect(self) -> None:
        """Collect and store a data sample."""
        self._data.append((time.time(), self._collect()))

    @abstractmethod
    def _process(self, sample: Any) -> dict:
        """Process a collected data sample.

        Args:
            sample: Collected data sample.

        Returns:
            Processed data sample.
        """

    def _postprocess(self, data: list[dict]) -> dict:
        """Postprocess a data series containing processed samples.

        Args:
            data: Data series containing processed samples.

        Returns:
            Reference data for the processed samples.
        """
        return {}

    def _clean(self, item: dict) -> None:
        """Remove empty data item entries recursively.

        Args:
            item: Data item to clean.
        """
        remove = []
        for key, val in item.items():
            if val is None or (isinstance(val, list) and len(val) == 0):
                remove.append(key)
            elif isinstance(val, dict):
                self._clean(val)
                if not val:
                    remove.append(key)
            elif isinstance(val, list):
                for subval in val:
                    if isinstance(subval, dict):
                        self._clean(subval)
        for key in remove:
            del item[key]

    @final
    def get_data(self) -> tuple[list[dict], dict]:
        """Return processed and cleaned data series and postprocessing references."""
        data = [
            self._process(sample) | {"timestamp": timestamp}
            for timestamp, sample in self._data
        ]

        refs = self._postprocess(data) or {}

        for item in data:
            self._clean(item)
        self._clean(refs)

        self._data = []

        return data, refs


class SystemCollector(Collector):
    """Abstract base class for system collectors."""


class ProcessCollector(Collector):
    """Abstract base class for process collectors."""

    def __init__(self, process: Process, config: dict | None = None):
        """Initialize the process collector.

        Args:
            process: Related process.
            config: Optional collector configuration.
        """
        super().__init__(config)

        self.process = get_process(process)


@cache
def get_collectors() -> dict[str, type[Collector]]:
    """Return dictionary of available collector classes."""
    collectors = {}

    for _, name, _ in pkgutil.iter_modules([__path__[0]]):
        module = importlib.import_module(f".{name}", f"{Collector.__module__}")
        for name, cls in inspect.getmembers(module, inspect.isclass):
            if issubclass(cls, Collector) and cls is not Collector:
                if not cls.__abstractmethods__:
                    code = cls.get_metadata().code
                    collectors[code] = cls
                else:
                    logger.debug("%s has abstract methods, skipping", cls)

    return collectors


def get_collector(
    code: str, config: dict | None = None, process: Process | None = None
) -> Collector:
    """Return collector with the specified code and configuration.

    Args:
        code: Collector code.
        config: Optional configuration.
        process: Optional process.

    Returns:
        Collector with the specified code and configuration.

    Raises:
        ValueError: If invalid collector code.
    """
    collector = get_collectors().get(code)

    if not collector or (issubclass(collector, ProcessCollector) and not process):
        raise ValueError(f"Invalid collector code: {code}")

    if issubclass(collector, ProcessCollector):
        return collector(process, config)

    return collector(config)


def get_process(process: Process) -> psutil.Process:
    """Return standard process.

    Raises:
        TypeError: If invalid process.
    """
    if isinstance(process, psutil.Process):
        return process

    if isinstance(process, subprocess.Popen):
        pid = process.pid

    elif isinstance(process, int):
        pid = process

    else:
        raise TypeError(f"Invalid process: {process}")

    return psutil.Process(pid)
