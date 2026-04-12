import os
import pandas as pd
import numpy as np
from scipy.spatial import cKDTree
import matplotlib.pyplot as plt

print("Starting script...", flush=True)

# --- File paths (copy 'plot_data_published' directory inside path dir) ---
path = "path_to_project_root" 

# --------------------
# Parameters
# --------------------
acc_thresholds = [10, 5]  # two thresholds

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
    #df['Feb_tot_mod'] = df[['Feb_W1','Feb_W2','Feb_W3','Feb_W4']].sum(axis=1)
    #df.drop(columns=['Feb_W1','Feb_W2','Feb_W3','Feb_W4'], inplace=True)
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
    # rename columns for MM if needed
    if lon_name != 'Longitude_md':
        final.rename(columns={'Longitude_md': lon_name, 'Latitude_md': lat_name}, inplace=True)
    return final

final_md = merge_model_obs(obs, md, coord_map)
final_mm = merge_model_obs(obs, mm, coord_map, lon_name='Longitude_mm', lat_name='Latitude_mm')

# --------------------
# Parameters
# --------------------
acc_thresholds = [10, 5]  # thresholds, optional for flagging

# --------------------
# Function to compute region-level obs vs predicted
# --------------------
def compute_region_mean(df, method=1, lat_col='Latitude_md', lat_max=37):
    df_sub = df[df[lat_col] < lat_max].copy()
    # Compute obs totals
    df_sub['obs_NDJ'] = df_sub['Nov_Total_obs'] + df_sub['Dec_Total_obs'] + df_sub['Jan_Total_obs']
    df_sub['obs_Feb'] = df_sub['Feb_Total_obs']
    df_sub['obs_NDJF'] = df_sub['obs_NDJ'] + df_sub['obs_Feb']
    
    # Compute model totals based on method
    if method == 1:
        df_sub['pred_NDJF'] = df_sub['obs_NDJ'] + df_sub['Feb_tot_mod']
    elif method == 2:
        df_sub['pred_NDJF'] = df_sub['Nov_Total_obs'] + df_sub['Dec_Total_obs'] + df_sub['Jan_Total_mod'] + df_sub['Feb_tot_mod']
    elif method == 3:
        df_sub['pred_NDJF'] = df_sub['Nov_Total_obs'] + df_sub['Dec_Total_mod'] + df_sub['Jan_Total_mod'] + df_sub['Feb_tot_mod']
    elif method == 4:
        df_sub['pred_NDJF'] = df_sub['Nov_Total_mod'] + df_sub['Dec_Total_mod'] + df_sub['Jan_Total_mod'] + df_sub['Feb_tot_mod']
    else:
        raise ValueError("method must be 1–4")

    # Aggregate by year (mean over all grid points)
    yearly_mean = df_sub.groupby('Year')[['obs_NDJF', 'pred_NDJF']].mean().reset_index()
    return yearly_mean


obs_df = (
    final_md
    .groupby('Year')[['Nov_Total_obs','Dec_Total_obs','Jan_Total_obs','Feb_Total_obs']]
    .mean()
    .reset_index()
)
obs_df['NDJF_obs'] = obs_df[['Nov_Total_obs','Dec_Total_obs',
                             'Jan_Total_obs','Feb_Total_obs']].sum(axis=1)

# --------------------
# Lead-time evaluation
# --------------------
thresholds = [10, 5]
lead_methods = {1:1, 2:2, 3:3, 4:4}  # mapping to your methods

def compute_pred(df, method):
    if method == 1:
        return df['Nov_Total_obs'] + df['Dec_Total_obs'] + df['Jan_Total_obs'] + df['Feb_tot_mod']
    elif method == 2:
        return df['Nov_Total_obs'] + df['Dec_Total_obs'] + df['Jan_Total_mod'] + df['Feb_tot_mod']
    elif method == 3:
        return df['Nov_Total_obs'] + df['Dec_Total_mod'] + df['Jan_Total_mod'] + df['Feb_tot_mod']
    elif method == 4:
        return df['Nov_Total_mod'] + df['Dec_Total_mod'] + df['Jan_Total_mod'] + df['Feb_tot_mod']

def compute_obs(df):
    return df['Nov_Total_obs'] + df['Dec_Total_obs'] + df['Jan_Total_obs'] + df['Feb_Total_obs']


def evaluate_model(df, lat_col):
    results = []

    df = df[df[lat_col] < 37].copy()
    df['obs_NDJF'] = compute_obs(df)

    for lead, method in lead_methods.items():
        df['pred_NDJF'] = compute_pred(df, method)

        # % error
        df['pct_error'] = 100 * (df['pred_NDJF'] - df['obs_NDJF']) / df['obs_NDJF']

        # ---- GRID LEVEL ----
        for th in thresholds:
            grid_total = len(df)
            grid_acc = np.sum(np.abs(df['pct_error']) <= th)

            # ---- REGION LEVEL (yearly mean) ----
            yearly = df.groupby('Year')[['obs_NDJF','pred_NDJF']].mean().reset_index()
            yearly['pct_error'] = 100 * (yearly['pred_NDJF'] - yearly['obs_NDJF']) / yearly['obs_NDJF']

            region_total = len(yearly)
            region_acc = np.sum(np.abs(yearly['pct_error']) <= th)

            results.append({
                'Lead time (month)': lead,
                'Threshold': th,
                'Accurate years': region_acc,
                'Total years': region_total,
                'Region (%)': round(100 * region_acc / region_total),
                'Grid (%)': round(100 * grid_acc / grid_total)
            })

    return pd.DataFrame(results)

md_results = evaluate_model(final_md, 'Latitude_md')
mm_results = evaluate_model(final_mm, 'Latitude_mm')

# Add model label
md_results['Model'] = 'MD'
mm_results['Model'] = 'MM'

final_table = pd.concat([md_results, mm_results], ignore_index=True)
save_dir = os.path.join(path, 'plots')
os.makedirs(save_dir, exist_ok=True)

# Save
out_csv = os.path.join(save_dir, "leadtime_accuracy_table.csv")
final_table.to_csv(out_csv, index=False)

print(final_table)