# -*- coding: utf-8 -*-
"""
Created on Sat Mar  8 19:20:01 2025

@author: Prakash
"""
import numpy as np
import matplotlib.pyplot as plt
import geopandas as gpd
import xarray as xr
import rioxarray
import os

# Configuration
models = ["CNRM-ESM2-1", "EC-Earth3-Veg", "GFDL-ESM4", "MPI-ESM1-2-HR"]
variable = 'RUNOFF'
#variable = 'SNOW_MELT'

path = 'path of the "metadata" dir'
#path = r'C:\Users\Prakash\Box\Sierra_Nevada_Regional_Report_Pre_Publication\chapter2_climate\metadata'
outdir = 'where you want to save the Figure'

shapefile_path = path + '/CC5a_Regions/CC5a_RegionsSub.shp'
regions = ["N Sierra", "NE Sierra", "S Sierra", "SE Sierra"]
month_labels = ['Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep']
scenarios = ["ssp245", "ssp370", "ssp585"]
periods = ["2041-2070", "2071-2100"]

# Load shapefile
shapefile = gpd.read_file(shapefile_path).to_crs("EPSG:4326")
shapefile['subregion_lower'] = shapefile['subregion'].str.lower()

# Load latitude and longitude data
latlon_data = np.load(path + '/VIC/soil_moisture/seasonal_means_CNRM-ESM2-1_historical.npz')
lon, lat = latlon_data['lon'], latlon_data['lat']

# Initialize storage dictionary
data_dict = {**{scenario: {period: [] for period in periods} for scenario in scenarios}, 'historical': []}

# Load the data for each model
for model in models:
    files = {scenario: np.load(path + f'/VIC/{variable}/{model}_{scenario}_{variable}_monthly_mean_results.npz') for scenario in scenarios}
    
    # Reorder data to start from October through September
    data_dict['historical'].append(np.roll(files['ssp245']['historical_monthly_mean'], -9, axis=0))
    
    for scenario in scenarios:
        for period in periods:
            data_dict[scenario][period].append(np.roll(files[scenario][f'{period}_monthly_mean'], -9, axis=0))

# Compute averages across models
def compute_avg(data, scenario, period):
    return np.mean(data_dict[scenario][period], axis=0)

# Clip dataset by region and return average monthly values
def clip_and_average(data, region_geometry):
    region_clipped = data.rio.clip([region_geometry], crs="EPSG:4326")
    return region_clipped.mean(dim=['x', 'y'])

# Initialize dictionary for monthly averages
monthly_averages = {region: {scenario: [] for scenario in ['historical', 'ssp245', 'ssp370', 'ssp585']} for region in regions}

# Create DataArrays
def create_dataarray(data_avg, coords, dims=['month', 'lat', 'lon']):
    da = xr.DataArray(data_avg, dims=dims, coords=coords)
    da = da.rename({'lat': 'y', 'lon': 'x'})
    da.rio.write_crs("EPSG:4326", inplace=True)
    da.rio.set_spatial_dims(x_dim='x', y_dim='y', inplace=True)
    return da

# Conversion factor mm -> inch
mm_to_inch = 0.0393701

if variable == 'RUNOFF':
    var_label = 'Runoff'
elif variable == 'SNOW_MELT':
    var_label = 'Snow Melt'
else:
    var_label = variable.title()  # fallback

