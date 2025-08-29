import copy
import inspect
import itertools
import json
import os
import re
import shutil
import time
import yaml

from .cache import clear_cache
from .executor.factory import create_executor
from .monitor import get_system_info, monitor_system
from .report import calculate_run_summary, generate_html_report

import logging
logger = logging.getLogger(__name__)


class Scenario:
    """Scenario class."""

    def __init__(
        self,
        type: str,
        name: str,
        command: str,
        inputs: list | dict=None,
        outputs: list | dict=None,
        arguments: list | dict=None,
        repeat: int=1,
        run_wait: float=5.0,
        run_monitor: float=5.0,
        system_wait: float=5.0,
        system_monitor: float=5.0,
        workdir: str=None,
        basedir: str=None,
        outdir: str=None,
        venv: str=None,
    ):
        """Initializes scenario object.

        Args:
            type (str): Scenario type.
            name (str): Scenario name.
            command (str): Command.
            inputs (list | dict): Dictionary of inputs (optional).
            outputs (list | dict): Dictionary of outputs (optional).
            arguments (list | dict): Arguments (optional).
            repeat (int): Number of repetations (default = 1).
            run_wait (float): Idle wait time before and after each run (s) (default = 5.0)
            run_monitor (float): Monitoring time before and after each run (s) (default = 5.0).
            system_wait (float): Wait time before and after all runs (s) (default = 5.0)
            system_monitor (float): Monitoring time before and after all runs (s) (default = 5.0)
            workdir (str): Working directory path (default = current working directory).
            basedir (str): Base directory path (default = current working directory).
            outdir (str): Output directory path (default = generated from name)
            venv (str): Virtual environment path (optional).

        Raises:
            ValueError: if invalid scenario type.
            ValueError: if empty scenario name.
            ValueError: if empty command.
            ValueError: if invalid arguments.
            ValueError: if invalid inputs.
            ValueError: if invalid outputs.
        """
        if type not in ['qgis-process', 'qgis-python', 'python', 'shell']:
            raise ValueError("Invalid scenario type.", type)

        if not name:
            raise ValueError("Empty scenario name.")

        if not command:
            raise ValueError("Empty command.")

        if arguments and not isinstance(arguments, (list, dict)):
            raise ValueError("Invalid arguments.")

        if inputs and not isinstance(inputs, (list, dict)):
            raise ValueError("Invalid inputs.")

        if outputs and not isinstance(outputs, (list, dict)):
            raise ValueError("Invalid outputs.")

        self.type = type
        self.name = name
        self.command = command
        self.inputs = inputs or {}
        self.outputs = outputs or {}
        self.arguments = arguments or {}
        self.repeat = repeat or 1
        self.run_wait = run_wait or 0.0
        self.run_monitor = run_monitor or 0.0
        self.system_wait = system_wait or 0.0
        self.system_monitor = system_monitor or 0.0

        cwd = os.getcwd()

        self.workdir = workdir or cwd
        if not os.path.isabs(self.workdir):
            self.workdir = os.path.join(cwd, self.workdir)
            if not os.path.isdir(self.workdir):
                raise ValueError("Invalid working directory.", workdir)

        self.basedir = basedir or cwd
        if not os.path.isabs(self.basedir):
            self.basedir = os.path.join(cwd, self.basedir)
            if not os.path.isdir(self.basedir):
                raise ValueError("Invalid base directory.", basedir)

        self.outdir = outdir or re.sub(r'-+', '-', re.sub(r'[^\w-]', '-', name.lower())).strip('-')
        if not os.path.isabs(self.outdir):
            self.outdir = os.path.join(self.basedir, self.outdir)

        self.venv = venv
        if self.venv:
            if not os.path.isabs(self.venv):
                self.venv = os.path.join(cwd, self.venv)
            if not os.path.isdir(self.venv):
                raise ValueError("Invalid virtual environment.", venv)

        if isinstance(self.outputs, dict):
            outputs = list(self.outputs.values())
        else:
            outputs = self.outputs

        if not all(isinstance(item, str) for item in outputs):
            raise ValueError("Invalid outputs.")

        multi_input = isinstance(self.inputs, dict)

        if isinstance(self.arguments, list):
            args = {key: val for key, val in enumerate(self.arguments)}
        else:
            args = self.arguments

        args = args | (self.inputs if multi_input else {})
        args = {
            key: val if isinstance(val, list) else [val]
            for key, val in args.items()
        }

        if args:
            keys, vals = zip(*args.items())
            sets = [dict(zip(keys, items)) for items in itertools.product(*vals)]

        else:
            sets = [{}]

        self.sets = []
        for args in sets:
            data = {}

            if multi_input:
                data['inputs'] = [args[key] for key in self.inputs.keys()]
            else:
                data['inputs'] = self.inputs if isinstance(self.inputs, list) else [self.inputs]

            data['outputs'] = outputs
            if isinstance(self.outputs, dict):
                args.update(self.outputs)

            data['arguments'] = args

            self.sets.append(data)


    def _store(self, filename: str, content: dict):
        path = os.path.join(self.outdir, filename)
        with open(path, 'w', encoding='utf-8') as file:
            json.dump(content, file, ensure_ascii=False, indent=2)


    def _store_result(self, result: dict):
        self._store('result.json', result)


    def benchmark(self, clean: bool=False) -> dict:
        """Performs benchmarking of the scenario.

        Args:
            clean (bool): Set True to clean the output directory, if exists.

        Returns:
            Benchmarking results.
        """
        result = {}

        try:
            print("Running scenario {}.".format(self.name))

            num_sets = len(self.sets)
            num_runs = num_sets * self.repeat
            print("{} scenario {} with {} {}, {} {} in total.".format(
                num_sets,
                "sets" if num_sets > 1 else "set",
                self.repeat,
                "repeats" if self.repeat > 1 else "repeat",
                num_runs,
                "runs" if num_runs > 1 else "run",
            ))

            # Create executor
            print("Creating {} executor.".format(self.type))
            executor = create_executor(self)

            # Set up output directory
            print("Setting up output directory {}.".format(self.outdir))
            if os.path.exists(self.outdir):
                if os.path.isdir(self.outdir):
                    if not clean:
                        print("Output directory exists, aborting.")
                        return {}
                    else:
                        logger.debug(f"Removing existing output directory {self.outdir}.")
                        shutil.rmtree(self.outdir)
                else:
                    print("Invalid output directory, aborting.")
                    return {}
            os.makedirs(self.outdir)

            # Store executor configuration
            print("Storing executor configuration.")
            result['config'] = executor.config
            self._store_result(result)

            # Perform system cleanup
            print("Clearing system caches.")
            clear_cache()

            # Idle wait before the runs, if required
            # REMARK: Allowing some time after cleanup is recommended.
            if self.system_wait:
                print("Waiting {} s before the scenario runs.".format(self.system_wait))
                time.sleep(self.system_wait)

            # Store system information
            print("Storing system information.")
            result['system'] = get_system_info()
            self._store_result(result)

            # Perform baseline monitoring before the runs, if required
            if self.system_monitor:
                print("Baseline monitoring for {} s.".format(self.system_monitor))
                result['baseline'] = monitor_system(self.system_monitor)
                self._store_result(result)

            # Start execution loop
            print("Executing the runs.")
            start_time = time.time()

            len_sets = len(str(num_sets))
            len_runs = len(str(self.repeat))

            run_list = []

            # For each scenario set
            for i, data in enumerate(self.sets):
                set_id = i + 1

                # For each repetation
                for j in range(self.repeat):
                    run_id = j + 1

                    print("Scenario set {}, run {}:".format(set_id, run_id))

                    path = os.path.join(
                        f"set_{set_id:0{len_sets}d}",
                        f"run_{run_id:0{len_runs}d}",
                    )

                    abs_path = os.path.join(self.outdir, path)
                    os.makedirs(abs_path, exist_ok=True)

                    result_path = os.path.join(abs_path, 'result.json')

                    out = {
                        'set': set_id,
                        'run': run_id,
                        'arguments': data['arguments'],
                    }

                    # Perform system cleanup
                    print("Clearing system caches.")
                    clear_cache()

                    # Idle wait before the run, if required
                    if self.run_wait:
                        print("Waiting {} s before the run.".format(self.run_wait))
                        time.sleep(self.run_wait)

                    # Perform baseline monitoring before the run, if required
                    if self.run_monitor:
                        print("Baseline monitoring for {} s.".format(self.run_monitor))
                        out['baseline'] = monitor_system(self.run_monitor)
                        self._store(result_path, out)

                    # Modify run-specific arguments
                    args = copy.deepcopy(data['arguments'])

                    # Set input file paths
                    if isinstance(self.inputs, dict):
                        logger.debug("Modifying input paths.")
                        for key in self.inputs.keys():
                            args[key] = os.path.normpath(
                                args[key] if os.path.isabs(args[key]) else
                                os.path.join(self.workdir, args[key])
                            )

                    # Set output file paths
                    if isinstance(self.outputs, dict):
                        logger.debug("Modifying output paths.")
                        for key in self.outputs.keys():
                            args[key] = os.path.normpath(
                                args[key] if os.path.isabs(args[key]) else
                                os.path.join(abs_path, args[key])
                            )

                    # Get execution arguments
                    args = executor.get_arguments(self.command, args)

                    # Perform the run
                    print("Executing the run.")

                    out.update(executor.execute(args))

                    self._store(result_path, out)

                    # Idle wait after the run, if required
                    if self.run_wait:
                        print("Waiting {} s after the run.".format(self.run_wait))
                        time.sleep(self.run_wait)

                    # Perform endline monitoring after the run, if required
                    if self.run_monitor:
                        print("Endline monitoring for {} s.".format(self.run_monitor))
                        out['endline'] = monitor_system(self.run_monitor)
                        self._store(result_path, out)

                    # TODO: Store input files in the output directory.
                    for key, value in self.inputs.items():
                        input_path = os.path.normpath(
                            value if os.path.isabs(value) else
                            os.path.join(self.workdir, value)
                        )
                        # Copy input file
                        try:
                            if os.path.exists(input_path) and not os.path.exists(abs_path):
                                shutil.copy(input_path, abs_path)
                        except Exception as e:
                            logger.error(f"Error copying input file {input_path} to {abs_path}: {e}")
                    # TODO: Store output files in the output directory, if required.
                    for key, value in self.outputs.items():
                        output_path = os.path.normpath(
                            value if os.path.isabs(value) else
                            os.path.join(abs_path, value)
                        )
                        # Copy output file
                        try: 
                            if os.path.exists(output_path) and not os.path.exists(abs_path):
                                shutil.copy(output_path, abs_path)
                        except Exception as e:
                            logger.error(f"Error copying output file {output_path} to {abs_path}: {e}")
                # Append run output to the list
                run_list.append(out)
                # TODO: Generate summary of the set runs.
                run_summary = calculate_run_summary(out)
                # TODO: Store summary of the set runs.
                run_summary_path = os.path.join(abs_path, 'summary.json')
                self._store(run_summary_path, run_summary)

            duration = time.time() - start_time

            print("{} run(s) completed in {} s.".format(num_sets, duration))

            # Idle wait after the runs, if required
            if self.system_wait:
                print("Waiting {} s after the scenario runs.".format(self.system_wait))
                time.sleep(self.system_wait)

            # Perform endline monitoring after the runs, if required
            if self.system_monitor:
                print("Endline monitoring for {} s.".format(self.system_monitor))
                result['endline'] = monitor_system(self.system_monitor)
                self._store_result(result)

            # TODO: Generate summary of all runs.
            # TODO: Store summary of all runs.

            # Generate report
            report_path = os.path.join(self.outdir, 'report.html')
            generate_html_report(system_data=result, run_data=run_list, output_path=report_path)

        except KeyboardInterrupt:
            print("Benchmark run interrupted by user.")

        except Exception as err:
            raise

        return result


def load_scenario(path, **kwargs):
    """Loads scenario from a YAML file and customizes it if required.

    See Scenario class initialization method for available arguments.

    Args:
        path (str): Path of the YAML file.
        **kwargs: Custom scenario arguments.

    Returns:
        Scenario object.
    """
    # Load scenario from file
    logger.debug(f"Loading scenario from {path}.")
    with open(path, 'r', encoding='utf-8') as file:
        scenario = yaml.safe_load(file)

    # Update scenario arguments
    logger.debug(f"Updating scenario with {kwargs}.")
    scenario.update(kwargs)

    if scenario.get('outputs') and not isinstance(scenario['outputs'], (list, dict)):
        scenario['outputs'] = [scenario['outputs']]

    if not scenario.get('name'):
        scenario['name'] = os.path.splitext(os.path.basename(path))[0]

    # Sanitize arguments
    args = {}
    for key in inspect.signature(Scenario.__init__).parameters.keys():
        val = scenario.get(key)
        if key != 'self' and val is not None:
            args[key] = val

    # Create scenario
    return Scenario(**args)
