import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os
import xarray as xr
from scipy.stats import linregress

def plot_trend(ax, x, y, color, label):
    x = np.array(x)
    y = np.array(y)
    mask = ~np.isnan(y)
    slope, intercept, r, p, stderr = linregress(x[mask], y[mask])
    ax.plot(
        x,
        intercept + slope * x,
        color=color,
        linewidth=1.5,
        alpha=0.9,
        label=label
    )
    return slope, intercept, p

#CMIP6
# --- File paths (copy 'plot_data_published' directory inside path dir) ---
path = "path_to_project_root" 
chill_historical = np.load(os.path.join(path, "plot_data_published/cmip6_chill_historical.npy"))
chill_ssp585 = np.load(os.path.join(path, "plot_data_published/cmip6_chill_ssp585.npy"))

latlon = pd.read_csv(os.path.join(path, 'plot_data_published/cmip6_loca2_lat_lon.csv'))
lat_model = latlon['lat'].dropna().values
lon_model = latlon['lon'].dropna().values
#%% GRIDMET
#read_path = os.path.join(path, 'plot_data_published/calif_chill_df_combined_see_script_plot_chill_diff.npz')
read_path = os.path.join(path, 'plot_data_published/GRIDMET_chill_df_Figure2.npz')
#read_path = '/glade/work/prajha/data/GRIDMET/gridmet_chill/calif_chill_df_combined_see_script_plot_chill_diff.npz'
chill_data = np.load(read_path)
chill_df = pd.DataFrame({
    'Longitude': chill_data['Longitude'],
    'Latitude': chill_data['Latitude'],
    'Year': chill_data['Year'],
    'Chill': chill_data['Chill']
})

ds = xr.open_dataset(os.path.join(path, 'plot_data_published/tmmx_1981.nc'))
# Extract 'lon' and 'lat' coordinates
lon_all = ds['lon'].values
lat_all = ds['lat'].values
#%% make chill array from chill_df
# Path to the NetCDF file
ncf = xr.open_dataset(os.path.join(path, 'plot_data_published/tmmx_1982-2021_calif.nc'))

# Extract valid latitudes and longitudes from NetCDF file
lon = ncf['lon'].values # Ensure consistent precision
lat = ncf['lat'].values

# Target years
years = np.arange(1980, 2025)  # From 1980 to 2024

def map_index_to_subset_index(global_idx, global_array, subset_array):
    val = global_array[global_idx]
    subset_idx = np.argmin(np.abs(subset_array - val))
    return subset_idx

# Create the new DataFrame with remapped indices
new_chill_df = chill_df.copy()
new_chill_df['Longitude'] = new_chill_df['Longitude'].apply(lambda i: map_index_to_subset_index(i, lon_all, lon))
new_chill_df['Latitude'] = new_chill_df['Latitude'].apply(lambda i: map_index_to_subset_index(i, lat_all, lat))

# Step 1: Get the unique year list (and ensure sorting)
years = sorted(new_chill_df['Year'].unique())
year_to_index = {year: idx for idx, year in enumerate(years)}

# Step 2: Add Year_Index column
new_chill_df['Year_Index'] = new_chill_df['Year'].map(year_to_index)

# Step 3: Extract numpy arrays of indices and values
lat_indices = new_chill_df['Latitude'].to_numpy(dtype=int)
lon_indices = new_chill_df['Longitude'].to_numpy(dtype=int)
year_indices = new_chill_df['Year_Index'].to_numpy(dtype=int)
chill_values = new_chill_df['Chill'].to_numpy()

# Step 4: Initialize the 3D array
new_chill_array = np.full(
    (len(np.unique(lat_indices)), len(np.unique(lon_indices)), len(years)),
    np.nan
)

# Step 5: Assign values
new_chill_array[lat_indices, lon_indices, year_indices] = chill_values
#%%
# Inputs
crops = ['pista', 'walnut', 'cherry', 'plum']

# source: https://ucanr.edu/site/fruit-nut-research-information-center/fruit-nut-crop-chill-portions-requirements
# the thresholds values are average of all varieties available in the web page
thresholds = {'pista': 55, 'walnut': 47, 'cherry': 48, 'plum': 58}

years_hist = list(range(1981, 2015))
years_fut = list(range(2015, 2041))
years_obs = list(range(1979, 2024))  # 45 years for observational dataset

# Find lat indices < 37° for the model grid
lat_mask_model = lat_model < 37
lat_indices_below_37_model = np.where(lat_mask_model)[0]

# Find lat indices < 37° for the obs grid
lat_mask_obs = lat < 37
lat_indices_below_37_obs = np.where(lat_mask_obs)[0]

# Median values for each crop (from variety data)
median_values = {
    'cherry': [37, 50.5, 30, 35, 58, 54, 45, 48, 70, 48],  # median of ranges where applicable
    'pista': [56, 36, 61.5, 60],  # Kerman(54-58)->56, Mateu 36, Peters(58-65)->61.5, Sirora 60
    'plum': [57.5],  # 55-60
    'walnut': [47.5, 54, 38]  # Chandler(45-50)->47.5, Hartley 54, Payne 38
}

# Improved thresholds as ranges
threshold_ranges = {
    'pista': (36, 65),
    'walnut': (38, 54),
    'cherry': (30, 70),
    'plum': (55, 60)
}

crop_labels = ['(a) Pistachio', '(b) Walnut', '(c) Cherry', '(d) Plum']

# Setup figure
# Median values for each crop (from variety data)
# Compute median of each crop (species) from all cultivar values
median_values = {
    'cherry': np.median([37, 50.5, 30, 35, 58, 54, 45, 48, 70, 48]),
    'pista': np.median([56, 36, 61.5, 60]),  # median of all cultivars
    'plum': np.median([57.5]),
    'walnut': np.median([47.5, 54, 38])
}

