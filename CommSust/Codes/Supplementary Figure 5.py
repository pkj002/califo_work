import matplotlib.pyplot as plt
import os
import numpy as np
import pandas as pd
import xarray as xr
import geopandas as gpd

'''
this script is same as 'plot_crop_county_long_term_chill_decline.py' script.
The only difference between these 2 is the former used monthly chill and produced 
sum of each month N+D+J+F but this script used NDJF sum directly from chill computation.
'''

# --- File paths (copy 'plot_data_published' directory inside path dir) ---
path = "path_to_project_root" 

#%% GRIDMET
read_path = os.path.join(path, 'plot_data_published', 'GRIDMET_chill_df_Figure2.npz')
chill_data = np.load(read_path)
chill_df = pd.DataFrame({
    'Longitude': chill_data['Longitude'],
    'Latitude': chill_data['Latitude'],
    'Year': chill_data['Year'],
    'Chill': chill_data['Chill']
})

# Load coordinate grid
ds = xr.open_dataset(os.path.join(path, 'plot_data_published', 'tmmx_1981.nc'))
lon_all = ds['lon'].values
lat_all = ds['lat'].values

ncf = xr.open_dataset(os.path.join(path, 'plot_data_published', 'tmmx_1982-2021_calif.nc'))
lon = ncf['lon'].values
lat = ncf['lat'].values

# Target years
years = np.arange(1980, 2025)
#%% --- Remap coordinates ---
def map_index_to_subset_index(global_idx, global_array, subset_array):
    val = global_array[global_idx]
    subset_idx = np.argmin(np.abs(subset_array - val))
    return subset_idx

new_chill_df = chill_df.copy()
new_chill_df['Longitude'] = new_chill_df['Longitude'].apply(lambda i: map_index_to_subset_index(i, lon_all, lon))
new_chill_df['Latitude'] = new_chill_df['Latitude'].apply(lambda i: map_index_to_subset_index(i, lat_all, lat))

years_unique = sorted(new_chill_df['Year'].unique())
year_to_index = {yr: idx for idx, yr in enumerate(years_unique)}
new_chill_df['Year_Index'] = new_chill_df['Year'].map(year_to_index)

lat_indices = new_chill_df['Latitude'].to_numpy(dtype=int)
lon_indices = new_chill_df['Longitude'].to_numpy(dtype=int)
year_indices = new_chill_df['Year_Index'].to_numpy(dtype=int)
chill_values = new_chill_df['Chill'].to_numpy()

#%% --- Initialize and fill chill array ---
new_chill_array = np.full((len(lat), len(lon), len(years_unique)), np.nan)

# Fill 3D array
for i, j, k, v in zip(lat_indices, lon_indices, year_indices, chill_values):
    new_chill_array[i, j, k] = v

print("Array shape:", new_chill_array.shape)
print("Total valid values:", np.sum(~np.isnan(new_chill_array)))
# ------------------------------
# Crop plotting info
# ------------------------------
crops = ['pista', 'walnut', 'cherry', 'plum']
crop_labels = ['(a) Pistachio', '(b) Walnut', '(c) Cherry', '(d) Plum']

threshold_ranges = {
    'pista': (36, 65),
    'walnut': (38, 54),
    'cherry': (30, 70),
    'plum': (55, 60)
}

median_values = {
    'cherry': np.median([37, 50.5, 30, 35, 58, 54, 45, 48, 70, 48]),
    'pista': np.median([56, 36, 61.5, 60]),
    'plum': np.median([57.5]),
    'walnut': np.median([47.5, 54, 38])
}

years_unique = list(range(1980, 2025))  # same as crop_timeseries keys

# Load California shapefile
shapefile_path = os.path.join(path, 'plot_data_published', 'SHP', 'CA_county.shp')
california = gpd.read_file(shapefile_path)

# Define crops, order, and counties
crop_county = {
    "pista": ['Kern', 'Tulare', 'Fresno', 'Madera', 'Merced', 'Kings'],
    "walnut": ['San Joaquin', 'Butte', 'Sutter', 'Stanislaus', 'Tulare', 'Glenn'],
    "cherry": ['San Joaquin', 'Stanislaus', 'Fresno', 'Kern', 'Merced', 'Kings'],
    "plum": ['Fresno', 'Tulare', 'Kings', 'Kern', 'Madera', 'Merced'],
}
crops = ['pista', 'walnut', 'cherry', 'plum']
crop_labels = ['(a) Pistachio', '(b) Walnut', '(c) Cherry', '(d) Plum']

# Function
def extract_mean_timeseries(array_3d, lat_inds, lon_inds):
    series = []
    for t in range(array_3d.shape[2]):
        vals = [array_3d[i, j, t] for i, j in zip(lat_inds, lon_inds)]
        series.append(np.nanmean(vals))
    return series

# Plot panel for 4 crops
plt.rcParams['font.family'] = 'Arial'
plt.rcParams['font.size'] = 16
fig, axes = plt.subplots(2, 2, figsize=(16, 12), sharex=True, sharey=True)
axes = axes.flatten()
years_list = years  # from your new_chill_array setup

for ax_idx, crop in enumerate(crops):
    crop_label = crop_labels[ax_idx]
    counties = crop_county[crop]
    ax = axes[ax_idx]

    # --- Plot county-level mean chill timeseries ---
    for county_name in counties:
        county_geom = california[california['ADM2_NAME'] == county_name].geometry.values[0]
        minx, miny, maxx, maxy = county_geom.bounds

        # Select all points in county
        lat_inds = [i for i, la in enumerate(lat) if miny <= la <= maxy]
        lon_inds = [j for j, lo in enumerate(lon) if minx <= lo <= maxx]

        if len(lat_inds) == 0 or len(lon_inds) == 0:
            print(f"No points found in {county_name} for {crop}")
            continue

        # Build mesh of all lat/lon indices
        mesh_lat_lon = [(i, j) for i in lat_inds for j in lon_inds]
        ts = extract_mean_timeseries(new_chill_array, [i for i,j in mesh_lat_lon], [j for i,j in mesh_lat_lon])
        ax.plot(years_list, ts, label=county_name, linewidth=2)

    # Threshold shading
    if crop in threshold_ranges:
        lower, upper = threshold_ranges[crop]
        ax.fill_between(years_list, lower, upper, color='gray', alpha=0.15, label='Threshold Range')

    # Median line
    if crop in median_values:
        ax.axhline(y=median_values[crop], color='red', linestyle='--', linewidth=1.5, label='Median')

    ax.set_title(crop_label, loc='left', fontsize=18)
    ax.set_xlabel('Year', fontsize=16)
    ax.set_ylabel('Chill Portions', fontsize=16)
    ax.grid(True)

# Shared legend
handles, labels = [], []
for ax in axes:
    h, l = ax.get_legend_handles_labels()
    for hh, ll in zip(h, l):
        if ll not in labels:
            handles.append(hh)
            labels.append(ll)

fig.legend(handles, labels, loc='lower center', ncol=7, bbox_to_anchor=(0.5, -0.005), fontsize=12, frameon=False)
plt.tight_layout(rect=[0, 0.03, 1, 0.98])
save_dir = os.path.join(path, 'plots')
os.makedirs(save_dir, exist_ok=True)
plt.savefig(os.path.join(save_dir,'Supplementary Figure 5tes.png'), dpi=300)
plt.show()
#%%
