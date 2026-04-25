import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from shapely.geometry import Point
import os

# --- Paths and variable ---
variable = 'SWE'
data_path = 'path of the "metadata" dir'
#data_path = r'C:\Users\Prakash\Box\Sierra_Nevada_Regional_Report_Pre_Publication\chapter2_climate\metadata'
outdir = 'where you want to save the Figure'

shapefile_path = os.path.join(data_path, 'CC5a_Regions/CC5a_RegionsSub.shp')
plot_path = os.path.join(outdir, f"{variable}_change_multiModel_new_absolute_without_watershed.png")

# --- Load lat/lon ---
coord_data = np.load(os.path.join(data_path, 'VIC/soil_moisture/seasonal_means_CNRM-ESM2-1_historical.npz'))
longitudes, latitudes = coord_data['lon'], coord_data['lat']

# --- Map extent ---
extent_buffered = [-122.484375, -117.5, 34.8, 42.1]

# --- Load shapefile ---
shapefile = gpd.read_file(shapefile_path).to_crs('EPSG:4326')
regions_to_mask = ["N Sierra", "NE Sierra", "S Sierra", "SE Sierra"]
subregion_geometries = shapefile.loc[shapefile['subregion'].isin(regions_to_mask), 'geometry']
if subregion_geometries.empty:
    raise ValueError(f"Subregion geometries for {regions_to_mask} not found.")

# --- Models and scenarios ---
models = ["CNRM-ESM2-1", "EC-Earth3-Veg", "GFDL-ESM4", "MPI-ESM1-2-HR"]
scenarios = ["ssp245", "ssp370", "ssp585"]
keys = ["historical_mean", "2041-2070_absolute_change", "2071-2100_absolute_change"]

# --- Load data ---
data = {}
for model in models:
    try:
        data[model] = {
            scenario: np.load(os.path.join(
                data_path, f"VIC/{variable}/april_1st_{variable.lower()}_absolute_changes_{model}_{scenario}.npz"
            ))
            for scenario in scenarios
        }
    except FileNotFoundError:
        print(f"File not found for model {model}. Skipping.")
        continue

if not data:
    raise ValueError("No data loaded for any model.")

# --- Masking function ---
def mask_data_vectorized(data_array, longitudes, latitudes, geometries):
    lon_grid, lat_grid = np.meshgrid(longitudes, latitudes)
    points = [Point(xy) for xy in zip(lon_grid.ravel(), lat_grid.ravel())]
    mask = np.array([any(geom.contains(p) for geom in geometries) for p in points]).reshape(data_array.shape)
    return np.where(mask, data_array, np.nan)

# --- Compute multimodel means ---
multimodel_mean = {s: {k: [] for k in keys} for s in scenarios}
for model in data:
    for s in scenarios:
        for k in keys:
            multimodel_mean[s][k].append(data[model][s][k])

for s in scenarios:
    for k in keys:
        multimodel_mean[s][k] = np.mean(multimodel_mean[s][k], axis=0)

# --- Convert to inches and mask ---
datasets = [
    (
        mask_data_vectorized(multimodel_mean[s]['2041-2070_absolute_change'], longitudes, latitudes, shapefile.geometry) / 25.4,
        f"({chr(97+i)}) {s.upper()} (2041-2070)"
    )
    for i, s in enumerate(scenarios)
] + [
    (
        mask_data_vectorized(multimodel_mean[s]['2071-2100_absolute_change'], longitudes, latitudes, shapefile.geometry) / 25.4,
        f"({chr(100+i)}) {s.upper()} (2071-2100)"
    )
    for i, s in enumerate(scenarios)
]

# --- Discrete colormap ---
all_data = np.concatenate([d[0].ravel() for d in datasets])

# --- Landmarks ---
landmarks = {
    "Hetch Hetchy": (-119.6, 37.97),
    "Mokelumne River": (-120.8, 38.3),
    "Sacramento": (-121.49, 38.58),
    "Fresno": (-119.77, 36.74),
    "Reno": (-119.81, 39.53)
}
landmark_numbers = {name: i+1 for i, name in enumerate(landmarks.keys())}

# --- Control flag for watershed ---
show_watershed = False   # Change to False to hide watershed boundary

# --- Colormap setup ---
all_data = np.concatenate([d[0].ravel() for d in datasets])

neg_colors = ['#bd0026', '#f03b20', '#fd8d3c', '#fecc5c', '#ffffb2']  
pos_colors = ['#eff3ff']  # single light blue

colors = neg_colors + pos_colors
custom_cmap = ListedColormap(colors)
bounds = [-50, -40, -30, -20, -10, 0, 10]  # 5 negative + 1 positive
norm = BoundaryNorm(bounds, ncolors=len(colors), clip=True)

# Example mapping function
def clean_title(old_title):
    
    new_title = old_title.replace('SSP245', 'SSP 2-4.5') \
                         .replace('SSP370', 'SSP 3-7.0') \
                         .replace('SSP585', 'SSP 5-8.5')
    return new_title


# --- Plotting ---
fig, axes = plt.subplots(2, 3, figsize=(14, 12),
                         subplot_kw={'projection': ccrs.PlateCarree()})

for ax, (data_arr, title) in zip(axes.flat, datasets):
    im = ax.pcolormesh(longitudes, latitudes, data_arr,
                       cmap=custom_cmap, norm=norm, shading='auto',
                       transform=ccrs.PlateCarree())
    ax.set_extent(extent_buffered)
    ax.coastlines()
    ax.add_feature(cfeature.BORDERS, linestyle=':')
    ax.add_geometries(subregion_geometries,
                      crs=ccrs.PlateCarree(),
                      edgecolor='black',
                      facecolor='none',
                      linewidth=0.75)
    ax.set_title(title, fontsize=16, fontfamily='Arial')
    # Set cleaned title
    ax.set_title(clean_title(title), fontsize=16, fontfamily='Arial')

    # Gridlines
    gl = ax.gridlines(draw_labels=True, linewidth=0.5, color='gray',
                      alpha=0.7, linestyle='--')
    gl.top_labels = False
    gl.bottom_labels = ax in axes[1, :]
    gl.left_labels = ax in axes[:, 0]
    gl.right_labels = False
    gl.xlabel_style = {'size': 16, 'fontname': 'Arial'}
    gl.ylabel_style = {'size': 16, 'fontname': 'Arial'}

# --- Adjust layout and colorbar ---
fig.subplots_adjust(left=0.05, right=0.95, top=0.92, bottom=0.18,
                    hspace=0.15, wspace=0.01)

cbar_ax = fig.add_axes([0.15, 0.07, 0.7, 0.03])
cbar = plt.colorbar(im, cax=cbar_ax, orientation='horizontal', ticks=bounds)

# --- Set colorbar label above and increase font size ---
cbar.set_label(f'Differences in {variable} (inches)', labelpad=10)
cbar.ax.xaxis.set_label_position('top')  # moves label above
cbar.ax.xaxis.label.set_fontsize(18)     # increase font size
cbar.ax.xaxis.label.set_fontname('Arial')

# --- Increase font size of tick labels ---
cbar.ax.tick_params(labelsize=14)  # tick labels along the colorbar

# --- Optionally, set tick label fontname too ---
for tick in cbar.ax.get_xticklabels():
    tick.set_fontname('Arial')

# --- Save and Show ---
plt.savefig(plot_path, dpi=600, bbox_inches='tight')
plt.show()
