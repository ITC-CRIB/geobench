import sys
import os
import platform

system = platform.system()
if system == 'Windows':
    # Example path for Windows (adjust as necessary)
    qgis_path = 'C:/OSGeo4W64/apps/qgis'
    osgeo_path = 'C:/OSGeo4W64/apps/Qt5/bin'
    python_path = 'C:/OSGeo4W64/apps/Python37'
elif system == 'Darwin':  # macOS
    # Example path for macOS (adjust as necessary)
    qgis_path = '/Applications/QGIS.app/Contents/MacOS'
    osgeo_path = '/Applications/QGIS.app/Contents/Frameworks'
    python_path = '/Applications/QGIS.app/Contents/Resources/python'
elif system == 'Linux':
    # Example path for Linux (adjust as necessary)
    qgis_path = '/usr'
    osgeo_path = '/usr/lib'
    python_path = '/usr/share/qgis/python'
else:
    raise Exception(f'Unsupported OS: {system}')
    
# Append paths
sys.path.append(os.path.join(qgis_path, 'python'))
sys.path.append(osgeo_path)
sys.path.append(python_path)
# Additional path for processing
sys.path.append(os.path.join(python_path, 'plugins'))

# Now import QGIS modules
from qgis.core import (
    QgsApplication,
    QgsVectorLayer,
    QgsProject
)
import processing
from qgis.analysis import QgsNativeAlgorithms

# Initialize QGIS application
QgsApplication.setPrefixPath(qgis_path, True)
qgs = QgsApplication([], False)

# Load QGIS providers and algorithms
qgs.initQgis()
QgsApplication.processingRegistry().addProvider(QgsNativeAlgorithms())

# Load the input vector layer
input_layer_path = '/Users/bhawiyuga/project/geobench/sample-input/enschede/polygon.shp'
input_layer = QgsVectorLayer(input_layer_path, 'input_layer', 'ogr')

if not input_layer.isValid():
    print("Layer failed to load!")
else:
    QgsProject.instance().addMapLayer(input_layer)
    
    # Set the parameters for the buffer
    buffer_distance = 100  # Buffer distance in the layer's units
    output_layer_path = 'TEMPORARY_OUTPUT'
    
    # Run the buffer algorithm
    processing.run("native:buffer", {
        'INPUT': input_layer,
        'DISTANCE': buffer_distance,
        'SEGMENTS': 5,
        'DISSOLVE': False,
        'END_CAP_STYLE': 0,  # Round cap
        'JOIN_STYLE': 0,  # Round join
        'MITER_LIMIT': 2,
        'OUTPUT': output_layer_path
    })
    
    # Load the output buffer layer
    output_layer = QgsVectorLayer(output_layer_path, 'output_layer', 'ogr')
    if output_layer.isValid():
        QgsProject.instance().addMapLayer(output_layer)
    else:
        print("Output layer failed to load!")

# Exit QGIS application
qgs.exitQgis()