import os
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Point
import matplotlib.colors as mcolors
import numpy as np
from mpl_toolkits.axes_grid1.inset_locator import inset_axes

# --- File paths (copy 'plot_data_published' directory inside path) ---
path = "path_to_project_root" 

# --- Load shapefiles ---
california = gpd.read_file(os.path.join(path, 'plot_data_published', 'SHP', 'CA_county.shp'))

# WORLD shapefile (your downloaded one)
world = gpd.read_file(os.path.join(path, 'plot_data_published', 'world', 'ne_110m_admin_0_countries.shp'))

# Chill trend data
chill_df = pd.read_csv(os.path.join(path, 'plot_data_published', 'GRIDMET_chill_df_MK_yp.csv'))

# --- Convert chill_df to GeoDataFrame ---
geometry = [Point(lon, lat) for lon, lat in zip(chill_df["Longitude"], chill_df["Latitude"])]
chill_gdf = gpd.GeoDataFrame(chill_df, geometry=geometry, crs="EPSG:4326")

# Reproject all to same CRS
world = world.to_crs(chill_gdf.crs)
california = california.to_crs(chill_gdf.crs)

# --- Keep only significant chill points inside California ---
sig_gdf = chill_gdf[chill_gdf["Significant"] == True]
sig_gdf = sig_gdf[sig_gdf.within(california.geometry.union_all())]

# --- Custom diverging colormap ---
colr = ['#01665e', '#35978f', '#f7f7f7', '#e08214', '#993404']
div_cmap = mcolors.LinearSegmentedColormap.from_list("bright_div", colr[::-1])

# --- Color bins ---
vmax = np.ceil(sig_gdf["Trend"].abs().max() * 10) / 10
bins = np.arange(-vmax, vmax + 0.2, 0.2)
norm = mcolors.BoundaryNorm(bins, div_cmap.N, extend='both')

# --- Main plot (California) ---
fig, ax = plt.subplots(figsize=(8, 8))

# County boundaries
california.boundary.plot(ax=ax, color='lightgray', linewidth=0.3)

# State outline
california.dissolve().boundary.plot(ax=ax, color='black', linewidth=0.6)

# Chill trends (square, small markers)
sig_gdf.plot(
    ax=ax,
    column='Trend',
    cmap=div_cmap,
    marker='s',
    markersize=1,          # can stay small
    alpha=0.95,
    norm=norm,
    rasterized=True,       # 🔑 KEY FIX
    legend=True,
    legend_kwds={
        'label': r"Chill slope (chill portions yr$^{-1}$)",
        'shrink': 0.7,
        'ticks': bins
    }
)

# --- Fix legend (colorbar) fonts ---
cbar = ax.get_figure().axes[-1]   # GeoPandas colorbar axis
cbar.tick_params(labelsize=12)
cbar.set_ylabel(r"Chill slope (chill portions yr$^{-1}$)", fontsize=12, labelpad=8)

#ax.set_title("Slope of chill changes between 1980–2023", fontsize=14)
ax.set_xlabel("Longitude", fontsize=14)
ax.set_ylabel("Latitude", fontsize=14)
ax.tick_params(axis='both', labelsize=12)

# --- International inset (top-right) ---
axins = inset_axes(
    ax,
    width="45%",
    height="45%",
    loc="upper right",
    borderpad=0.8
)

# Plot world very lightly
world.plot(
    ax=axins,
    color='#eeeeee',
    edgecolor='gray',
    linewidth=0.3
)

# Highlight California
california.dissolve().plot(
    ax=axins,
    facecolor='red',
    edgecolor='black',
    linewidth=0.8
)

# Focus on North America (international context)
axins.set_xlim(-170, -50)
axins.set_ylim(15, 75)

# Remove inset clutter
axins.set_xticks([])
axins.set_yticks([])
axins.set_frame_on(False)

# --- Save figure ---
fig.subplots_adjust(top=0.95)
save_dir = os.path.join(path, 'plots')
os.makedirs(save_dir, exist_ok=True)
plt.savefig(os.path.join(save_dir, 'Figure 1.png'), dpi=300, bbox_inches='tight')
plt.show()
