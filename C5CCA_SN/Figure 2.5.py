# -*- coding: utf-8 -*-
"""
Created on Sat Mar  8 11:51:14 2025

@author: Prakash
"""
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from matplotlib.colors import BoundaryNorm, ListedColormap
from shapely.geometry import Point

# Define paths
data_path = 'path of the "metadata" dir'
#data_path = r"C:\Users\Prakash\Box\Sierra_Nevada_Regional_Report_Pre_Publication\chapter2_climate\metadata"
shapefile_path = data_path + '/CC5a_Regions/CC5a_RegionsSub.shp'
outdir = 'where you want to save the Figure'
#outdir = data_path + "/pr_change_3SSPs_halfsize.png"

# Load the data
main_data = np.load(data_path + '/arrays_climatology_data_bar_plotpr.npz')
#hist1 = main_data['hist1']
hist2 = main_data['hist2']
# mid
ssp245_mid = main_data['ssp245_mid']
ssp370_mid = main_data['ssp370_mid']
ssp585_mid = main_data['ssp585_mid']
# end
ssp245_end = main_data['ssp245_end']
ssp370_end = main_data['ssp370_end']
ssp585_end = main_data['ssp585_end']

## array in ssp370 has shape (227,160). Pad it
# Given shape (227, 160), target shape (227, 192)
target_shape = hist2.shape

# Calculate padding size
pad_width = target_shape[1] - ssp370_mid.shape[1]  # 192 - 160 = 32

# Pad with NaNs along the second dimension (right side)
ssp370_mid_padded = np.pad(ssp370_mid, ((0, 0), (0, pad_width)), mode='constant', constant_values=np.nan)
ssp370_end_padded = np.pad(ssp370_end, ((0, 0), (0, pad_width)), mode='constant', constant_values=np.nan)

# now compute change %
# mid
diff_ssp245_array_mid = (ssp245_mid - hist2)*100/hist2
diff_ssp370_array_mid = (ssp370_mid_padded - hist2)*100/hist2
diff_ssp585_array_mid = (ssp585_mid - hist2)*100/hist2

# end
diff_ssp245_array_end = (ssp245_end - hist2)*100/hist2
diff_ssp370_array_end = (ssp370_end_padded - hist2)*100/hist2
diff_ssp585_array_end = (ssp585_end - hist2)*100/hist2

## get lon/lat
data1 = np.load(data_path + '/pr_data.npz')
longitudes = data1['longitudes']
latitudes = data1['latitudes']

# Load the shapefile
shapefile = gpd.read_file(shapefile_path)

# Define the target coordinate system (WGS84)
target_crs = 'EPSG:4326'
shapefile = shapefile.to_crs(target_crs)

# Select the subregions of interest and combine them
regions_to_mask = ["N Sierra", "NE Sierra", "S Sierra", "SE Sierra"]
subregion_geometries = shapefile.loc[shapefile['subregion'].isin(regions_to_mask), 'geometry']

if subregion_geometries.empty:
    raise ValueError(f"Subregion geometries for {regions_to_mask} not found.")

# Combine selected subregion geometries into a single MultiPolygon
combined_geom = subregion_geometries.unary_union

# Create a mask for the selected subregions
def mask_data(data, lon, lat, geometry):
    mask = np.zeros_like(data, dtype=bool)
    lon_flat = lon.flatten()
    lat_flat = lat.flatten()
    for i, x in enumerate(lon_flat):
        for j, y in enumerate(lat_flat):
            if geometry.contains(Point(x, y)):
                mask[j, i] = True
    return np.where(mask, data, np.nan)

# Mask the data arrays
masked_data_ssp245_mid = mask_data(diff_ssp245_array_mid, longitudes, latitudes, combined_geom)
masked_data_ssp370_mid = mask_data(diff_ssp370_array_mid, longitudes, latitudes, combined_geom)
masked_data_ssp585_mid = mask_data(diff_ssp585_array_mid, longitudes, latitudes, combined_geom)

masked_data_ssp245_end = mask_data(diff_ssp245_array_end, longitudes, latitudes, combined_geom)
masked_data_ssp370_end = mask_data(diff_ssp370_array_end, longitudes, latitudes, combined_geom)
masked_data_ssp585_end = mask_data(diff_ssp585_array_end, longitudes, latitudes, combined_geom)

