"""Command line interface module."""

from typing import Any
import argparse
import ast
import json
import os

from .executor import get_executors
from .executor.program import ProgramExecutor
from .scenario import Scenario, load_scenario

import logging

logger = logging.getLogger(__name__)


class ArgumentDefaultsHelpFormatterNoNone(argparse.ArgumentDefaultsHelpFormatter):
    """Argument help formatter that omits empty default values."""

    def _get_help_string(self, action):
        if action.default is None:
            return action.help
        return super()._get_help_string(action)


def parse_dict(val: str) -> dict:
    """Parse a dictionary argument from a JSON or Python literal string.

    Attempts to parse the input as JSON first. If JSON parsing fails,
    falls back to parsing a Python literal (e.g., using single quotes).
    """
    try:
        return json.loads(val)

    except json.JSONDecodeError:
        return ast.literal_eval(val)


def parse_key_value(val: str) -> tuple[str, Any]:
    """Parse a key=value argument from a string."""
    try:
        key, val = val.split("=", 1)
    except ValueError:
        raise argparse.ArgumentTypeError("Argument must be in key=value format")

    try:
        val = ast.literal_eval(val)
    except (ValueError, SyntaxError):
        raise argparse.ArgumentTypeError("Value must be a literal")

    try:
        key = int(key)
    except ValueError:
        pass

    return key, val


def merge_args(args: dict | None = None, arg_items: list | None = None) -> dict:
    """Merge argument values from combined and separate representations."""
    args = args.clone() if args else {}
    for key, val in arg_items or []:
        if key not in args:
            args[key] = set()
        if isinstance(val, tuple):
            args[key].update(val)
        else:
            args[key].add(val)
    args = {key: list(val) for key, val in args.items() if isinstance(val, set)}
    return args


class CLI:
    """Command line interface class."""

    def __init__(self):
        """Initialize command line interface object."""

        self.parser = argparse.ArgumentParser(
            description="Benchmarking toolkit for geospatial processing workflows.",
            formatter_class=ArgumentDefaultsHelpFormatterNoNone,
        )
        self.parser.add_argument(
            "-t",
            "--type",
            type=str,
            choices=[
                id
                for id, executor in get_executors().items()
                if issubclass(executor, ProgramExecutor)
            ],
            help="Scenario type",
            default="shell",
        )
        self.parser.add_argument(
            "-n",
            "--name",
            type=str,
            help="Scenario name",
        )
        self.parser.add_argument(
            "-r",
            "--repeat",
            type=int,
            help="Number of repeats",
            default=1,
        )
        self.parser.add_argument(
            "-i",
            "--input",
            type=parse_key_value,
            action="append",
            help="Input file (can be repeated)",
        )
        self.parser.add_argument(
            "-o",
            "--output",
            type=parse_key_value,
            action="append",
            help="Output file (can be repeated)",
        )
        self.parser.add_argument(
            "--inputs",
            type=str,
            nargs="+",
            help="List of input files",
        )
        self.parser.add_argument(
            "--outputs",
            type=str,
            nargs="+",
            help="List of output files",
        )
        self.parser.add_argument(
            "-a",
            "--arg",
            type=parse_key_value,
            action="append",
            help="Argument as key=value (can be repeated)",
        )
        self.parser.add_argument(
            "--arguments",
            type=parse_dict,
            help="Dictionary of arguments",
        )
        self.parser.add_argument(
            "-w",
            "--wait",
            type=float,
            help="Wait time before and after in seconds.",
            default=2.0,
        )
        self.parser.add_argument(
            "-m",
            "--monitor",
            type=float,
            help="Monitor time before and after in seconds.",
            default=2.0,
        )
        self.parser.add_argument(
            "-rw",
            "--run-wait",
            type=float,
            help="Wait time before and after each run in seconds (default: wait time)",
        )
        self.parser.add_argument(
            "-rm",
            "--run-monitor",
            type=float,
            help="Monitoring time before and after each run in seconds (default: monitor time)",
        )
        self.parser.add_argument(
            "-sw",
            "--system-wait",
            type=float,
            help="Wait time before and after all runs in seconds (default: wait time)",
        )
        self.parser.add_argument(
            "-sm",
            "--system-monitor",
            type=float,
            help="Monitoring time before and after all runs in seconds (default: monitor time)",
        )
        self.parser.add_argument(
            "--archive",
            type=str,
            choices=["none", "both", "input", "output"],
            help="File types to archive",
            default="both",
        )
        self.parser.add_argument(
            "--workdir",
            type=str,
            help="Working directory (default: current working directory)",
        )
        self.parser.add_argument(
            "--basedir",
            type=str,
            help="Base directory (default: current working directory)",
        )
        self.parser.add_argument(
            "--outdir",
            type=str,
            help="Output directory (default: autogenerated from the scenario name)",
        )
        self.parser.add_argument(
            "--venv",
            type=str,
            help="Virtual environment path",
        )
        self.parser.add_argument(
            "-c",
            "--clean",
            action="store_true",
            help="Clean the output directory",
        )
        self.parser.add_argument(
            "--clean-outputs",
            action="store_true",
            help="Clean the output files"
        )
        self.parser.add_argument(
            "-d",
            "--debug",
            action="store_true",
            help="Enable debug mode",
        )
        self.parser.add_argument(
            "command",
            type=str,
            help="Scenario filename or command",
        )
        self.parser.add_argument(
            "args",
            type=str,
            nargs=argparse.REMAINDER,
            help="Shell command arguments",
        )

    def run(self):
        """Run command line interface."""
        args = self.parser.parse_args()

        if args.debug:
            logging.basicConfig(
                level=logging.DEBUG,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            )

            for name in logging.root.manager.loggerDict:
                if name.startswith("geobench"):
                    logging.getLogger(name).setLevel(logging.DEBUG)

            logger.debug("Debugging enabled")
        else:
            logging.basicConfig(
                level=logging.INFO, format="%(levelname)s - %(message)s"
            )

        kwargs = {
            key: val
            for key, val in vars(args).items()
            if val is not None
            and key
            not in ["command", "arg", "args", "input", "output", "clean", "debug"]
        }

        kwargs["arguments"] = merge_args(
            kwargs.get("arguments"), (args.arg or []) + list(enumerate(args.args or []))
        )
        kwargs["inputs"] = merge_args(kwargs.get("inputs"), args.input)
        kwargs["outputs"] = merge_args(kwargs.get("outputs"), args.output)

        if args.command == "help":
            try:
                args.command = args.args.pop()
            except IndexError:
                self.parser.error("a command is required for help")
            executor = get_executors()[args.type]()
            help = executor.get_help(args.command)
            print(help)
            exit()

        elif args.command.endswith(".yaml"):
            logger.debug("Loading scenario from %s", args.command)
            scenario = load_scenario(os.path.abspath(args.command), **kwargs)

        else:
            logger.debug("Creating scenario from command line arguments")
            if args.command.endswith(".py"):
                logger.debug("Changing scenario type to Python")
                kwargs["type"] = "python"
                kwargs["name"] = os.path.basename(args.command)
            kwargs["command"] = args.command
            scenario = Scenario(**kwargs)

        scenario.benchmark(clean=args.clean)


def main():
    """Run command line interface."""
    cli = CLI()
    cli.run()
