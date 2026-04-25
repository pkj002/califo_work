# -*- coding: utf-8 -*-
"""
Created on Sat Mar  8 11:11:09 2025

@author: Prakash
"""
import geopandas as gpd
import numpy as np
import xarray as xr
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.lines as mlines

# Define the path to the data
path = r'C:\Users\Prakash\Box\Sierra_Nevada_Regional_Report_Pre_Publication\chapter2_climate\metadata'
outdir = 'where you want to save the Figure'

# Load the data
tmx_data = np.load(path + '/arrays_climatology_data_bar_plot_tasmax.npz')
tmin_data = np.load(path + '/arrays_climatology_data_bar_plot_tasmin.npz')

hist2 = (tmx_data['hist2'] + tmin_data['hist2'])/2

# mid century
ssp245_mid = (tmx_data['ssp245_mid'] + tmin_data['ssp245_mid'])/2
ssp370_mid = (tmx_data['ssp370_mid'] + tmin_data['ssp370_mid'])/2
ssp585_mid = (tmx_data['ssp585_mid'] + tmin_data['ssp585_mid'])/2 

# end
ssp245_end = (tmx_data['ssp245_end'] + tmin_data['ssp245_end'])/2
ssp370_end = (tmx_data['ssp370_end'] + tmin_data['ssp370_end'])/2
ssp585_end = (tmx_data['ssp585_end'] + tmin_data['ssp585_end'])/2 

## array in ssp370 has shape (227,160). Pad it
# Given shape (227, 160), target shape (227, 192)
target_shape = hist2.shape

# Calculate padding size
pad_width = target_shape[1] - ssp370_mid.shape[1]  # 192 - 160 = 32

# Pad with NaNs along the second dimension (right side)
ssp370_mid_padded = np.pad(ssp370_mid, ((0, 0), (0, pad_width)), mode='constant', constant_values=np.nan)
ssp370_end_padded = np.pad(ssp370_end, ((0, 0), (0, pad_width)), mode='constant', constant_values=np.nan)

# Load shapefile for regions
shapefile = gpd.read_file(path + '/CC5a_Regions/CC5a_RegionsSub.shp').dropna(subset=['subregion']).to_crs('EPSG:4326')

# Define the regions to mask
regions_to_mask = ["N Sierra", "NE Sierra", "S Sierra", "SE Sierra"]
subregion_geometries = shapefile[shapefile['subregion'].isin(regions_to_mask)]

# Prepare a list to store results
clipped_results = []

# List of data arrays (periods)
data_arrays = [hist2, ssp245_mid, ssp370_mid_padded, ssp585_mid,ssp245_end,ssp370_end_padded,ssp585_end]
period_names = ['hist2', 'ssp245_mid', 'ssp370_mid','ssp585_mid', 'ssp245_end', 'ssp370_end', 'ssp585_end']
    
# Get lon/lat from external file
data1 = np.load(path + '/pr_data.npz')
lon = data1['longitudes']
lat = data1['latitudes']

# Loop through each dataset (period)
for data, period_name in zip(data_arrays, period_names):
    # Create the xarray without 'time' if it's just spatial data
    averaged_data = xr.DataArray(data, dims=['y', 'x'], coords={'y': lat, 'x': lon})
    
    # Check the dimensions and coordinates of the DataArray
    print(f"Dimensions of {period_name} dataset: {averaged_data.dims}")
   
    # Check if the CRS is already assigned, if not, assign it
    if not averaged_data.rio.crs:
        print(f"Assigning CRS to averaged data for period: {period_name}")
        averaged_data = averaged_data.rio.write_crs("EPSG:4326")  # Assuming WGS84 (EPSG:4326). Adjust if necessary.
    
    # Explicitly set spatial dimensions
    averaged_data = averaged_data.rio.set_spatial_dims(x_dim='x', y_dim='y')

    # Loop through each subregion and perform clipping and statistics
    for subregion_name in regions_to_mask:
        # Filter the GeoDataFrame for the current subregion
        subregion = subregion_geometries[subregion_geometries['subregion'] == subregion_name]
        
        if not subregion.empty:
            print(f"Clipping {period_name} for subregion: {subregion_name}")
            
            # Extract geometry for clipping
            geometry = subregion['geometry']
            
            # Perform clipping
            clipped_data = averaged_data.rio.clip(geometry.values, subregion.crs, drop=True)
            
            if clipped_data is not None:
                # Calculate statistics
                mean_val = clipped_data.mean().item()
                max_val = clipped_data.max().item()
                min_val = clipped_data.min().item()
                
                # Append results
                clipped_results.append({
                    'period': period_name,
                    'subregion': subregion_name,
                    'mean': mean_val,
                    'max': max_val,
                    'min': min_val
                })

# Convert the results into a DataFrame for further analysis or export
clipped_results_df = pd.DataFrame(clipped_results)

clipped_results_df = pd.DataFrame(clipped_results)

# Create separate dataframes for mean, max, and min with the custom row order
# Drop the 'subregion' column and reorder based on 'period_order'
df_mean = clipped_results_df.pivot(index='period', columns='subregion', values='mean').reindex(period_names)
df_max = clipped_results_df.pivot(index='period', columns='subregion', values='max').reindex(period_names)
df_min = clipped_results_df.pivot(index='period', columns='subregion', values='min').reindex(period_names)

