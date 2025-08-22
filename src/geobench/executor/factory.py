from .shell import ShellExecutor
from .python import PythonExecutor
from .qgis_process import QGISProcessExecutor
from .qgis_python import QGISPythonExecutor


_classes = {
    'shell': ShellExecutor,
    'python': PythonExecutor,
    'qgis-process': QGISProcessExecutor,
    'qgis-python': QGISPythonExecutor,
}


def create_executor(scenario: 'Scenario') -> 'Executor':
    """Returns an executor object for the scenario.

    Args:
        scenario (Scenario): Scenario object.

    Returns:
        Executor object for the scenario.
    """
    cls = _classes.get(scenario.type)
    if not cls:
        raise ValueError("Invalid scenario type.", scenario.type)

    return cls(scenario)
