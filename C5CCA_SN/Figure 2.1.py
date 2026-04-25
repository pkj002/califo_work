import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from matplotlib.colors import BoundaryNorm, ListedColormap
from shapely.geometry import Point
import matplotlib.colors as mcolors
import matplotlib as mpl

# -----------------------------
# Global font settings
# -----------------------------
base_fontsize = 16
mpl.rcParams.update({'font.size': base_fontsize, 'font.family': 'Arial'})

# -----------------------------
# Define paths and load data
# -----------------------------
data_path = 'path of the "metadata" dir'
#data_path = r'C:\Users\Prakash\Box\Sierra_Nevada_Regional_Report_Pre_Publication\chapter2_climate\metadata'
outdir = 'where you want to save the Figure'
shapefile_path = data_path + '/CC5a_Regions/CC5a_RegionsSub.shp'

# Historical averages
p1 = np.load(data_path + '/arrays_hist_fut_pr.npz')['historical_avg'] 
tx1 = np.load(data_path + '/arrays_hist_fut_tasmax.npz')['historical_avg']
tn1 = np.load(data_path + '/arrays_hist_fut_tasmin.npz')['historical_avg']

# Coordinates
co = np.load(data_path + '/coordinates.npz')
longitudes = co['longitudes']
latitudes = co['latitudes']

# -----------------------------
# Load shapefile and filter regions
# -----------------------------
shapefile = gpd.read_file(shapefile_path).to_crs('EPSG:4326')

regions_to_mask = ["N Sierra", "NE Sierra", "S Sierra", "SE Sierra"]
subregion_df = shapefile.loc[shapefile['subregion'].isin(regions_to_mask)]

if subregion_df.empty:
    raise ValueError(f"Subregion geometries for {regions_to_mask} not found.")

combined_geom = subregion_df['geometry'].unary_union

# -----------------------------
# Mask function
# -----------------------------
def mask_data(data, lon, lat, geometry):
    mask = np.zeros_like(data, dtype=bool)
    lon_flat = lon.flatten()
    lat_flat = lat.flatten()
    for i, x in enumerate(lon_flat):
        for j, y in enumerate(lat_flat):
            if geometry.contains(Point(x, y)):
                mask[j, i] = True
    return np.where(mask, data, np.nan)

# Apply masking
masked_data_p = mask_data(p1, longitudes, latitudes, combined_geom)
masked_data_tx = mask_data(tx1, longitudes, latitudes, combined_geom)
masked_data_tn = mask_data(tn1, longitudes, latitudes, combined_geom)

# -----------------------------
# Plot settings
# -----------------------------
extent_buffered = [longitudes.min(), -117.8,
                   latitudes.min() - 0.1, latitudes.max() + 0.1]

# Color maps
cmap_tmx = ListedColormap(['#f7fcf5','#e5f5e0','#ffffcc','#ffeda0','#fed976',
                           '#feb24c','#fd8d3c','#fc4e2a','#e31a1c','#bd0026','#800026'])
bounds_tmx = np.arange(34, 94, 6)
norm_tmx = BoundaryNorm(boundaries=bounds_tmx, ncolors=len(bounds_tmx)-1, clip=True)

cmap_tmin = ListedColormap(['#f7fcf5','#e5f5e0','#ffffcc','#ffeda0','#fed976',
                            '#feb24c','#fd8d3c','#fc4e2a','#e31a1c','#bd0026','#800026'])
bounds_tmin = np.arange(12, 67, 6)
norm_tmin = BoundaryNorm(boundaries=bounds_tmin, ncolors=len(bounds_tmin)-1, clip=True)

cmap_pr = mcolors.ListedColormap(['#f7fbff','#deebf7','#c6dbef','#9ecae1',
                                  '#6baed6','#3182bd','#08519c'])
bounds_pr = np.array([0, 6, 12, 24, 36, 48, 84])
norm_pr = mcolors.BoundaryNorm(bounds_pr, cmap_pr.N, extend='max')

# -----------------------------
# Create plots
# -----------------------------
fig_width, fig_height = 11.69, 6  # width fits A4, height scaled for 3 panels
fig, axes = plt.subplots(nrows=1, ncols=3,
                         subplot_kw={'projection': ccrs.PlateCarree()},
                         figsize=(fig_width, fig_height),
                         gridspec_kw={'wspace': 0.1})

