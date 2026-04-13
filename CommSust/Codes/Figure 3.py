import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os
import xarray as xr
import geopandas as gpd

# --- File paths (copy 'plot_data_published' directory inside path dir) ---
# Download "plot_data_published" directory (https://ucmerced.box.com/s/u9ntcj58lii519std4u1cfi8gkl07h5k)
path = "path_to_project_root" 

# GRIDMET
read_path = os.path.join(path, 'plot_data_published', 'GRIDMET_chill_df_Figure2.npz')
chill_data = np.load(read_path)
chill_df = pd.DataFrame({
    'Longitude': chill_data['Longitude'],
    'Latitude': chill_data['Latitude'],
    'Year': chill_data['Year'],
    'Chill': chill_data['Chill']
})

ds = xr.open_dataset(os.path.join(path, 'plot_data_published', 'tmmx_1981.nc'))
# Extract 'lon' and 'lat' coordinates
lon_all = ds['lon'].values
lat_all = ds['lat'].values
#%% make chill array from chill_df
# Path to the NetCDF file
ncf = xr.open_dataset(os.path.join(path, 'plot_data_published','tmmx_1982-2021_calif.nc'))

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
std_results = {}
window = 10
years = list(range(1981, 1981 + 45))  # Adjust if years change
crops = ['walnut', 'pista', 'cherry', 'plum']

for crop in crops:
    # Load lat/lon CSV for crop
    # File paths and crops
   
    crop_df = pd.read_csv(os.path.join(path, 'plot_data_published', f'{crop}_lat_lon_in_Calif.csv'))
    
    # Filter crop points to only those south of 37°N
    crop_df_south = crop_df[crop_df['lat'] < 37]

    if crop_df_south.empty:
        print(f"No crop points south of 37° for {crop}")
        continue

    # Create GeoDataFrame
    crop_gdf = gpd.GeoDataFrame(
        crop_df_south,
        geometry=gpd.points_from_xy(crop_df_south["lon"], crop_df_south["lat"]),
        crs="EPSG:4326"
    ).to_crs("EPSG:4326")  # same as GRIDMET CRS

    # Convert to index space of new_chill_array
    lat_inds = [np.argmin(np.abs(lat - pt.y)) for pt in crop_gdf.geometry]
    lon_inds = [np.argmin(np.abs(lon - pt.x)) for pt in crop_gdf.geometry]

    # Optional: remove duplicates to avoid double counting
    index_set = set(zip(lat_inds, lon_inds))
    
    # Extract chill time series for each (lat, lon) pair
    time_series = []
    for lat_i, lon_i in index_set:
        chill_values = new_chill_array[lat_i, lon_i, :]
        time_series.append(chill_values)

    # Stack and average across grid points
    chill_mean = np.nanmean(np.stack(time_series), axis=0)  # shape: (45,)
    # Convert to Pandas Series and compute rolling std
    chill_series = pd.Series(chill_mean, index=years)
    rolling_std = chill_series.rolling(window=window).std()

    std_results[crop] = rolling_std
    
    # Save or plot
    plt.plot(range(1980 + 1, 1980 + 1 + len(chill_mean)), chill_mean, label=crop.capitalize())

plt.figure(figsize=(10, 6))

for crop in crops:
    plt.plot(std_results[crop].index, std_results[crop].values, label=crop.capitalize(), linewidth=1)

plt.xlabel("Year")
plt.ylabel(f"{window}-Year Rolling Std Dev of Chill Portions")
plt.title(f"{window}-Year Rolling Variability of Chill Portions (< 37°N)")
plt.legend()
plt.grid(True)
plt.tight_layout()
save_dir = os.path.join(path, 'plots')
os.makedirs(save_dir, exist_ok=True)
plt.savefig(os.path.join(save_dir, 'Figure 3.png'), dpi=300, bbox_inches='tight')
plt.show()
#%%

