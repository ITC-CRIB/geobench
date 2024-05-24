import os
import dask
import dask.array as da
import rioxarray
import xarray as xr
from dask.distributed import Client
from pystac_client import Client as STACClient

# Initialize the Dask client
# client = Client("localhost:8786")

# print("Connected to Dask cluster")

from shapely.geometry import Point

point = Point(4.89, 52.37)  # AMS coordinates
# Define the STAC API URL and search parameters
stac_api_url = "https://earth-search.aws.element84.com/v1"
search_params = {
    "collections": ["sentinel-2-l2a"],
    # "bbox": [30.918946733283434, -25.8560847081756, 41.697736288557536, -12.604168927104041],  # Approximate bounding box for Mozambique
    "datetime": "2023-01-01/2023-01-02",
    # "query": {"eo:cloud_cover": {"lt": 20}},
    "intersects":point,
    "max_items":50,
}


print("Searching datasets")
# Initialize the STAC client and search for items
stac_client = STACClient.open(stac_api_url)
search = stac_client.search(**search_params)
print(f"Found datasets {search.matched()}")
items = search.item_collection()


print("Downloading assets")
# Download URLs for NIR (B08) and Red (B04) bands
nir_urls = [item.assets["nir08"].href for item in items]
red_urls = [item.assets["red"].href for item in items]

# Ensure the lists are not empty
if not nir_urls or not red_urls:
    raise ValueError("No data found for the specified search parameters.")

def load_raster(url):
    return rioxarray.open_rasterio(url, chunks="auto", masked=True)

def calculate_ndvi(nir_url, red_url):
    # Load the NIR and Red bands using rioxarray
    nir = load_raster(nir_url)
    red = load_raster(red_url)

    red = red.rio.reproject_match(nir)
    
    # Ensure that the data arrays are Dask arrays
    nir_data = nir.data
    red_data = red.data
    
    # Calculate NDVI
    ndvi = (nir_data - red_data) / (nir_data + red_data)
    
    # Update the xarray metadata to reflect the NDVI band
    ndvi_da = xr.DataArray(ndvi, name='NDVI', coords=nir.coords, dims=nir.dims, attrs=nir.attrs)
    return ndvi_da

print("Calculates NDVI")
# Calculate NDVI for all pairs of NIR and Red URLs
ndvi_list = [calculate_ndvi(nir, red) for nir, red in zip(nir_urls, red_urls)]

def save_ndvi(ndvi_da, output_path):
    ndvi_da.rio.to_raster(output_path, tiled=True, windowed=True)

output_dir = "ndvi_output"
os.makedirs(output_dir, exist_ok=True)

print("Saving outputs")
for i, ndvi_da in enumerate(ndvi_list):
    output_path = os.path.join(output_dir, f"ndvi_{i}.tif")
    save_ndvi(ndvi_da, output_path)

# Close the Dask client
# client.close()