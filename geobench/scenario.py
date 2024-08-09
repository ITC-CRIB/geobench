import yaml
import itertools
import re
import os

from .error import MissingParameterError

# Define the scenario structure
class Scenario:
    def __init__(self, name, repeat, type, command, command_file, inputs, outputs, temp_directory, parameters, output_structure, scenario_combination):
        self.name = name
        self.repeat = repeat
        self.type = type
        self.command = command
        self.command_file = command_file
        self.inputs = inputs
        self.outputs = outputs
        self.temp_directory = temp_directory
        self.parameters = parameters
        self.output_structure = output_structure
        self.combination = scenario_combination

    def __repr__(self):
        return (f"Scenario(name={self.name}, repeat={self.repeat}, type={self.type}, "
                f"command={self.command}, command_file={self.command_file}, inputs={self.inputs}, "
                f"outputs={self.outputs}, temp_directory={self.temp_directory}, "
                f"parameters={self.parameters}, output_structure={self.output_structure}, scenarios={self.combination})")


def parse_range_expression(expression):
    # Match the pattern <start>:<end>:<step> or <start>:<end>
    match = re.match(r'(\d+):(\d+)(?::(\d+))?', expression)
    if not match:
        raise ValueError(f"Invalid range expression: {expression}")
    
    start = int(match.group(1))
    end = int(match.group(2))
    step = int(match.group(3)) if match.group(3) else 1
    
    return list(range(start, end + 1, step))

def expand_parameters(parameters):
    expanded_params = {}
    for key, values in parameters.items():
        expanded_values = []
        for value in values:
            if isinstance(value, str) and ':' in value:
                # Assume it's a range expression
                expanded_values.extend(parse_range_expression(value))
            else:
                expanded_values.append(value)
        expanded_params[key] = expanded_values
    return expanded_params

def generate_scenarios(parameters):
     # Ensure all values are lists
    normalized_parameters = {k: v if isinstance(v, list) else [v] for k, v in parameters.items()}
    
    keys, values = zip(*normalized_parameters.items())
    scenarios = [dict(zip(keys, combination)) for combination in itertools.product(*values)]
    return scenarios

def load_scenario(yaml_file, cmd_args):
    with open(yaml_file, 'r') as file:
        scenario_data = yaml.safe_load(file)
    
    # Get the repetition parameter
    args_repeat = cmd_args.repeat
    # Get scenario name 
    args_scenario_name = cmd_args.name

    name = args_scenario_name if args_scenario_name is not None else scenario_data.get('name', None)
    repeat = scenario_data.get('repeat')
    type = scenario_data.get('type')
    command = scenario_data.get('command')
    command_file = scenario_data.get('command-file')
    inputs = scenario_data.get('inputs', {})
    outputs = scenario_data.get('outputs', {})
    temp_directory = scenario_data.get('temp-directory')
    parameters = scenario_data.get('parameters', {})
    output_structure = scenario_data.get('output-structure')

    checked_inputs = {}
    # Update inputs parameters to absolute path
    for key_param, value_param in inputs.items():
        checked_inputs[key_param] = os.path.abspath(value_param)
    
    checked_outputs = {}
    # Update outputs parameters to absolute path
    for key_param, value_param in outputs.items():
        checked_outputs[key_param] = os.path.abspath(value_param)

    # expanded_parameters = expand_parameters(parameters)
    all_parameters = parameters | checked_inputs | checked_outputs
    scenarios = generate_scenarios(all_parameters)

    if name is None:
        raise MissingParameterError("Error: 'name' is a mandatory parameter and must be specified either as a command line argument or in the YAML scenario file.")
    
    if type not in ["qgis-command", "qgis-python", "qgis-json", "arcgis-python"]:
        raise MissingParameterError(f"Error: '{type}' is not a valid type. Use qgis-command, qgis-python, qgis-json, arcgis-python.")
    
    return Scenario(name, repeat, type, command, command_file, checked_inputs, checked_outputs, temp_directory, parameters, output_structure, scenarios)

# Example usage
if __name__ == "__main__":
    scenario_path = "example-scenario.yml"  # Replace with your YAML file path
    scenario = load_scenario(scenario_path)
    print(scenario)