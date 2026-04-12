import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import os
from scipy.stats import pearsonr
import matplotlib.colors as mcolors
import matplotlib as mpl

print("Starting script...", flush=True)

# --- Global font setup ---
plt.rcParams.update({
    'font.size': 18,
    'font.family': 'Arial'
})

# --- File paths (copy 'plot_data_published' directory inside path dir) ---
path = "path_to_project_root" 

obs = pd.read_csv(os.path.join(path, 'plot_data_published/GRIDMET_chill_monthly_sum_obs_all_years.csv'))
md  = pd.read_csv(os.path.join(path, 'plot_data_published/ECMWF_chill_daily_bc_daily_all_years.csv'))
mm  = pd.read_csv(os.path.join(path, 'plot_data_published/ECCMWF_chill_monthly_bc_daily_all_years.csv'))

# Load shapefile for CA counties
california = gpd.read_file(os.path.join(path, 'plot_data_published/SHP/CA_county.shp'))

# Create Feb_Total in each dataset
obs['Feb_Total'] = obs[['Feb_W1','Feb_W2','Feb_W3','Feb_W4']].sum(axis=1)
md['Feb_Total']  = md[['Feb_W1','Feb_W2','Feb_W3','Feb_W4']].sum(axis=1)
mm['Feb_Total']  = mm[['Feb_W1','Feb_W2','Feb_W3','Feb_W4']].sum(axis=1)

months = ['Nov_Total', 'Dec_Total', 'Jan_Total', 'Feb_Total']

# Round coordinates consistently
obs['Lon_r'] = obs['Longitude'].round(3)
obs['Lat_r'] = obs['Latitude'].round(3)
md['Lon_r']  = md['Longitude'].round(3)
md['Lat_r']  = md['Latitude'].round(3)
mm['Lon_r']  = mm['Longitude'].round(3)
mm['Lat_r']  = mm['Latitude'].round(3)
#%%
# --- Merge obs with MD and MM on rounded coords and Year ---
merged_md = obs.merge(md, on=['Lon_r','Lat_r','Year'], suffixes=('_obs','_md'))
merged_mm = obs.merge(mm, on=['Lon_r','Lat_r','Year'], suffixes=('_obs','_mm'))

acc_md = {}
acc_mm = {}

for month in months:
    acc_md_list = []
    acc_mm_list = []

    # --- Obs vs MD ---
    for (lon_r, lat_r), group in merged_md.groupby(['Lon_r', 'Lat_r']):

        ts_obs = group[f'{month}_obs'].values
        ts_md  = group[f'{month}_md'].values

        if len(ts_obs) > 1:

            # ---- ANOMALIES ----
            obs_anom = ts_obs - np.nanmean(ts_obs)
            md_anom  = ts_md  - np.nanmean(ts_md)

            # avoid constant series
            if np.nanstd(obs_anom) > 0 and np.nanstd(md_anom) > 0:
                r, p = pearsonr(obs_anom, md_anom)
                acc = r if p < 0.05 else np.nan
            else:
                acc = np.nan
        else:
            acc = np.nan

        acc_md_list.append([lon_r, lat_r, acc])

    acc_md[month] = pd.DataFrame(acc_md_list, columns=['Longitude','Latitude','ACC'])

    # --- Obs vs MM ---
    for (lon_r, lat_r), group in merged_mm.groupby(['Lon_r', 'Lat_r']):

        ts_obs = group[f'{month}_obs'].values
        ts_mm  = group[f'{month}_mm'].values

        if len(ts_obs) > 1:

            # ---- ANOMALIES ----
            obs_anom = ts_obs - np.nanmean(ts_obs)
            mm_anom  = ts_mm  - np.nanmean(ts_mm)

            if np.nanstd(obs_anom) > 0 and np.nanstd(mm_anom) > 0:
                r, p = pearsonr(obs_anom, mm_anom)
                acc = r if p < 0.05 else np.nan
            else:
                acc = np.nan
        else:
            acc = np.nan

        acc_mm_list.append([lon_r, lat_r, acc])

    acc_mm[month] = pd.DataFrame(acc_mm_list, columns=['Longitude','Latitude','ACC'])


