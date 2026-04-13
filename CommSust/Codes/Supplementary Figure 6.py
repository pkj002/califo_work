import os
import pandas as pd
import numpy as np
from scipy.spatial import cKDTree
import matplotlib.pyplot as plt

print("Starting script...", flush=True)

# --- File paths (copy 'plot_data_published' directory inside path dir) ---
# Download "plot_data_published" directory (https://ucmerced.box.com/s/u9ntcj58lii519std4u1cfi8gkl07h5k)
path = "path_to_project_root" 

# --------------------
# Load data
# --------------------
obs = pd.read_csv(os.path.join(path, 'plot_data_published/GRIDMET_chill_monthly_sum_obs_all_years_Supp_Fig6.csv'))
md  = pd.read_csv(os.path.join(path, 'plot_data_published/ECMWF_chill_daily_bc_daily_Supp_Fig6.csv'))
mm  = pd.read_csv(os.path.join(path, 'plot_data_published/ECMWF_mod_chill_monthly_bc_daily_Supp_Fig6.csv'))
# --------------------
# Preprocess observed data
# --------------------
obs['Feb_Total_obs'] = obs[['Feb_W1','Feb_W2','Feb_W3','Feb_W4']].sum(axis=1)
obs['NDJF_obs'] = obs[['Nov_Total','Dec_Total','Jan_Total']].sum(axis=1) + obs['Feb_Total_obs']
obs.rename(columns={'Nov_Total':'Nov_Total_obs','Dec_Total':'Dec_Total_obs','Jan_Total':'Jan_Total_obs'}, inplace=True)
obs.drop(columns=['Feb_W1','Feb_W2','Feb_W3','Feb_W4'], inplace=True)

# --------------------
# Preprocess model data
# --------------------
for df in [md, mm]:
    df.rename(columns={'Nov_Total':'Nov_Total_mod','Dec_Total':'Dec_Total_mod','Jan_Total':'Jan_Total_mod',
                       'Feb_Total': 'Feb_tot_mod'}, inplace=True)

# --------------------
# KD-tree mapping obs -> model
# --------------------
def create_coord_map(model_df, obs_df):
    md_coords = model_df[['Longitude','Latitude']].drop_duplicates().to_numpy()
    obs_coords = obs_df[['Longitude','Latitude']].drop_duplicates().to_numpy()
    tree = cKDTree(md_coords)
    _, idx = tree.query(obs_coords, k=1)
    coord_map = pd.DataFrame({
        'Longitude_obs': obs_coords[:,0],
        'Latitude_obs': obs_coords[:,1],
        'Longitude_md': md_coords[idx,0],
        'Latitude_md': md_coords[idx,1]
    }).drop_duplicates(subset=['Longitude_md','Latitude_md'], keep='first')
    return coord_map

coord_map = create_coord_map(md, obs)

# --------------------
# Merge obs + model
# --------------------
def merge_model_obs(obs_df, model_df, coord_map, lon_name='Longitude_md', lat_name='Latitude_md'):
    obs_merged = obs_df.merge(coord_map, left_on=['Longitude','Latitude'],
                              right_on=['Longitude_obs','Latitude_obs'])
    mod_merged = model_df.merge(coord_map, left_on=['Longitude','Latitude'],
                                right_on=['Longitude_md','Latitude_md'])
    obs_cols = ['Longitude_md','Latitude_md','Year','Nov_Total_obs','Dec_Total_obs','Jan_Total_obs','Feb_Total_obs','NDJF_obs']
    mod_cols = ['Longitude_md','Latitude_md','Year','Nov_Total_mod','Dec_Total_mod','Jan_Total_mod','Feb_tot_mod']
    final = obs_merged[obs_cols].merge(mod_merged[mod_cols],
                                       on=['Longitude_md','Latitude_md','Year'])
    if lon_name != 'Longitude_md':
        final.rename(columns={'Longitude_md': lon_name, 'Latitude_md': lat_name}, inplace=True)
    return final

final_md = merge_model_obs(obs, md, coord_map)
final_mm = merge_model_obs(obs, mm, coord_map, lon_name='Longitude_mm', lat_name='Latitude_mm')

# --------------------
# Region-level computation
# --------------------
# --------------------
# Year-by-year observed vs predicted (Method 1 only)
# --------------------
def analyze_region_yearly(df, lat_col='Latitude_md', lat_max=37):
    df_sub = df[df[lat_col] < lat_max].copy()
    yearly = df_sub.groupby('Year').mean(numeric_only=True).reset_index()

    # Observed components
    yearly['obs_NDJ'] = yearly['Nov_Total_obs'] + yearly['Dec_Total_obs'] + yearly['Jan_Total_obs']
    yearly['obs_Feb'] = yearly['Feb_Total_obs']
    yearly['obs_NDJF'] = yearly['obs_NDJ'] + yearly['obs_Feb']

    # Predicted (Method 1)
    yearly['pred_NDJF'] = yearly['obs_NDJ'] + yearly['Feb_tot_mod']

    # Differences
    yearly['Diff'] = yearly['pred_NDJF'] - yearly['obs_NDJF']
    yearly['Pct_diff'] = 100 * yearly['Diff'] / yearly['obs_NDJF']

    return yearly[['Year', 'obs_NDJF', 'pred_NDJF', 'Diff', 'Pct_diff']]

# --------------------
# Run for both models (MD and MM)
# --------------------
results_list = []

for name, df in zip(['MD','MM'], [final_md, final_mm]):
    lat_col = 'Latitude_md' if name=='MD' else 'Latitude_mm'
    yearly_res = analyze_region_yearly(df, lat_col=lat_col)
    yearly_res['Model'] = name
    results_list.append(yearly_res)

# Combine and save
results_df = pd.concat(results_list, ignore_index=True)
out_file = os.path.join(path, "mod_obs/region_yearly_obs_pred_method1.csv")
#results_df.to_csv(out_file, index=False)

# print(f"Saved yearly observed vs predicted chill (Method 1 only) to {out_file}")
# pd.set_option('display.max_columns', None)
# print(results_df.head(10))
#%%

# Separate data for MD and MM
md = results_df[results_df['Model'] == 'MD']
mm = results_df[results_df['Model'] == 'MM']

# Set font globally
plt.rcParams['font.family'] = 'Arial'
plt.rcParams['font.size'] = 18

# Create figure
plt.figure(figsize=(12, 7))

# Plot observed
plt.plot(md['Year'], md['obs_NDJF'], color='black', linestyle='--', linewidth=3, label='Observed')

# Plot ECMWF predictions
plt.plot(md['Year'], md['pred_NDJF'], color='tab:blue', linewidth=3, label='(NDJ obs + Feb ECMWF (MD)')
plt.plot(mm['Year'], mm['pred_NDJF'], color='tab:orange', linewidth=3, label='NDJ obs + Feb ECMWF (MM)')

# Labels and style
plt.xlabel('Year')
plt.ylabel('Total CP during NDJF season')
#plt.legend(loc='lower left')  # bottom-left legend
plt.legend(loc='lower left', ncol=1, fontsize=15)
#plt.title('Observed vs ECMWF (MD & MM) Predictions')
plt.grid(True, linestyle='--', alpha=0.5)
plt.tight_layout()
save_dir = os.path.join(path, "plots")
os.makedirs(save_dir, exist_ok=True)
plt.savefig(os.path.join(save_dir, 'Supplementary Figure 6.png'), dpi=600)
plt.show()
#%%