# Threshold ranges
threshold_ranges = {
    'pista': (36, 65),
    'walnut': (38, 54),
    'cherry': (30, 70),
    'plum': (55, 60)
}

crop_labels = ['(a) Pistachio', '(b) Walnut', '(c) Cherry', '(d) Plum']

plt.rcParams.update({
    'font.size': 18,          # set default font size
    'font.family': 'Arial'    # set default font to Arial
})
fig, axes = plt.subplots(nrows=2, ncols=2, figsize=(16, 12), sharex=True, sharey=True)
axes = axes.flatten()

for idx, crop in enumerate(crops):
    label = crop_labels[idx]
    crop_latlon = pd.read_csv(os.path.join(path, 'plot_data_published', f'{crop}_lat_lon_in_Calif.csv'))
    
    # Filter points below 37
    crop_latlon_below_37 = crop_latlon[crop_latlon['lat'] < 37]
    if crop_latlon_below_37.empty:
        print(f"No valid points for {crop} below 37°N. Skipping.")
        continue

    # Model historical & future indices
    i_inds_model = [np.abs(lat_model - lat_val).argmin() for lat_val in crop_latlon_below_37['lat']]
    j_inds_model = [np.abs(lon_model - lon_val).argmin() for lon_val in crop_latlon_below_37['lon']]
    valid_model_pts = [(i, j) for i, j in zip(i_inds_model, j_inds_model) if i in lat_indices_below_37_model]
    if not valid_model_pts:
        print(f"No valid model grid cells for {crop} below 37°N. Skipping.")
        continue
    i_inds_model, j_inds_model = zip(*valid_model_pts)

    chill_hist_vals = [
        np.nanmean([chill_historical[i, j, yr] for i, j in zip(i_inds_model, j_inds_model)])
        for yr in range(len(years_hist))
    ]
    chill_fut_vals = [
        np.nanmean([chill_ssp585[i, j, yr] for i, j in zip(i_inds_model, j_inds_model)])
        for yr in range(len(years_fut))
    ]

    # Observational data
    i_inds_obs = [np.abs(lat - lat_val).argmin() for lat_val in crop_latlon_below_37['lat']]
    j_inds_obs = [np.abs(lon - lon_val).argmin() for lon_val in crop_latlon_below_37['lon']]
    valid_obs_pts = [(i, j) for i, j in zip(i_inds_obs, j_inds_obs) if i in lat_indices_below_37_obs]
    if not valid_obs_pts:
        chill_obs_vals = [np.nan] * len(years_obs)
    else:
        i_inds_obs, j_inds_obs = zip(*valid_obs_pts)
        chill_obs_vals = [
            np.nanmean([new_chill_array[i, j, yr] for i, j in zip(i_inds_obs, j_inds_obs)])
            for yr in range(len(years_obs))
        ]

    ax = axes[idx]
    # ---- Trend lines (NEW) ----
    slope_obs, int_obs, p_obs = plot_trend(
        ax, years_obs, chill_obs_vals, 'blue', 'Obs trend'
    )
    
    slope_hist, int_hist, p_hist = plot_trend(
        ax, years_hist, chill_hist_vals, 'black', 'CMIP6 Hist trend'
    )
    
    slope_fut, int_fut, p_fut = plot_trend(
        ax, years_fut, chill_fut_vals, 'green', 'Future trend'
    )

    # ---- Trend-based threshold crossing year (NEW) ----
    if crop in median_values and slope_fut < 0:
        median = median_values[crop]
        cross_year = (median - int_fut) / slope_fut
    
        if years_fut[0] <= cross_year <= years_fut[-1]:
            print(f"{crop.capitalize()} trend crosses median chill (~{median}) around year {int(cross_year)}")

    # Plot data
    ax.plot(years_obs, chill_obs_vals, marker='x', linestyle='-', color='blue', markersize=4, linewidth=1.2, label='GRIDMET (Obs)')
    ax.plot(years_hist, chill_hist_vals, marker='^', linestyle='--', color='black', markersize=4, linewidth=1.2, label='Historical')
    ax.plot(years_fut, chill_fut_vals, marker='^', linestyle='-', color='green', markersize=4, linewidth=1.2, label='Future (SSP585)')

    # Threshold shading & upper line
    if crop in threshold_ranges:
        lower, upper = threshold_ranges[crop]
        all_years = range(min(years_obs), max(years_fut))  # extend shading to end
        #ax.axhline(y=upper, color='darkred', linestyle=':', linewidth=1.5, alpha=0.8, label='Threshold Upper')
        ax.fill_between(all_years, lower, upper, color='gray', alpha=0.15, label='Threshold Range')

    # Median line for the crop
    if crop in median_values:
        #ax.axhline(y=median_values[crop], color='darkred', linestyle=':', linewidth=1.5, alpha=0.8, label='Median')
        ax.axhline(y=median_values[crop], color='red', linestyle='--', linewidth=1.5, label='Median')
        
    ax.set_title(label)
    ax.set_xlabel('Year')
    ax.set_ylabel('Chill Portions')
    ax.grid(True)

    # Only legend in the first subplot
    if idx == 3:
        ax.legend(
            loc='lower left',
            bbox_to_anchor=(0.0, 0.0),
            fontsize=12,
            frameon=False
        )
plt.tight_layout()
save_dir = os.path.join(path, 'plots')
os.makedirs(save_dir, exist_ok=True)
plt.savefig(os.path.join(save_dir, 'Figure 2.png'), dpi=300)
plt.show()
#%%