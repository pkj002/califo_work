import os
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, BoundaryNorm
from matplotlib.ticker import FormatStrFormatter

print("Starting script...", flush=True)

# === Paths and SSPs ===
#inp_path = 'path of the "metadata" dir'
inp_path = r'C:\Users\Prakash\Box\Sierra_Nevada_Regional_Report_Pre_Publication\chapter2_climate\metadata'
outdir = 'where you want to save the Figure'
outdir = inp_path

# === Set variable to process ===
variable = 'SWE'

ssps = ['ssp245', 'ssp370', 'ssp585']

# === Shapefile ===
shapefile = inp_path + r'\CC5a_Regions\CC5a_RegionsSub.shp'
gdf = gpd.read_file(shapefile).to_crs("EPSG:4326")

region_id_to_label = {
    "Region_0": "(a) Northern Sierra Nevada",
    "Region_1": "(b) Northeastern Sierra Nevada",
    "Region_2": "(c) Southern Sierra Nevada",
    "Region_3": "(d) Southeastern Sierra Nevada"
}

# =========================
# A4 PORTRAIT PAGE SETTINGS
# =========================
A4_W_IN = 8.27   # 210 mm
A4_H_IN = 11.69  # 297 mm

LEFT_IN, RIGHT_IN = 0.45, 0.25
TOP_IN, BOTTOM_IN = 0.35, 0.55

WSPACE_IN = 0.10
HSPACE_IN = 0.02

BASE_FS = 12
TITLE_FS = 12
LABEL_FS = 12
CBAR_FS = 12

# Polar geometry
DOY_SHIFT = 273
full_radius_data = 100
blank_frac = 0.25
extra_radius = 18
inner_radius = full_radius_data * blank_frac
outer_data_radius = full_radius_data
outer_radius = outer_data_radius + extra_radius

LABEL_OFFSET_FROM_DATA = 9.0
OUTER_CLEARANCE = 3.0
label_radius = min(outer_data_radius + LABEL_OFFSET_FROM_DATA,
                   outer_radius - OUTER_CLEARANCE)
outer_label_radius = outer_radius + 3

# Colormap
colors = ['#f1eef6', '#d0d1e6', '#a6bddb', '#74a9cf', '#3690c0', '#0570b0', '#034e7b']
cmap = LinearSegmentedColormap.from_list('custom_palette', colors)