# Loop through periods and regions to calculate monthly averages
for period in periods:
    historical_data_avg = np.mean(data_dict['historical'], axis=0)
    ssp245_data_avg = compute_avg(data_dict, 'ssp245', period)
    ssp37_data_avg = compute_avg(data_dict, 'ssp370', period)
    ssp585_data_avg = compute_avg(data_dict, 'ssp585', period)
    
    for region in regions:
        region_geometry = shapefile[shapefile['subregion_lower'] == region.lower()].geometry.iloc[0]
        coords = {'month': np.arange(1, 13), 'lat': lat, 'lon': lon}
        dataarrays = {
            'historical': create_dataarray(historical_data_avg, coords),
            'ssp245': create_dataarray(ssp245_data_avg, coords),
            'ssp370': create_dataarray(ssp37_data_avg, coords),
            'ssp585': create_dataarray(ssp585_data_avg, coords),
        }
        for scenario, da in dataarrays.items():
            monthly_averages[region][scenario] = clip_and_average(da, region_geometry).values

    # Convert all monthly averages to inch/day
    for region in regions:
        for scenario in ['historical', 'ssp245', 'ssp370', 'ssp585']:
            monthly_averages[region][scenario] = monthly_averages[region][scenario] * mm_to_inch

    # Determine global y-axis limits across all regions and scenarios
    all_values = []
    for region in regions:
        for scenario in ['historical', 'ssp245', 'ssp370', 'ssp585']:
            all_values.extend(monthly_averages[region][scenario])
    ymin, ymax = 0, max(all_values) * 1.1  # Add 10% padding at top
  
    # Set figure size for A4 landscape
    fig, axes = plt.subplots(2, 2, figsize=(11.69, 8.27))  # A4 landscape
    axes = axes.flatten()
    
    x_indices = np.arange(len(month_labels))
    
    # Base font size
    base_fontsize = 16
    plt.rcParams.update({'font.size': base_fontsize, 'font.family': 'Arial'})
    
    # Colorblind-friendly palette & markers
    cb_colors = {
        'Historical': '#000000',   
        'SSP 2-4.5': '#0072B2',    
        'SSP 3-7.0': '#E69F00',    
        'SSP 5-8.5': '#D55E00'    
    }
    
    cb_markers = {
        'Historical': 'o',
        'SSP 2-4.5': 's',
        'SSP 3-7.0': 'x',
        'SSP 5-8.5': '*'
    }
    
    regions_labels = ["(a) Northern Sierra Nevada", "(b) Northeastern Sierra Nevada",
                      "(c) Southern Sierra Nevada", "(d) Southeastern Sierra Nevada"]
    
    # Plot for each region
    for i, region in enumerate(regions):
        axes[i].plot(x_indices, monthly_averages[region]['historical'],
                     label='Historical', marker=cb_markers['Historical'], color=cb_colors['Historical'])
        axes[i].plot(x_indices, monthly_averages[region]['ssp245'],
                     label='SSP 2-4.5', marker=cb_markers['SSP 2-4.5'], color=cb_colors['SSP 2-4.5'])
        axes[i].plot(x_indices, monthly_averages[region]['ssp370'],
                     label='SSP 3-7.0', marker=cb_markers['SSP 3-7.0'], color=cb_colors['SSP 3-7.0'])
        axes[i].plot(x_indices, monthly_averages[region]['ssp585'],
                     label='SSP 5-8.5', marker=cb_markers['SSP 5-8.5'], color=cb_colors['SSP 5-8.5'])
    
        # Titles & labels with scaled fonts
        axes[i].set_title(regions_labels[i], fontsize=base_fontsize + 6, fontname='Arial')
        axes[i].set_ylabel(f'{var_label} (inch day$^{{-1}}$)', fontsize=base_fontsize + 4, fontname='Arial')
        axes[i].tick_params(axis='x', labelsize=base_fontsize)  # x-axis ticks
        axes[i].tick_params(axis='y', labelsize=base_fontsize + 2)  # y-axis ticks
    
        axes[i].set_ylim(ymin, ymax)
        axes[i].set_xticks(x_indices)
    
        # Grid
        axes[i].grid(axis='x', linestyle='-', linewidth=0.8, color='lightgray')
        axes[i].grid(axis='y', linestyle='--', linewidth=0.6, alpha=0.6)
        axes[i].tick_params(axis='x', which='major', length=8, width=1.5, direction='out')
    
        # Only show month labels for bottom row
        if i < 2:
            axes[i].set_xticklabels([])
        else:
            axes[i].set_xticklabels(month_labels, rotation=45, ha='right')
    
    # Common legend below all subplots
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower center', ncol=4, bbox_to_anchor=(0.5, 0.05),
               prop={'size': base_fontsize, 'weight': 'bold'})
    
    # Adjust layout
    fig.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.18, hspace=0.15, wspace=0.22)
    
    # Output paths
    output_path = os.path.join(outdir, f'monthly_mean_actual_values1_{variable}_{period}_Dec2025.png')
      
    # Save PNG (raster) and PDF (vector)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')  # PNG
       
    # Show figure
    plt.show()
