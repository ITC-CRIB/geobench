"""
GeoBench - A benchmarking tool for geospatial operations.
"""

from .benchmark import Benchmark
from .scenario import Scenario

__all__ = ["Benchmark", "Scenario", "benchmark"]


def benchmark(name: str | None = None, **kwargs) -> callable:
    """Create a decorator that benchmarks the execution of a function.

    Args:
        name: Optional name of the benchmark. If None, the name of the decorated function is used.
        **kwargs: Additional keyword arguments passed to the Scenario constructor.

    Returns:
        A decorator that wraps the function and benchmarks its execution.
    """

    def decorator(func):
        def wrapper(*func_args, **func_kwargs):
            arguments = kwargs.pop("arguments", {})
            arguments.update(
                func_kwargs | {key: val for key, val in enumerate(func_args)}
            )

            scenario = Scenario(
                name=name or func.__name__,
                executor="function",
                config={"function": func},
                arguments=arguments,
                **kwargs,
            )

            return scenario.benchmark()

        return wrapper

    return decorator