# === Loop through SSPs ===
for ssp in ssps:
    print(f"\n=== Processing {ssp} ===")

    csv_file = os.path.join(inp_path,'clock', f"data_for_plot_clock_4regions_{variable}_{ssp}_SierraNevada.csv")
    if not os.path.exists(csv_file):
        print(f"WARNING: CSV not found for {ssp}, skipping.")
        continue

    df = pd.read_csv(csv_file)
    df['time'] = pd.to_datetime(df['time'])
    df['year'] = df['time'].dt.year
    df['doy'] = df['time'].dt.dayofyear

    regions = [col for col in df.columns if col.startswith('Region_')]

    vmin, vmax = df[regions].min().min(), df[regions].max().max()
    bounds = np.linspace(vmin, vmax, len(colors) + 1)
    norm = BoundaryNorm(bounds, cmap.N)

    # =========================
    # Create A4 portrait figure
    # =========================
    fig = plt.figure(figsize=(A4_W_IN, A4_H_IN))
    fig.subplots_adjust(
        left=LEFT_IN / A4_W_IN,
        right=1 - RIGHT_IN / A4_W_IN,
        bottom=BOTTOM_IN / A4_H_IN,
        top=1 - TOP_IN / A4_H_IN,
        wspace=WSPACE_IN / ((A4_W_IN - LEFT_IN - RIGHT_IN) / 2.0),
        hspace=HSPACE_IN / ((A4_H_IN - TOP_IN - BOTTOM_IN) / 2.0)
    )

    axs = fig.subplots(2, 2, subplot_kw={'projection': 'polar'}).flatten()

    # ---- Verify A4 ----
    fig_w, fig_h = fig.get_size_inches()
    pc = None

    # =========================
    # Plot 4 regions
    # =========================
    for i, region in enumerate(regions[:4]):
        ax = axs[i]

        pivot = df.pivot(index='year', columns='doy', values=region)
        years = pivot.index.values
        n_years = len(years)

        r_edges = np.linspace(inner_radius, outer_data_radius, n_years + 1)

        T_plot = np.roll(pivot.values.T, -DOY_SHIFT, axis=0)
        data_for_pcolor = T_plot.T
        theta_edges = np.linspace(0, 2 * np.pi, data_for_pcolor.shape[1] + 1)

        pc = ax.pcolormesh(theta_edges, r_edges, data_for_pcolor,
                           cmap=cmap, shading='auto', norm=norm)

        ax.set_theta_zero_location("N")
        ax.set_theta_direction(-1)
        ax.set_ylim(0, outer_label_radius + 2)
        ax.grid(False)
        ax.set_xticks([])
        ax.set_yticklabels([])
        ax.set_aspect('equal', adjustable='box')

        # Month labels
        months = ['O', 'N', 'D', 'J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S']
        month_centers_doy = np.array([289, 320, 350, 16, 46, 75, 105, 135, 166, 196, 227, 258])
        month_angles = 2 * np.pi * ((month_centers_doy - DOY_SHIFT) % 365) / 365

        for m, angle in zip(months, month_angles):
            rot = np.degrees(angle)
            if 90 < rot < 270:
                rot = (rot + 180) % 360
            ax.text(angle, label_radius, m,
                    fontsize=LABEL_FS, fontname='Arial',
                    ha='center', va='center',
                    rotation=rot, rotation_mode='anchor',
                    bbox=dict(facecolor='white', edgecolor='none', pad=0.15))

        # Year rings/labels
        start_year, end_year = years[0], years[-1]
        year_labels = np.arange(start_year, end_year + 1, 30)

        def year_to_radius(y):
            return inner_radius + (full_radius_data - inner_radius) * (y - start_year) / (end_year - start_year)

        theta_full = np.linspace(0, 2 * np.pi, 360)
        for ylbl in year_labels:
            if ylbl < start_year or ylbl > end_year:
                continue
            r_pos = year_to_radius(ylbl)
            ax.plot(theta_full, np.full_like(theta_full, r_pos),
                    color='black', lw=0.3, alpha=0.25, ls='--')
            ax.text(0, r_pos, str(ylbl),
                    color='black', fontsize=BASE_FS, fontname='Arial',
                    ha='right', va='center')

        ax.set_title(region_id_to_label.get(region, region),
                     fontsize=TITLE_FS, fontname='Arial', pad=6)

    # =========================
    # Shared colorbar (fixed initial position)
    # =========================
    cbar_left_in = LEFT_IN + 0.40
    cbar_right_in = RIGHT_IN + 0.40
    cbar_w_in = A4_W_IN - cbar_left_in - cbar_right_in
    cbar_h_in = 0.25
    cbar_y_in = 0.75

    cbar_ax = fig.add_axes([
        cbar_left_in / A4_W_IN,
        cbar_y_in / A4_H_IN,
        cbar_w_in / A4_W_IN,
        cbar_h_in / A4_H_IN
    ])

    cbar = fig.colorbar(pc, cax=cbar_ax, orientation='horizontal',
                        boundaries=bounds, ticks=bounds)
    cbar.ax.xaxis.set_label_position('top')
    cbar.ax.set_xlabel(f'Daily {variable} (inches)', fontsize=CBAR_FS, fontname='Arial')
    cbar.ax.xaxis.set_major_formatter(FormatStrFormatter('%d'))
    cbar.ax.tick_params(labelsize=CBAR_FS, pad=2)
    for lab in cbar.ax.get_xticklabels():
        lab.set_fontname('Arial')

    # =========================
    # Layout tightening 
    # =========================
    TARGET_GAP = 0.05  # increase if bottom titles touch top row (try 0.04–0.07)

    top_axes = [axs[0], axs[1]]
    bot_axes = [axs[2], axs[3]]

    top_y0 = min(a.get_position().y0 for a in top_axes)
    bot_y1 = max(a.get_position().y1 for a in bot_axes)
    current_gap = top_y0 - bot_y1

    delta = current_gap - TARGET_GAP
    if delta > 0:
        # move TOP row down to enforce gap
        for a in top_axes:
            p = a.get_position()
            a.set_position([p.x0, p.y0 - delta, p.width, p.height])

    # Now shift EVERYTHING up to remove top whitespace (includes colorbar)
    DESIRED_TOP = 0.935
    current_top = max(a.get_position().y1 for a in top_axes)
    shift_up = DESIRED_TOP - current_top

    if shift_up > 0:
        for a in axs[:4]:
            p = a.get_position()
            a.set_position([p.x0, p.y0 + shift_up, p.width, p.height])

        p = cbar_ax.get_position()
        cbar_ax.set_position([p.x0, p.y0 + shift_up, p.width, p.height])

        print(f"Shifted polar block + colorbar up by {shift_up:.3f}")
    else:
        print("Top whitespace already minimal; no upward shift applied.")

    # Save per SSP (avoid bbox_inches='tight' to preserve exact A4 canvas)
    outfile = os.path.join(outdir, f'daily_{variable}_{ssp}_sierra_regions_A4.png')
    fig.savefig(outfile, dpi=300, pad_inches=0.0)
    plt.show()
    plt.close(fig)
    print(f"Saved {outfile}")