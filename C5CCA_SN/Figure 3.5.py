import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from shapely.geometry import Point
import os

# Define variable and paths
variable = 'SWE'

# -----------------------------
# Define the path to the data
# -----------------------------
data_path = 'path of the "metadata" dir'
#data_path = r'C:\Users\Prakash\Box\Sierra_Nevada_Regional_Report_Pre_Publication\chapter2_climate\metadata'

plot_path = 'where you want to save the Figure'
#plot_path = os.path.join(data_path, "Figure 3.5.png")

shapefile = gpd.read_file(os.path.join(data_path, 'CC5a_Regions', 'CC5a_RegionsSub.shp')).dropna(subset=['subregion']).to_crs('EPSG:4326')

# Load lat/lon
coord_data = np.load(os.path.join(data_path, 'VIC/soil_moisture/seasonal_means_CNRM-ESM2-1_historical.npz'))
longitudes, latitudes = coord_data['lon'], coord_data['lat']

# Extent
extent_buffered = [-122.484375, -117.5, 34.8, 42.1]

# Load and filter shapefile
shapefile = shapefile.to_crs('EPSG:4326')
regions_to_mask = ["N Sierra", "NE Sierra", "S Sierra", "SE Sierra"]
subregion_geometries = shapefile.loc[shapefile['subregion'].isin(regions_to_mask), 'geometry']
if subregion_geometries.empty:
    raise ValueError(f"Subregion geometries for {regions_to_mask} not found.")

# Define models and scenarios
models = ["CNRM-ESM2-1", "EC-Earth3-Veg", "GFDL-ESM4", "MPI-ESM1-2-HR"]
scenarios = ["ssp245", "ssp370", "ssp585"]
keys = ["historical_mean", "2041-2070_percentage_change", "2071-2100_percentage_change"]

# Load data
data = {}
for model in models:
    try:
        data[model] = {
            scenario: np.load(os.path.join(data_path, "VIC", f"{variable}/april_1st_{variable.lower()}_percentage_changes_{model}_{scenario}.npz"))
            for scenario in scenarios
        }
    except FileNotFoundError as e:
        print(f"File not found for model {model}. Skipping.")
        continue

if not data:
    raise ValueError("No data loaded for any model.")

# Color settings
bounds = [-100, -80, -60, -40, -20, 0, 20, 40, 60, 80, 100]
colors = ['#a50026','#f46d43','#fdae61','#fee08b','#fee8c8','#eff3ff','#bdd7e7','#6baed6','#3182bd','#08519c']
custom_cmap = ListedColormap(colors)
norm = BoundaryNorm(bounds, len(colors), clip=True)

# Masking function
def mask_data_vectorized(data_array, longitudes, latitudes, geometries):
    lon_grid, lat_grid = np.meshgrid(longitudes, latitudes)
    points = [Point(xy) for xy in zip(lon_grid.ravel(), lat_grid.ravel())]
    mask = np.array([any(geom.contains(p) for geom in geometries) for p in points]).reshape(data_array.shape)
    return np.where(mask, data_array, np.nan)

# Compute multimodel means
multimodel_mean = {s: {k: [] for k in keys} for s in scenarios}
for model in data:
    for s in scenarios:
        for k in keys:
            multimodel_mean[s][k].append(data[model][s][k])

for s in scenarios:
    for k in keys:
        multimodel_mean[s][k] = np.mean(multimodel_mean[s][k], axis=0)

# Mask multimodel mean data
datasets = [
    (mask_data_vectorized(multimodel_mean[s]['2041-2070_percentage_change'], longitudes, latitudes, shapefile.geometry), f"({chr(97+i)}) {s.upper()} (2041-2070)")
    for i, s in enumerate(scenarios)
] + [
    (mask_data_vectorized(multimodel_mean[s]['2071-2100_percentage_change'], longitudes, latitudes, shapefile.geometry), f"({chr(100+i)}) {s.upper()} (2071-2100)")
    for i, s in enumerate(scenarios)
]

# Example mapping function
def clean_title(old_title):
    # Replace SSP245 to SSP 2-4.5, SSP370 to SSP 3-7.0, SSP585 to SSP 5-8.5
    new_title = old_title.replace('SSP245', 'SSP 2-4.5') \
                         .replace('SSP370', 'SSP 3-7.0') \
                         .replace('SSP585', 'SSP 5-8.5')
    return new_title


# Plotting
fig, axes = plt.subplots(2, 3, figsize=(7, 6), subplot_kw={'projection': ccrs.PlateCarree()})
for ax, (data_arr, title) in zip(axes.flat, datasets):
    im = ax.pcolormesh(longitudes, latitudes, data_arr, 
                       cmap=custom_cmap, norm=norm, shading='auto', transform=ccrs.PlateCarree())
    ax.set_extent(extent_buffered)
    ax.coastlines()
    ax.add_feature(cfeature.BORDERS, linestyle=':')
    ax.add_geometries(subregion_geometries, crs=ccrs.PlateCarree(), edgecolor='black', facecolor='none', linewidth=0.75)

    # Set cleaned title
    ax.set_title(clean_title(title), fontsize=9)

    # Gridlines with labels
    gl = ax.gridlines(draw_labels=True, linewidth=0.5, color='gray', alpha=0.7, linestyle='--')
    gl.top_labels = False
    gl.bottom_labels = ax in axes[1, :]  # keep bottom x labels only for bottom row
    gl.left_labels = True                 # show latitude labels on all panels
    gl.right_labels = False
    gl.xlabel_style = {'size': 8}
    gl.ylabel_style = {'size': 8}

fig.subplots_adjust(left=0.05, right=0.95, top=0.80, bottom=0.18, hspace=0.21, wspace=0.01)

# Colorbar
cbar_ax = fig.add_axes([0.15, 0.07, 0.7, 0.03])
cbar = plt.colorbar(im, cax=cbar_ax, orientation='horizontal')

# Set label above the colorbar
cbar.set_label(f'Differences in {variable} (%)', labelpad=5)
cbar.ax.xaxis.set_label_position('top')  # moves label above
cbar.ax.xaxis.label.set_size(10)          # set font size here
cbar.ax.tick_params(labelsize=10)
cbar.set_ticks(bounds)

plt.savefig(plot_path, dpi=300, bbox_inches='tight')
plt.show()
