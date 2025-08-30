# GeoBench

GeoBench is a tool designed to benchmark geospatial software. It allows users to run benchmarks based on scenarios specified in YAML files or directly in Jupyter notebooks. This project is currently under development.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Operating System**: Linux, Windows (with WSL2 or Powershell), MacOS
- **Python**: Python 3 with the `pip` package manager installed

## Preparation

Follow these steps to set up GeoBench:

- **Clone the repository**:
   ```bash
   git clone https://github.com/ITC-CRIB/geobench
   cd geobench
   ```

- **Pull the repository**:
   ```bash
   cd geobench
   git pull
   ```

## Installation as Tool
- Using `pip`
  ```
  pip install .
  ```
- Using `uv`
	- Install `uv` tool
		- MacOS and Linux
		```
		curl -LsSf https://astral.sh/uv/install.sh | sh
		```
		- Windows (from Powershell/Terminal)
		```
		powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
		```
	- Run the installation process
	```
	uv tool install . --upgrade
	```
- To run the program you can execute following command:
	```
	geobench scenario.yaml
	```
## Development
- **Set up and activate the Python environment**:
   - **Using `venv`**:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate   # On Windows, use `.venv\Scripts\activate`
	 pip install -r requirements.txt
     ```
   
    - **Using `uv` (recommended) **:
	```
	uv sync
	```

- To run the program during development (without installing it as tool), you can execute following command:
	```
	python -m geobench.cli scenario.yaml
	```

## Running Benchmarking Scenario
A benchmarking scenario is represented in a YAML file. For the time being, there are two scenario types supported in this tool: `qgis-process` and `qgis-python`. The `qgis-json` and `arcgis-command` will be supported later.

### Using Jupyter Notebook Benchmarking
In addition to YAML scenarios, GeoBench now supports benchmarking directly within Jupyter notebooks. This is useful for benchmarking Python code interactively.
---

Feel free to contribute to the development of GeoBench by submitting issues or pull requests on the repository. For more details on contributing, please refer to the CONTRIBUTING.md file in the repository.

## Jupyter Notebook Benchmarking

GeoBench now supports benchmarking directly within Jupyter notebooks. There are three ways to use this functionality:

### 1. Using the JupyterBenchmark Class

```python
from geobench.jupyter import JupyterBenchmark

# Create a benchmark instance
bench = JupyterBenchmark(
    name="my-benchmark",
    outdir="results",
    run_monitor=2.0,
    clean=True
)

# Start benchmarking
bench.start("my-function")

# Run your code
result = my_function()

# Finish benchmarking
bench.finish(True)  # Pass True for success, False for failure

# Generate HTML report
bench.generate_report()
```

### 2. Using the Benchmark Decorator

```python
from geobench.jupyter import benchmark

@benchmark(name="my-function-benchmark", outdir="results", clean=True)
def my_function():
    # Your code here
    return result
    
# Call the decorated function
result = my_function()
```