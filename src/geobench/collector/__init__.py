"""Collector module."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import cache, cached_property
from typing import TypeAlias
import importlib
import inspect
import operator
import pkgutil
import subprocess

import psutil

import logging

logger = logging.getLogger(__name__)


Process: TypeAlias = int | subprocess.Popen | psutil.Process


@dataclass(frozen=True)
class CollectorInfo:
    """Metadata describing a collector."""

    code: str
    name: str
    description: str


class Collector(ABC):
    """Abstract base class for collectors."""

    def __init__(self, config: dict | None = None):
        """Initialize collector."""
        self.config = config or {}

    @classmethod
    @abstractmethod
    def get_info(cls) -> CollectorInfo:
        """Return collector information."""

    @cached_property
    def code(self) -> str:
        return self.get_info().code

    @abstractmethod
    def collect(self) -> dict:
        """Collect data.

        Returns:
            Dictionary containing collected data.
        """

    @classmethod
    def clean_dict(cls, item: dict):
        """Clean empty data item attributes recursively.

        Args:
            item: Data item to be cleaned.
        """
        remove = []
        for key, val in item.items():
            if val is None or val == -1 or (isinstance(val, list) and len(val) == 0):
                remove.append(key)
            elif isinstance(val, dict):
                cls.clean_dict(val)
                if not val:
                    remove.append(key)
            elif isinstance(val, list):
                for subval in val:
                    if isinstance(subval, dict):
                        cls.clean_dict(subval)
        for key in remove:
            del item[key]

    @classmethod
    def reduce(cls, data: list[dict], opts: dict):
        """Reduce collected data.

        Args:
            data: Collected data.
            opts: Reduction options.
        """
        ops = {
            "diff": operator.sub,
        }

        def _apply(lhs: dict, rhs: dict, rule: dict, idx: int = 0):
            if not isinstance(lhs, dict):
                raise ValueError("Invalid left operand")
            if not isinstance(rhs, dict):
                raise ValueError("Invalid right operand")

            keys = rule["keys"]
            key = keys[idx]
            if key not in lhs or key not in rhs:
                raise ValueError(f"Invalid key: {key}")
            parent = lhs
            lhs = lhs[key]
            rhs = rhs[key]

            if idx == len(keys) - 1:
                if callable(rule["op"]):
                    val = rule["op"](lhs, rhs)
                elif rule["op"] == "pair":
                    val = [rhs, lhs]
                elif rule["op"] == "mean":
                    val = (rhs + lhs) / 2
                else:
                    raise ValueError(f"Invalid operator: {rule['op']}")
                parent[key] = val

            elif isinstance(lhs, list) or isinstance(rhs, list):
                for lval, rval in zip(lhs, rhs, strict=True):
                    _apply(lval, rval, rule, idx + 1)
            else:
                _apply(lhs, rhs, rule, idx + 1)

        if len(data) < 2:
            data.clear()
            return

        rules = []
        for key, val in opts.items():
            rule = {"keys": key.split(":")}
            if isinstance(val, dict):
                rule.update(val)
            else:
                rule["op"] = val
            if rule["op"] in ops:
                rule["op"] = ops[rule["op"]]
            rules.append(rule)

        first = prev = data.pop(0)
        for item in data:
            for rule in rules:
                _apply(item, prev, rule)
            prev = item

        return first

    def process_item(self, item: dict):
        """Process collected data item.

        Args:
            item: Data item to be processed.
        """
        self.clean_dict(item)

    def process_data(self, data: list[dict]) -> dict:
        """Process collected data.

        Args:
            data: Collected data.

        Returns:
            Additional data generated during processing.
        """
        for item in data:
            self.process_item(item)

        return {}


class SystemCollector(Collector):
    """Abstract base class for system collectors."""


class ProcessCollector(Collector):
    """Abstract base class for process collectors."""

    def __init__(self, process: Process, config: dict | None = None):
        """Initialize process collector."""
        super().__init__(config)

        self.process = get_process(process)


@cache
def get_collectors() -> dict[str, Collector]:
    """Return dictionary of available collectors."""
    collectors = {}

    for _, name, _ in pkgutil.iter_modules([__path__[0]]):
        module = importlib.import_module(f".{name}", f"{Collector.__module__}")
        for name, cls in inspect.getmembers(module, inspect.isclass):
            if issubclass(cls, Collector) and cls is not Collector:
                if not cls.__abstractmethods__:
                    code = cls.get_info().code
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
        ValueError: If invalid collector type.
    """
    collector = get_collectors().get(code)

    if not collector or (issubclass(collector, ProcessCollector) and not process):
        raise ValueError(f"Invalid collector type: {type}")

    if issubclass(collector, ProcessCollector):
        return collector(process, config)

    return collector(config)


def get_process(process: Process) -> psutil.Process:
    """Return standard process."""
    if isinstance(process, psutil.Process):
        return process

    if isinstance(process, subprocess.Popen):
        id = process.pid

    elif isinstance(process, int):
        id = process

    else:
        raise ValueError(f"Invalid process: {process}")

    return psutil.Process(id)
