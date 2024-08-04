import re
import ast

def extract_parameters_from_code(code_snippet):
    try:
        # Use regex to find the dictionary part in the code
        pattern = re.compile(r"processing.run\([^,]+, ({[^}]+})\)")
        match = pattern.search(code_snippet)
        if match:
            param_str = match.group(1)
            return param_str
        else:
            return None
    except Exception as e:
        return str(e)

def decode_parameters(parameter_str):
    try:
        # Decode the string into a dictionary
        param_dict = ast.literal_eval(parameter_str)
        return param_dict
    except Exception as e:
        return str(e)

def encode_parameters(param_dict):
    try:
        # Encode the dictionary back into a string
        param_str = str(param_dict)
        return param_str
    except Exception as e:
        return str(e)

def replace_parameters_in_code(code_snippet, new_param_str):
    try:
        # Use regex to replace the old dictionary part with the new one
        pattern = re.compile(r"(processing.run\([^,]+, ){[^}]+}(.*\))")
        new_code = pattern.sub(rf"\1{new_param_str}\2", code_snippet)
        return new_code
    except Exception as e:
        return str(e)

# Example usage
code_snippet = """
import processing
from processing.core.Processing import Processing

Processing.initialize()
# QgsApplication.processingRegistry().addProvider(QgsNativeAlgorithms())

processing.run("native:buffer", {'INPUT':'/Users/bhawiyuga/project/geobench/sample-input/enschede/polygon.shp','DISTANCE':10,'SEGMENTS':5,'END_CAP_STYLE':0,'JOIN_STYLE':0,'MITER_LIMIT':2,'DISSOLVE':False,'SEPARATE_DISJOINT':False,'OUTPUT':'/Users/bhawiyuga/project/geobench/sample-output/hello.shp'})

# Exit QGIS application
qgs.exitQgis()
"""

# Extract parameters
parameter_str = extract_parameters_from_code(code_snippet)
decoded_params = decode_parameters(parameter_str)
decoded_params["DISSOLVE"] = True
print("Decoded Parameters:", decoded_params)

# Encode parameters back to string
encoded_params = encode_parameters(decoded_params)
# print("Encoded Parameters:", encoded_params)

# Replace parameters in the code snippet
new_code_snippet = replace_parameters_in_code(code_snippet, encoded_params)
print("New Code Snippet:\n", new_code_snippet)