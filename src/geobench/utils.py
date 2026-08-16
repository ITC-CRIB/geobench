import argparse
import ast
from typing import Any


class KeyValueAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        values = getattr(namespace, self.dest, None) or {}
        key, value = values.split("=", 1)
        values[key] = value
        setattr(namespace, self.dest, values)


class ConfigOptionAction(argparse.Action):
    """Parse and combine repeated key=value configuration options."""

    def __init__(
        self,
        option_strings: list[str],
        dest: str,
        nargs: str | int | None = None,
        **kwargs: Any,
    ) -> None:
        kwargs.setdefault("default", {})
        super().__init__(option_strings, dest, nargs, **kwargs)
        self._values: dict[Any, set[Any]] = {}

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        value: str,
        option_string: str | None = None,
    ) -> None:
        try:
            key, val = value.split("=", 1)
        except ValueError:
            raise argparse.ArgumentError(self, "argument must be in key=value format")

        try:
            val = ast.literal_eval(val)
        except ValueError:
            pass
        except SyntaxError:
            raise argparse.ArgumentError(self, "value must be a valid literal")

        try:
            key = int(key)
        except ValueError:
            pass

        values = self._values.setdefault(key, set())

        if isinstance(val, (list, tuple, set)):
            values.update(val)
        else:
            values.add(val)

        setattr(
            namespace,
            self.dest,
            {key: sorted(values) for key, values in self._values.items()},
        )
