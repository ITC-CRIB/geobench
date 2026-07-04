"""Executor factory module."""

from .python import PythonExecutor
from .qgis_process import QGISProcessExecutor
from .qgis_python import QGISPythonExecutor
from .shell import ShellExecutor

_classes = {
    "python": PythonExecutor,
    "qgis-process": QGISProcessExecutor,
    "qgis-python": QGISPythonExecutor,
    "shell": ShellExecutor,
}


def create_executor(scenario: "Scenario") -> "Executor":
    """Return an executor instance for the scenario.

    Args:
        scenario: Scenario.

    Returns:
        Executor instance for the scenario.

    Raises:
        ValueError: If invalid scenario type.
    """
    cls = _classes.get(scenario.type)
    if not cls:
        raise ValueError(f"Invalid scenario type: {scenario.type}")

    return cls(scenario)