# --- Prepare plotting ---
california = california.to_crs("EPSG:4326")
colors = ['#67001f','#b2182b','#d6604d','#f4a582','#fddbc7','#e0e0e0','#bababa','#878787','#4d4d4d','#1a1a1a'] 
colors_rev = colors[::-1]

# Create a ListedColormap from the reversed colors
cmap = mcolors.ListedColormap(colors_rev)
n_colors = len(colors_rev)
half = (n_colors - 1) // 2  # number of bins above and below 0
bin_width = 1 / (half + 1)

# negative bins
neg_bins = -np.arange(half, 0, -1) * bin_width
# positive bins
pos_bins = np.arange(1, half+1) * bin_width

# combine
bin_edges = np.concatenate([neg_bins, [0.0], pos_bins])
bin_edges = np.concatenate([[-1.0], bin_edges, [1.0]])  # optional include -1,1 edges

norm = mcolors.BoundaryNorm(bin_edges, cmap.N)

fig, axes = plt.subplots(2, 4, figsize=(20, 10))
plt.subplots_adjust(wspace=0.1, hspace=0.35)

for i, month in enumerate(months):
    # Clean month name for title
    month_title = month.replace('_', ' ')
    
    # --- MD row ---
    gdf_md = gpd.GeoDataFrame(acc_md[month],
                              geometry=gpd.points_from_xy(acc_md[month]['Longitude'],
                                                          acc_md[month]['Latitude']),
                              crs="EPSG:4326")
    
    california.boundary.plot(ax=axes[0,i], color='gray', linewidth=0.3)
    california.dissolve().boundary.plot(ax=axes[0,i], color='black', linewidth=0.5)
    
    gdf_md.plot(ax=axes[0,i], column='ACC', cmap=cmap, norm=norm, markersize=8)
    axes[0,i].set_title(f'{month_title} (MD)')
    
    if i == 0:
        axes[0,i].set_xlabel('Longitude')
        axes[0,i].set_ylabel('Latitude')
    else:
        axes[0,i].set_xlabel('')
        axes[0,i].set_ylabel('')
        axes[0,i].set_xticklabels([])
        axes[0,i].set_yticklabels([])
    
    # --- MM row ---
    gdf_mm = gpd.GeoDataFrame(acc_mm[month],
                              geometry=gpd.points_from_xy(acc_mm[month]['Longitude'],
                                                          acc_mm[month]['Latitude']),
                              crs="EPSG:4326")
    
    california.boundary.plot(ax=axes[1,i], color='gray', linewidth=0.3)
    california.dissolve().boundary.plot(ax=axes[1,i], color='black', linewidth=0.5)
    
    gdf_mm.plot(ax=axes[1,i], column='ACC', cmap=cmap, norm=norm, markersize=8)
    axes[1,i].set_title(f'{month_title} (MM)')
    
    if i == 0:
        axes[1,i].set_xlabel('Longitude')
        axes[1,i].set_ylabel('Latitude')
    else:
        axes[1,i].set_xlabel('')
        axes[1,i].set_ylabel('')
        axes[1,i].set_xticklabels([])
        axes[1,i].set_yticklabels([])

# Add a shared colorbar
sm = mpl.cm.ScalarMappable(cmap=cmap, norm=norm)
sm._A = []
cbar = fig.colorbar(sm, ax=axes.ravel().tolist(), orientation='vertical', fraction=0.02, pad=0.01)
cbar.set_label('Anomaly Correlation Coefficient (ACC)')
save_dir = os.path.join(path, 'plots')
os.makedirs(save_dir, exist_ok=True)
plt.savefig(os.path.join(save_dir, 'Figure 4.png'), dpi=300, bbox_inches='tight')
plt.suptitle("ACC: Obs vs ECMWF's direct daily (top) and Obs vs ECMWF's daily from monthly mean (bottom)", y=0.95)
plt.show()
#%%
