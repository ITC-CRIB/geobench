"""
GeoBench - A benchmarking tool for geospatial operations.
"""

from .jupyter import Geobench

__all__ = ["Geobench", "geobench"]


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
