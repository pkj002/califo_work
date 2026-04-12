import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.cm as cm
import os
import pandas as pd
from matplotlib.colors import ListedColormap, BoundaryNorm
import matplotlib.cm as cm

# --- File paths (copy 'plot_data_published' directory inside path dir) ---
path = "path_to_project_root" 

# Parameters
metrics = ['Avg', 'Diff', 'Trend', 'CV_Diff']
titles = [
    'Average Chill Portions (1980–2023)',
    'Chill Difference (2015–24 minus 1981–90)',
    'Mann-Kendall Slope (1980–2023)',
    'CV Difference (2015–24 minus 1981–90)'
]
cmaps = ['viridis', 'coolwarm', 'coolwarm', 'coolwarm']
metric_file_labels = ['avg', 'diff', 'trend', 'cv_diff']
crops = ['walnut', 'pista', 'cherry', 'plum']

# Load boundary
california = gpd.read_file(os.path.join(path, 'plot_data_published', 'SHP', 'CA_county.shp'))
#california = california.to_crs("EPSG:3310")

# Shared axis limits
xlim = california.total_bounds[[0, 2]]
ylim = california.total_bounds[[1, 3]]

# Load all crop GeoDataFrames
crop_stat_gdfs = {
    crop: gpd.read_file(os.path.join(path, 'plot_data_published', 'av_diff_cv_trend', f"{crop}_chill_stats.geojson"))
    for crop in crops
}


# Define colormaps
custom_cmaps = {
    'diff': ListedColormap(['#ffffb2','#fecc5c','#fd8d3c','#f03b20','#bd0026']),
    'trend': ListedColormap(['#ffffb2','#fecc5c','#fd8d3c','#f03b20','#bd0026']),
    'avg': ListedColormap(['#edf8e9','#bae4b3','#74c476','#31a354','#006d2c']),
    'cv_diff': ListedColormap(['#ffffb2','#fecc5c','#fd8d3c','#f03b20','#bd0026']),
}

boundaries_dict = {
    'diff': [-10, -8, -6, -4, -2, 0],       # Still increasing numerically
    'trend': [-0.2, -0.15, -0.1, -0.05, 0],
    'avg': [ 40, 50, 60, 70, 80 ],  # Adjust based on actual range
    'cv_diff': [0, 0.02, 0.04, 0.08, 0.1]
 
}

#%%
# Loop through metrics and create panel plots
for m_idx, (metric, title, cmap_name, mfile) in enumerate(zip(metrics, titles, cmaps, metric_file_labels)):
    
    base_cmap = custom_cmaps[mfile]

    if mfile in ['diff', 'trend']:
        cmap = base_cmap.reversed()
    else:
        cmap = base_cmap

    boundaries = boundaries_dict[mfile]
    norm = BoundaryNorm(boundaries, ncolors=cmap.N)

    fig = plt.figure(figsize=(20, 15))
    axes = []

    for j in range(4):
        left = 0.01 + j * 0.245
        ax = fig.add_axes([left, 0.04, 0.24, 0.9])
        axes.append(ax)

    for j, crop in enumerate(crops):
        ax = axes[j]
        gdf = crop_stat_gdfs[crop].to_crs(california.crs)

        gdf.plot(
            ax=ax,
            column=metric,
            cmap=cmap,
            norm=norm,
            markersize=6,
            alpha=0.8,
            legend=False
        )

        california.boundary.plot(ax=ax, color='black', linewidth=0.5)

        ax.set_xlim(xlim)
        ax.set_ylim(ylim)
        ax.set_title(crop.capitalize(), fontsize=13)
        ax.set_aspect('equal', adjustable='box')

        if j == 0:
            ax.set_ylabel('Latitude', fontsize=12)
        else:
            ax.set_yticklabels([])
            ax.set_ylabel("")
            ax.tick_params(left=False)

        ax.set_xlabel('Longitude', fontsize=12)

    sm = cm.ScalarMappable(cmap=cmap, norm=norm)
    sm._A = []

    cbar = fig.colorbar(sm, ax=axes, location='bottom', fraction=0.025, pad=0.05)
    cbar.set_label(title, fontsize=12)

    # FIXED FILENAME INDEX
    save_dir = os.path.join(path, "plots")
    os.makedirs(save_dir, exist_ok=True)
    output_path = os.path.join(
        save_dir,
        f"Supplementary_Figure_{m_idx + 1}.png"
    )

    fig.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close(fig)
#%%