# (a) Tmax
ax1 = axes[0]
im1 = ax1.pcolormesh(longitudes, latitudes, masked_data_tx,
                     cmap=cmap_tmx, norm=norm_tmx, shading='auto',
                     transform=ccrs.PlateCarree())
ax1.set_extent(extent_buffered, crs=ccrs.PlateCarree())
ax1.coastlines()
ax1.add_feature(cfeature.BORDERS, linestyle=':')
gl1 = ax1.gridlines(draw_labels=True, linewidth=0.5, color='gray',
                    alpha=0.7, linestyle='--')
gl1.top_labels, gl1.right_labels = False, False
ax1.set_title('(a) Tmax')

# (b) Tmin
ax2 = axes[1]
im2 = ax2.pcolormesh(longitudes, latitudes, masked_data_tn,
                     cmap=cmap_tmin, norm=norm_tmin, shading='auto',
                     transform=ccrs.PlateCarree())
ax2.set_extent(extent_buffered, crs=ccrs.PlateCarree())
ax2.coastlines()
ax2.add_feature(cfeature.BORDERS, linestyle=':')
gl2 = ax2.gridlines(draw_labels=True, linewidth=0.5, color='gray',
                    alpha=0.7, linestyle='--')
gl2.top_labels, gl2.right_labels = False, False
ax2.set_title('(b) Tmin')

# (c) Precipitation
ax3 = axes[2]
im3 = ax3.pcolormesh(longitudes, latitudes, masked_data_p,
                     cmap=cmap_pr, norm=norm_pr, shading='auto',
                     transform=ccrs.PlateCarree())
ax3.set_extent(extent_buffered, crs=ccrs.PlateCarree())
ax3.coastlines()
ax3.add_feature(cfeature.BORDERS, linestyle=':')
gl3 = ax3.gridlines(draw_labels=True, linewidth=0.5, color='gray',
                    alpha=0.7, linestyle='--')
gl3.top_labels, gl3.right_labels = False, False
ax3.set_title('(c) Precipitation')

# -----------------------------
# Add region boundaries
# -----------------------------
for ax in axes:
    ax.add_geometries(subregion_df['geometry'], crs=ccrs.PlateCarree(),
                      edgecolor='black', facecolor='none', linewidth=0.75)

# -----------------------------
# Tmax
cbar_ax1 = fig.add_axes([0.08, 0.005, 0.22, 0.035])  # moved down from 0.02 → 0.005
cbar1 = plt.colorbar(im1, cax=cbar_ax1, orientation='horizontal')
cbar1.set_ticks(bounds_tmx)
cbar1.ax.set_xticklabels([f'{tick}' for tick in bounds_tmx])  # no °F
cbar1.ax.xaxis.set_label_position('top')
cbar1.ax.set_xlabel("°F")

# Tmin
cbar_ax2 = fig.add_axes([0.38, 0.005, 0.22, 0.035])
cbar2 = plt.colorbar(im2, cax=cbar_ax2, orientation='horizontal')
cbar2.set_ticks(bounds_tmin)
cbar2.ax.set_xticklabels([f'{tick}' for tick in bounds_tmin])  # no °F
cbar2.ax.xaxis.set_label_position('top')
cbar2.ax.set_xlabel("°F")

# Precipitation
cbar_ax3 = fig.add_axes([0.7, 0.005, 0.22, 0.035])
cbar3 = plt.colorbar(im3, cax=cbar_ax3, orientation='horizontal')
cbar3.set_ticks(bounds_pr)
cbar3.ax.set_xticklabels([f'{tick}' for tick in bounds_pr])  # no inch
cbar3.ax.xaxis.set_label_position('top')
cbar3.ax.set_xlabel("Inches")

# Adjust bottom spacing to prevent overlap
plt.subplots_adjust(top=0.9, bottom=0.17, left=0.05, right=0.95, wspace=0.1)

# -----------------------------
# Save figure
# -----------------------------
plt_path_png = data_path + '/normals_plot2.png'

plt.savefig(plt_path_png, bbox_inches='tight', dpi=300)  # raster
plt.show()
fig_width, fig_height = fig.get_size_inches()
print(f"Figure size: {fig_width:.2f} in × {fig_height:.2f} in")
