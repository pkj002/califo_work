# -*- coding: utf-8 -*-
"""
Created on Sat Mar  8 13:04:50 2025

@author: Prakash
"""
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.ticker as mticker
import os
import string
import matplotlib as mpl

# Define paths
data_path = 'path of the "metadata" dir'
#data_path = r'C:\Users\Prakash\Box\Sierra_Nevada_Regional_Report_Pre_Publication\chapter2_climate\metadata'
outdir = 'where you want to save the Figure'
shapefile_path = data_path + '/CC5a_Regions/CC5a_RegionsSub.shp'

# Load latitude and longitude data from one historical file
data3 = np.load(data_path + '/VIC/soil_moisture/seasonal_means_CNRM-ESM2-1_historical.npz')
longitudes = data3['lon']
latitudes = data3['lat']

# Define extent based on valid data and the new longitude range
long_min, long_max = -122.484375, -117.5
lat_min, lat_max = 34.8, 42.1

# Load the shapefile
shapefile = gpd.read_file(shapefile_path)
target_crs = 'EPSG:4326'
shapefile = shapefile.to_crs(target_crs)

# Define the models and seasons
models = ["EC-Earth3-Veg", "MPI-ESM1-2-HR"]
seasons = ['DJF', 'MAM', 'JJA', 'SON']

# Initialize data dictionary
data = {}
# Only scenarios that actually exist
available_ssps = ["ssp245", "ssp370", "ssp585"]

# Define color bounds and colors
bounds = [-40, -30, -20, -10, -5, 0, 5, 10, 20, 30, 40]
colors = ['#67001f', '#b2182b', '#d6604d', '#f4a582', '#f7f7f7', 
          '#f7f7f7', '#d1e5f0', '#92c5de', '#4393c3', '#2166ac', '#053061']
custom_cmap = ListedColormap(colors)
norm = BoundaryNorm(boundaries=bounds, ncolors=len(colors), clip=True)

# Loop through SSP scenarios and periods
# --- Step 1: Precompute multimodel averages outside plotting ---
# Define scenarios
scenarios = [
    ('ssp245', '2041-2070'),
    ('ssp245', '2071-2100'),
    ('ssp370', '2041-2070'),
    ('ssp370', '2071-2100'),
    ('ssp585', '2041-2070'),
    ('ssp585', '2071-2100'),
]

seasons = ['DJF', 'MAM', 'JJA', 'SON']

# -----------------------------
# Load shapefile and filter regions
# -----------------------------
shapefile = gpd.read_file(shapefile_path).to_crs('EPSG:4326')

regions_to_mask = ["N Sierra", "NE Sierra", "S Sierra", "SE Sierra"]
subregion_df = shapefile.loc[shapefile['subregion'].isin(regions_to_mask)]

# Subtitle letters for up to 12 panels
subtitle_letters = [f"({c})" for c in string.ascii_lowercase[:12]]

# Mapping SSP codes to pretty labels
ssp_labels = {
    'ssp245': 'SSP 2-4.5',
    'ssp370': 'SSP 3-7.0',
    'ssp585': 'SSP 5-8.5'
}

# -----------------------------
# Plot: A4 PORTRAIT-ready 3x4 panel map
# -----------------------------
period = '2071-2100'
ssps = ['ssp245', 'ssp370', 'ssp585']
seasons = ['DJF', 'MAM', 'JJA', 'SON']

# A4 portrait in inches
A4_W, A4_H = 8.27, 11.69

# Global font settings (portrait + 12 panels)
base_fs = 11
mpl.rcParams.update({
    "font.family": "Arial",
    "font.size": base_fs,
    "axes.titlesize": base_fs + 2,
    "axes.labelsize": base_fs,
})

fig, axes = plt.subplots(
    nrows=3, ncols=4,
    figsize=(A4_W, A4_H),
    subplot_kw={'projection': ccrs.PlateCarree()}
)

# Gridline tick locations
xticks = np.arange(-122, -117, 1)  # -122, -121, ... -118
yticks = np.arange(35, 43, 1)      # 35..42

panel_idx = 0
im = None  # mappable for colorbar

for i, ssp in enumerate(ssps):
    file_path = data_path + '/VIC/soil_moisture/precomputed/' + f"precomputed_multimodel_{ssp}_{period}.npz"
    npz = np.load(file_path)

    for j, season in enumerate(seasons):
        ax = axes[i, j]

        # NPZ contains precomputed multi-model mean for each season
        season_avg = npz[season]

        im = ax.pcolormesh(
            longitudes, latitudes, season_avg,
            cmap=custom_cmap, norm=norm, shading='auto',
            transform=ccrs.PlateCarree()
        )

        ax.set_extent([long_min, long_max, lat_min, lat_max], crs=ccrs.PlateCarree())
        ax.coastlines(linewidth=0.5)
        ax.add_feature(cfeature.BORDERS, linestyle=':', linewidth=0.4)
        ax.add_geometries(
            subregion_df['geometry'], crs=ccrs.PlateCarree(),
            edgecolor='black', facecolor='none', linewidth=0.5
        )

        # Gridlines with labels only on outer edges
        gl = ax.gridlines(
            crs=ccrs.PlateCarree(),
            draw_labels=True,
            linewidth=0.35,
            color='gray',
            alpha=0.6,
            linestyle='--'
        )
        gl.xlocator = mticker.FixedLocator(xticks)
        gl.ylocator = mticker.FixedLocator(yticks)

        gl.top_labels = False
        gl.right_labels = False
        gl.left_labels = (j == 0)
        gl.bottom_labels = (i == 2)

        gl.xlabel_style = {"size": base_fs}
        gl.ylabel_style = {"size": base_fs}

        # Panel title
        ax.set_title(f"{subtitle_letters[panel_idx]} {ssp_labels[ssp]} {season}",
             pad=4, fontsize=base_fs+2)
        panel_idx += 1

# ----- Colorbar (single, horizontal) -----
# Figure coords: [left, bottom, width, height]
cbar_ax = fig.add_axes([0.17, 0.055, 0.66, 0.02])
cbar = fig.colorbar(im, cax=cbar_ax, orientation='horizontal')

cbar.set_label('% Soil Moisture Change',
               fontsize=base_fs+2,
               labelpad=8)

cbar.ax.tick_params(labelsize=base_fs)

# ----- Layout tuning for A4 portrait -----
fig.subplots_adjust(
    left=0.08, right=0.99,
    top=0.96, bottom=0.11,
    wspace=0.03, hspace=0.065
)

# Save figure 
plot_path = os.path.join(data_path, f"multimodel_soil_moisture_SN_{period}_A4_portrait.png")
plt.savefig(plot_path, dpi=600, bbox_inches='tight')
plt.show()