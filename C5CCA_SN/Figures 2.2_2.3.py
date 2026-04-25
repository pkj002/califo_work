# -*- coding: utf-8 -*-
"""
Created on Mon Mar 10 18:18:12 2025

@author: Prakash
"""
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from matplotlib.colors import BoundaryNorm, ListedColormap
from shapely.geometry import Point

#var = "tasmin"  # This could be "tmx" or another value
var = "tasmax"
var_labels = {
    "tasmax": "Tmax",
    "tasmin": "Tmin"
    }

# Define paths
data_path = 'path of the "metadata" dir'
#data_path = r"C:\Users\Prakash\Box\Sierra_Nevada_Regional_Report_Pre_Publication\chapter2_climate\metadata"
outdir = 'where you want to save the Figure'
shapefile_path = data_path + '/CC5a_Regions/CC5a_RegionsSub.shp'
plot_path = outdir + f"/{var}_change_all_models_mid_end1.png"

# Load essential data
data = np.load(data_path + f'/arrays_climatology_data_bar_plot_{var}.npz')
data_arrays = [data[key] for key in ['hist1', 'hist2', 'ssp245_mid', 'ssp585_mid', 'ssp245_end', 'ssp585_end']]
period_names = ['hist1', 'hist2', 'ssp245_mid', 'ssp585_mid', 'ssp245_end', 'ssp585_end']

# padding (227, 160)
ssp_370_end = np.pad(data['ssp370_end'], ((0, 0), (0, 32)), constant_values=np.nan)
ssp_370_mid = np.pad(data['ssp370_mid'], ((0, 0), (0, 32)), constant_values=np.nan)

# end 
diff_ssp585_array_end = data['ssp585_end'] - data['hist2']
diff_ssp245_array_end = data['ssp245_end'] - data['hist2']
diff_ssp370_array_end = ssp_370_end - data['hist2']

# mid
diff_ssp585_array_mid = data['ssp585_mid'] - data['hist2']
diff_ssp245_array_mid = data['ssp245_mid'] - data['hist2']
diff_ssp370_array_mid = ssp_370_mid - data['hist2']


## Get lon, lat from old file
co = np.load(data_path + '/coordinates.npz')
longitudes = co['longitudes']
latitudes = co['latitudes']

# Load the shapefile
shapefile = gpd.read_file(shapefile_path)
target_crs = 'EPSG:4326'
shapefile = shapefile.to_crs(target_crs)

regions_to_mask = ["N Sierra", "NE Sierra", "S Sierra", "SE Sierra"]
subregion_geometries = shapefile.loc[shapefile['subregion'].isin(regions_to_mask), 'geometry']

if subregion_geometries.empty:
    raise ValueError(f"Subregion geometries for {regions_to_mask} not found.")

combined_geom = subregion_geometries.unary_union

def mask_data(data, lon, lat, geometry):
    mask = np.zeros_like(data, dtype=bool)
    lon_flat = lon.flatten()
    lat_flat = lat.flatten()
    for i, x in enumerate(lon_flat):
        for j, y in enumerate(lat_flat):
            if geometry.contains(Point(x, y)):
                mask[j, i] = True
    return np.where(mask, data, np.nan)


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

colors = ['#ffffcc', '#ffeda0', '#fed976', '#feb24c', '#fd8d3c', '#fc4e2a', '#e31a1c', '#b10026']

bounds = [2, 5, 6, 7, 8,9,10,11]

custom_cmap = ListedColormap(colors)
norm = BoundaryNorm(boundaries=bounds, ncolors=len(colors) - 1, clip=True)

# Mask the data for each scenario and period
masked_data = {
    'ssp245_mid': mask_data(diff_ssp245_array_mid, longitudes, latitudes, combined_geom),
    'ssp370_mid': mask_data(diff_ssp370_array_mid, longitudes, latitudes, combined_geom),
    'ssp585_mid': mask_data(diff_ssp585_array_mid, longitudes, latitudes, combined_geom),
    'ssp245_end': mask_data(diff_ssp245_array_end, longitudes, latitudes, combined_geom),
    'ssp370_end': mask_data(diff_ssp370_array_end, longitudes, latitudes, combined_geom),
    'ssp585_end': mask_data(diff_ssp585_array_end, longitudes, latitudes, combined_geom)
}


titles = [
    '(a) SSP 2-4.5\n2041–2070',
    '(b) SSP 3-7.0\n2041–2070',
    '(c) SSP 5-8.5\n2041–2070',
    '(d) SSP 2-4.5\n2071–2100',
    '(e) SSP 3-7.0\n2071–2100',
    '(f) SSP 5-8.5\n2071–2100'
]

# ---- FINAL PRINT-SIZE FIGURE SETTINGS ----
FIG_WIDTH = 3.3   
FIG_HEIGHT = 4.8  # tune if needed

plt.rcParams.update({
    'font.size': 7.2,
    'font.family': 'Arial',
    'axes.titlesize': 7.6,
    'axes.titlepad': 2
})

fig, axes = plt.subplots(
    nrows=2, ncols=3,
    subplot_kw={'projection': ccrs.PlateCarree()},
    figsize=(FIG_WIDTH, FIG_HEIGHT)
)

plot_order = [
    'ssp245_mid', 'ssp370_mid', 'ssp585_mid',
    'ssp245_end', 'ssp370_end', 'ssp585_end'
]

# ---- draw panels ----
for ax, key, title in zip(axes.flat, plot_order, titles):
    im = ax.pcolormesh(
        longitudes, latitudes, masked_data[key],
        cmap=custom_cmap, norm=norm,
        shading='auto',
        transform=ccrs.PlateCarree()
    )

    ax.set_extent(extent_buffered, crs=ccrs.PlateCarree())
    ax.coastlines(linewidth=0.35)
    ax.add_feature(cfeature.BORDERS, linestyle=':', linewidth=0.35)

    # 2-line titles, smaller + tighter
    ax.set_title(title, pad=2)

    ax.add_geometries(
        subregion_geometries,
        crs=ccrs.PlateCarree(),
        edgecolor='black', facecolor='none',
        linewidth=0.45
    )

    # Gridlines: show labels only on left column & bottom row
    gl = ax.gridlines(draw_labels=True, linewidth=0.3,
                  color='gray', alpha=0.6, linestyle='--')

    gl.top_labels = False
    gl.right_labels = False
    
    # Latitude labels only on left column
    gl.left_labels = (ax in axes[:, 0])
    
    # Longitude labels on ALL bottom panels
    gl.bottom_labels = (ax in axes[1, :])
    
    # Make labels smaller so they don't collide between columns
    gl.xlabel_style = {'size': 5}
    gl.ylabel_style = {'size': 6}
    
    # Pull x labels a bit closer to the axis (reduces spillover)
    gl.xpadding = 1


fig.subplots_adjust(
    left=0.12, right=0.98,
    top=0.93, bottom=0.18,
    wspace=0.12,   # <-- increase from 0.05
    hspace=0.03
)

cax = fig.add_axes([0.10, 0.10, 0.85, 0.035])
cbar = fig.colorbar(im, cax=cax, orientation='horizontal')
cbar.set_ticks(bounds)
label_name = var_labels.get(var, var)
cbar.set_label(f"Differences in {label_name} (°F)", fontsize=8)
cbar.ax.xaxis.set_label_position('top')
cbar.ax.xaxis.set_ticks_position('bottom')
plt.savefig(plot_path, dpi=600)
plt.show()