# Define extent based on valid data and the new longitude range
long_min, long_max = -122.484375, -117.5
lat_min, lat_max = latitudes.min(), latitudes.max()
extent = [long_min, long_max, lat_min, lat_max]

# Adjust the buffered longitude and latitude ranges
long_min_buffered = longitudes.min()  # Use the minimum longitude from the data
long_max_buffered = -117.8  # Set the maximum longitude to -118 # Extend the longitude to the right by 0.5 degrees
lat_min_buffered = latitudes.min() - 0.1  # Add a small buffer to the latitude (optional)
lat_max_buffered = latitudes.max() + 0.1

# Updated extent based on buffered values
extent_buffered = [long_min_buffered, long_max_buffered, lat_min_buffered, lat_max_buffered]

# Define the masked datasets
masked_datasets = [
    ("(a) SSP 2-4.5 (2041–2070)", masked_data_ssp245_mid),
    ("(b) SSP 3-7.0 (2041–2070)", masked_data_ssp370_mid),
    ("(c) SSP 5-8.5 (2041–2070)", masked_data_ssp585_mid),
    ("(d) SSP 2-4.5 (2071–2100)", masked_data_ssp245_end),
    ("(e) SSP 3-7.0 (2071–2100)", masked_data_ssp370_end),
    ("(f) SSP 5-8.5 (2071–2100)", masked_data_ssp585_end),
]

# 1️⃣ Set global font settings
size = 7  # 6.5–8 works best for 4-inch width
plt.rcParams.update({
    'font.size': size,
    'font.family': 'Arial',
    'axes.titlesize': size,
    'xtick.labelsize': size,
    'ytick.labelsize': size
})

FIG_W_IN = 4.0          # half A4 width guideline
FIG_H_IN = 6.2          # keep tall enough for 2x3 maps; tweak if needed
SAVE_DPI = 600

fig, axes = plt.subplots(
    nrows=2, ncols=3,
    figsize=(4,5.5),
    subplot_kw={'projection': ccrs.PlateCarree()}
)
# Define color map and boundaries
colors = ['#a6611a','#d0d1e6','#67a9cf','#1c9099','#016c59']
bounds = [-10, 0, 10, 20, 30, 40]
custom_cmap = ListedColormap(colors)
norm = BoundaryNorm(boundaries=bounds, ncolors=len(colors), clip=True)

for ax, (title, data) in zip(axes.flat, masked_datasets):
    im = ax.pcolormesh(longitudes, latitudes, data, cmap=custom_cmap, norm=norm, shading='auto', transform=ccrs.PlateCarree())
    ax.set_extent(extent_buffered, crs=ccrs.PlateCarree())
    ax.coastlines()
    ax.add_feature(cfeature.BORDERS, linestyle=':')
    ax.add_geometries(subregion_geometries, crs=ccrs.PlateCarree(), edgecolor='black', facecolor='none', linewidth=0.75)

    # Gridlines
    gl = ax.gridlines(draw_labels=True, linewidth=0.5, color='gray', alpha=0.7, linestyle='--')
    gl.top_labels = False
    gl.right_labels = False
    gl.bottom_labels = ax not in axes[0, :]
    gl.left_labels = ax in axes[:, 0]

    # Gridline label sizes inherit rcParams['font.size'] now
    gl.xlabel_style = {}
    gl.ylabel_style = {}

    # Titles inherit rcParams['axes.titlesize']
    ax.set_title(title, pad=9)

# Adjust subplots to make room for suptitle
fig.subplots_adjust(
    left=0.08, right=0.98,
    top=0.92, bottom=0.18,
    hspace=0.12, wspace=0.05
)

# Colorbar
cbar_ax = fig.add_axes([0.12, 0.11, 0.76, 0.028])  # [left, bottom, width, height]
cbar = plt.colorbar(im, cax=cbar_ax, orientation='horizontal')
cbar.set_ticks(bounds)
cbar.ax.set_xticklabels([f'{tick}%' for tick in bounds])
# Tick labels now inherit rcParams['font.size']
cbar.ax.tick_params(labelsize=None)
w, h = fig.get_size_inches()
plt.savefig(outdir, dpi=SAVE_DPI, bbox_inches='tight')
plt.show()