# Convert to NumPy arrays
data_avg = df_mean.to_numpy()
data_max = df_max.to_numpy()
data_min = df_min.to_numpy()

# Define the custom order for periods
custom_order = [
    'historical_1981-2010',
    'future_2041-2070_ssp245',
    'future_2071-2100_ssp245',
    'future_2041-2070_ssp370',
    'future_2071-2100_ssp370',
    'future_2041-2070_ssp585',
    'future_2071-2100_ssp585'
]

# Convert custom_order to lowercase
custom_order_lower = [period.lower() for period in custom_order]

# Mapping original period names to custom periods
period_mapping = {
    'hist2': 'historical_1981-2010',
    'ssp245_mid': 'future_2041-2070_ssp245',
    'ssp245_end': 'future_2071-2100_ssp245',
    'ssp370_mid': 'future_2041-2070_ssp370',
    'ssp370_end': 'future_2071-2100_ssp370',
    'ssp585_mid': 'future_2041-2070_ssp585',
    'ssp585_end': 'future_2071-2100_ssp585'
}

# Define the data
ticks = [
    'Historical\n1981-2010',
    '2041-70\nSSP 2-4.5',
    '2071-00\nSSP 2-4.5',
    '2041-70\nSSP 3-7.0',
    '2071-00\nSSP 3-7.0',
    '2041-70\nSSP 5-8.5',
    '2071-00\nSSP 5-8.5'
]

# -----------------------------
# Subregions and colors
# -----------------------------
subregions = ["Northern Sierra Nevada", "Northeastern Sierra Nevada", 
              "Southern Sierra Nevada", "Southeastern Sierra Nevada"]
colors = ['#1f77b4', '#ff7f0e', '#d62728', '#7f7f7f']  # Colorblind-friendly palette

# Define bar width and positions
bar_width = 0.114  # Reduced width
index = np.array([0, 1.5, 2.5, 4, 5, 6.5, 7.5])  # 8 tick positions

# -----------------------------
# PRINT-SAFE FIGURE SETTINGS
# -----------------------------
FIG_W = 8.0      # inches (A4 full-width should not exceed 8")
FIG_H = 4.8      # inches (adjust if you want more height)
DPI  = 600       # keep 600 if required

# Font sizes tuned for an 8-inch wide print figure
BASE = 10
plt.rcParams.update({
    'font.family': 'Arial',
    'font.size': BASE,
    'axes.labelsize': BASE + 1,
    'xtick.labelsize': BASE,
    'ytick.labelsize': BASE,
    'legend.fontsize': BASE,
})

fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))

# -----------------------------
# Bars + average notches
# -----------------------------
bar_width = 0.16
index = np.arange(len(ticks))  # evenly spaced categories (print-stable)

# Use a little separation between the 4 bars in each group
offsets = (np.arange(len(subregions)) - (len(subregions)-1)/2) * (bar_width + 0.02)

for i, subregion in enumerate(subregions):
    x = index + offsets[i]

    bars = ax.bar(
        x,
        data_max[:, i] - data_min[:, i],
        width=bar_width,
        bottom=data_min[:, i],
        color=colors[i],
        edgecolor='black',
        linewidth=0.6,
        zorder=2
    )

    # Average "notch" line
    for xi, avg in zip(x, data_avg[:, i]):
        ax.plot([xi - bar_width*0.45, xi + bar_width*0.45],
                [avg, avg],
                color=colors[i],
                linewidth=3,
                solid_capstyle='butt',
                zorder=3)

# -----------------------------
# Axes formatting
# -----------------------------
ax.set_ylabel('Temperature (°F)')
ax.set_xticks(index)
ax.set_xticklabels(ticks, ha='center')
ax.margins(x=0.02)

# Y limits with padding
min_y = np.nanmin(data_min) - 1
max_y = np.nanmax(data_max)
ax.set_ylim(min_y, max_y + (max_y - min_y) * 0.08)

# Light grid helps reading at print size
ax.grid(axis='y', linestyle='--', linewidth=0.5, alpha=0.5, zorder=1)

# -----------------------------
# Legend (compact, print-safe)
# -----------------------------
legend_handles = [mlines.Line2D([0], [0], color=c, lw=4, label=s)
                  for c, s in zip(colors, subregions)]

ax.legend(
    handles=legend_handles,
    loc='upper left',
    bbox_to_anchor=(0.0, 1.02),
    ncol=2,
    frameon=False,
    columnspacing=1.0,
    handletextpad=0.5
)

# -----------------------------
# Layout + save
# -----------------------------
fig.tight_layout(pad=0.6)

# Optional: print the final physical size 
w, h = fig.get_size_inches()
print(f"Saved figure physical size: {w:.2f} in × {h:.2f} in at {DPI} dpi")

# -----------------------------
# Verify final figure size
# -----------------------------
fig_width, fig_height = fig.get_size_inches()

save_dpi = 600  # same value used in savefig

pixel_width = fig_width * save_dpi
pixel_height = fig_height * save_dpi

output_file = outdir + '/new_bar_temperature_all_models_3SSPs1.png'
fig.savefig(output_file, dpi=DPI, bbox_inches='tight')
plt.show()