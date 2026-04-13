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
# Parameters
# --------------------
acc_thresholds = [10, 5]  # two thresholds

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

#%%
def plot_methods_4panel(df, lat_col, name, obs_df, save_path=None):
    fig, axes = plt.subplots(
        2, 2,
        figsize=(14, 10),
        sharex=True,
        sharey=True,
        gridspec_kw={
            'hspace': 0.15,  # reduce space between rows
            'wspace': 0.03    # reduce space between columns
        }
    )

    # Custom subplot titles
    subplot_titles = [
        "(a) NDJ observations + February ECMWF",
        "(b) ND observations + JF ECMWF",
        "(c) N observations + DJF ECMWF",
        "(d) NDJF ECMWF"
    ]

    methods = [1, 2, 3, 4]

    for ax, method, sub_title in zip(axes.flat, methods, subplot_titles):
        yearly_mean = compute_region_mean(
            df, method=method, lat_col=lat_col
        )

        # Predicted
        ax.plot(
            yearly_mean['Year'],
            yearly_mean['pred_NDJF'],
            linewidth=2, color='blue',
            linestyle='--',
            label='Predicted'
        )

        # Observed
        ax.plot(
            obs_df['Year'],
            obs_df['NDJF_obs'],
            linewidth=2, color='black',
            label='Observed'
        )

        # Subplot title with padding
        ax.set_title(sub_title, fontsize=15, pad=13)

        # Increase font size of ticks
        ax.tick_params(axis='both', which='major', labelsize=12)

        # Grid
        ax.grid(True)

    # Axis labels with bigger font
    for ax in axes[-1, :]:
        ax.set_xlabel('Year', fontsize=14)
    for ax in axes[:, 0]:
        ax.set_ylabel('NDJF Chill Portions', fontsize=14)

    # Legend only in bottom-left of first subplot
    axes[0, 0].legend(
        loc='lower left',
        fontsize=12,
        frameon=False
    )
    # Save figure if save_path is provided
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
    # Adjust layout so titles & labels are not clipped
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.show()
#===================================
# MD figure
save_dir = os.path.join(path, "plots")
os.makedirs(save_dir, exist_ok=True)

plot_methods_4panel(
    df=final_md,
    lat_col='Latitude_md',
    name='MD (Daily)',
    obs_df=obs_df,
    save_path=os.path.join(save_dir,'Supplementary Figure 7tes.png')
)

# MM figure
plot_methods_4panel(
    df=final_mm,
    lat_col='Latitude_mm',
    name='MM (Monthly)',
    obs_df=obs_df,
    save_path=os.path.join(save_dir,'Supplementary Figure 8tes.png')
)
