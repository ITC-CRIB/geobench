# GeoBench

GeoBench is a tool designed to benchmark geospatial software. It allows users to run benchmarks based on scenarios specified in YAML files. This project is currently under development.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Operating System**: Linux, Windows (with WSL2 or Powershell), MacOS
- **Python**: Python 3 with the `pip` package manager installed

## Installation

Follow these steps to set up GeoBench:

1. **Clone the repository**:
   ```bash
   git clone https://github.com/ITC-CRIB/geobench
   cd geobench
   ```
2. **Pull the repository**:
   ```bash
   cd geobench
   git pull
   ```

3. **Set up and activate the Python environment**:
   - **Using `venv`**:
     ```bash
     python3 -m venv venv
     source .venv/bin/activate   # On Windows, use `venv\Scripts\activate`
     ```

   - **Using `virtualenv`**:
     ```bash
     pip install virtualenv
     virtualenv .venv
     source .venv/bin/activate   # On Windows, use `venv\Scripts\activate`
     ```

4. **Install required packages**:
   ```bash
   pip install -r requirements.txt
   ```

## Running

An example YAML file, `example-scenario.yml`, is provided. 

Prepare the data and place it to `sample-input` directory.

Create `scenario.yaml` file. You can copy from the example yaml file. You can also modify the scenario depending on the need.
```
cp example-scenario.yaml scenario.yaml
```

To run the benchmark, use the following command:

```bash
python geobench run -f scenario.yaml
```

This will execute the benchmark as specified in the `example-scenario.yml` file.

---

Feel free to contribute to the development of GeoBench by submitting issues or pull requests on the repository. For more details on contributing, please refer to the CONTRIBUTING.md file in the repository.