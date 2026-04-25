# -*- coding: utf-8 -*-
"""
Created on Sat Mar  8 11:11:09 2025
@author: Prakash
"""
import geopandas as gpd
import numpy as np
import xarray as xr
import rioxarray
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import os

# -----------------------------
# Figure size requirements
# -----------------------------
FIG_W_IN = 8.0         
FIG_H_IN = 4.8          
SAVE_DPI = 600

# -----------------------------
# Define the path to the data
# -----------------------------
path = 'path of the "metadata" dir'
#path = r'C:\Users\Prakash\Box\Sierra_Nevada_Regional_Report_Pre_Publication\chapter2_climate\metadata'
outdir = 'where you want to save the Figure'

# Load the data
main_data = np.load(os.path.join(path, 'arrays_climatology_data_bar_plotpr.npz'))
hist1 = main_data['hist1']
hist2 = main_data['hist2']
ssp245_mid = main_data['ssp245_mid']
ssp370_mid = main_data['ssp370_mid']
ssp585_mid = main_data['ssp585_mid']
ssp245_end = main_data['ssp245_end']
ssp370_end = main_data['ssp370_end']
ssp585_end = main_data['ssp585_end']

# Pad SSP370 arrays to match hist2
target_shape = hist2.shape
pad_width = target_shape[1] - ssp370_mid.shape[1]
ssp370_mid_padded = np.pad(ssp370_mid, ((0, 0), (0, pad_width)), mode='constant', constant_values=np.nan)
ssp370_end_padded = np.pad(ssp370_end, ((0, 0), (0, pad_width)), mode='constant', constant_values=np.nan)

# Load shapefile for regions
shapefile = gpd.read_file(os.path.join(path, 'CC5a_Regions', 'CC5a_RegionsSub.shp')).dropna(subset=['subregion']).to_crs('EPSG:4326')
regions_to_mask = ["N Sierra", "NE Sierra", "S Sierra", "SE Sierra"]
subregion_geometries = shapefile[shapefile['subregion'].isin(regions_to_mask)]

clipped_results = []

data_arrays = [hist1, hist2, ssp245_mid, ssp370_mid_padded, ssp585_mid, ssp245_end, ssp370_end_padded, ssp585_end]
period_names = ['hist1', 'hist2', 'ssp245_mid', 'ssp370_mid', 'ssp585_mid', 'ssp245_end', 'ssp370_end', 'ssp585_end']

data1 = np.load(os.path.join(path, 'pr_data.npz'))
lon = data1['longitudes']
lat = data1['latitudes']

for data, period_name in zip(data_arrays, period_names):
    averaged_data = xr.DataArray(data, dims=['y', 'x'], coords={'y': lat, 'x': lon})

    if not averaged_data.rio.crs:
        averaged_data = averaged_data.rio.write_crs("EPSG:4326")
    averaged_data = averaged_data.rio.set_spatial_dims(x_dim='x', y_dim='y')

    for subregion_name in regions_to_mask:
        subregion = subregion_geometries[subregion_geometries['subregion'] == subregion_name]
        if subregion.empty:
            continue

        clipped_data = averaged_data.rio.clip(subregion['geometry'].values, subregion.crs, drop=True)
        if clipped_data is None:
            continue

        clipped_results.append({
            'period': period_name,
            'subregion': subregion_name,
            'mean': clipped_data.mean().item(),
            'max': clipped_data.max().item(),
            'min': clipped_data.min().item()
        })

clipped_results_df = pd.DataFrame(clipped_results)

df_mean = clipped_results_df.pivot(index='period', columns='subregion', values='mean').reindex(period_names)
df_max  = clipped_results_df.pivot(index='period', columns='subregion', values='max').reindex(period_names)
df_min  = clipped_results_df.pivot(index='period', columns='subregion', values='min').reindex(period_names)

data_avg = df_mean.to_numpy()
data_max = df_max.to_numpy()
data_min = df_min.to_numpy()

# Drop first period to match 7 ticks (remove hist1)
data_min = data_min[1:, :]
data_max = data_max[1:, :]
data_avg = data_avg[1:, :]

ticks = [
    'Historical\n1981-2010',
    '2041-70\nSSP 2-4.5',
    '2071-00\nSSP 2-4.5',
    '2041-70\nSSP 3-7.0',
    '2071-00\nSSP 3-7.0',
    '2041-70\nSSP 5-8.5',
    '2071-00\nSSP 5-8.5'
]

subregions = ["Northern Sierra Nevada", "Northeastern Sierra Nevada",
              "Southern Sierra Nevada", "Southeastern Sierra Nevada"]
colors = ['#1f77b4', '#ff7f0e', '#d62728', '#7f7f7f']

bar_width = 0.114
index = np.array([0, 1.4, 2.6, 4.0, 5.2, 6.5, 7.7])

# -----------------------------
# Fonts 
# -----------------------------
# -----------------------------
base = 12          # overall default
xtick_fs = 10      # x tick labels
ytick_fs = 11      # y tick labels
legend_fs = 10     # legend text
ylabel_fs = 12     # y-axis label

plt.rcParams.update({
    'font.family': 'Arial',
    'font.size': base,
    'axes.titlesize': base,
    'axes.labelsize': ylabel_fs,
    'xtick.labelsize': xtick_fs,
    'ytick.labelsize': ytick_fs,
    'legend.fontsize': legend_fs
})
# -----------------------------
# Create the plot at compliant size
# -----------------------------
fig, ax = plt.subplots(figsize=(FIG_W_IN, FIG_H_IN))

for i, subregion in enumerate(subregions):
    bar_positions = index + i * bar_width - 1.5 * bar_width
    bars = ax.bar(
        bar_positions,
        data_max[:, i] - data_min[:, i],
        bar_width,
        bottom=data_min[:, i],
        color=colors[i],
        edgecolor='black'
    )
    # avg line
    for bar, avg in zip(bars, data_avg[:, i]):
        bar_center = bar.get_x() + bar.get_width() / 2
        half_notch = bar.get_width() / 2
        ax.plot(
            [bar_center - half_notch, bar_center + half_notch],
            [avg, avg],
            color=colors[i],
            linewidth=6,
            zorder=5
        )


legend_handles = [mlines.Line2D([0], [0], color=c, lw=4, label=s)
                  for c, s in zip(colors, subregions)]
ax.set_ylabel('Annual Precipitation (inches)', fontsize=ylabel_fs)

leg = ax.legend(
    handles=legend_handles,
    loc='upper left',
    bbox_to_anchor=(0, 1.03),
    ncol=2,
    columnspacing=0.8,
    handletextpad=0.4,
    frameon=False
)
# Optional: shrink legend line symbols a bit
for h in leg.legend_handles:
    h.set_linewidth(3)
    
ax.set_xticks(index)
ax.set_xticklabels(ticks, rotation=0, ha='center')

min_y = np.nanmin(data_min) - 1
max_y = np.nanmax(data_max)
ax.set_ylim(min_y, max_y + (max_y - min_y) * 0.1)

# Make room for legend above axes while keeping a tight figure
fig.subplots_adjust(left=0.10, right=0.98, bottom=0.18, top=0.82)

# -----------------------------
# Save + print size check
# -----------------------------
output_file = os.path.join(outdir, 'Figure_2.6.png')
plt.savefig(output_file, dpi=SAVE_DPI, bbox_inches='tight')
plt.show()
#%%