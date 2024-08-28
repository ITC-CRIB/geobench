# Note

- No need to define "qgis_process run" in the command
- No need to include INPUT and OUTPUT in the command string (or no need to define input and output as parameters in yaml)
- Change the way we define the input in scenario.

    ```
    name: ExampleBenchmark
    repeat: 2
    type: qgis-process
    command: native:countpointsinpolygon
    temp-directory: "./sample-output"
    inputs:
    POLYGONS : /Users/bhawiyuga/project/geobench/sample-input/enschede/polygon.shp
    POINTS: /Users/bhawiyuga/project/geobench/sample-input/enschede/point.shp
    outputs:
    OUTPUT: </temp/xxx.shp>
    parameters:
    distance_units: meters
    area_units: m2
    ellipsoid: EPSG:7030
    WEIGHT: 
    CLASSFIELD: 
    FIELD: NUMPOINTS 
    output-structure: nested
    ```

- Copy input to the output directory
- Standardized the name of the summary json file
- Try to find the way to execute program with different version
- Support query (collec data) from the (multiple) prometheus/server -> selected
- Discuss: parameters to be collected from tools 

Meeting 22 Aug 2024:
- [x] Bug: the output location is wrong
- [x] Record CPU (per CPU core), memory, existing process for each second 
- Also record how many time take for recording these informations
- [x] Output for each run -> also include input parameters (with the input information)
- Output disk I/O statistics
- Include query from prometheus 
- Configuration file for the tool itself (we can define it later). For example: number of replication, prometheus port and url, 