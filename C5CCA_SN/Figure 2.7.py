import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, BoundaryNorm
from matplotlib.ticker import FormatStrFormatter
import matplotlib as mpl
import os

data_path = 'path of the "metadata" dir'
#data_path = r'C:\Users\Prakash\Box\Sierra_Nevada_Regional_Report_Pre_Publication\chapter2_climate\metadata'
#outdir = data_path
outdir = 'where you want to save the Figure'

variable = "SWE"
ssps = ['ssp245', 'ssp370', 'ssp585']

# === Colormap ===
colors = ['#f1eef6', '#d0d1e6', '#a6bddb', '#74a9cf',
          '#3690c0', '#0570b0', '#034e7b']
cmap = LinearSegmentedColormap.from_list('custom_palette', colors)

mpl.rcParams['font.family'] = 'sans-serif'
mpl.rcParams['font.size'] = 12

# =========================
# A4 PORTRAIT WIDTH CONTROL
# =========================
A4_W_IN = 8.27  # inches (A4 width in portrait)

# margins and layout in inches (tweak if you want)
LEFT_IN   = 0.35
RIGHT_IN  = 0.15
TOP_IN    = 0.10
BOTTOM_IN = 0.70

# horizontal spacing between subplots (in inches)
GAP_IN = 0.15

usable_w = A4_W_IN - LEFT_IN - RIGHT_IN
panel_d = (usable_w - 2 * GAP_IN) / 3.0  # 3 panels, 2 gaps

# extra vertical space for titles + colorbar + padding (in inches)
EXTRA_H_IN = 0.55

fig_h = panel_d + TOP_IN + BOTTOM_IN + EXTRA_H_IN

fig, axs = plt.subplots(
    1, 3,
    subplot_kw={'projection': 'polar'},
    figsize=(A4_W_IN, fig_h),
    gridspec_kw={'wspace': GAP_IN / panel_d}  # convert inches gap to relative wspace
)

# ===== Verify figure size =====
fig_w, fig_h = fig.get_size_inches()
dpi = fig.dpi
axs = axs.flatten()

# Convert inch margins -> subplots_adjust fractions
fig.subplots_adjust(
    left=LEFT_IN / A4_W_IN,
    right=1 - RIGHT_IN / A4_W_IN,
    bottom=BOTTOM_IN / fig_h,
    top=1 - TOP_IN / fig_h
)

ssp_titles = {
    'ssp245': '(a) SSP 2-4.5',
    'ssp370': '(b) SSP 3-7.0',
    'ssp585': '(c) SSP 5-8.5'
}

pc = None  # so colorbar can use the last mappable
bounds = None

for ax, ssp in zip(axs, ssps):
    print(f"Loading saved data for {ssp}...")
    df = pd.read_csv(os.path.join(
        data_path, 'clock',
        f"data_for_plot_clock_entire_Sierra_{variable}_{ssp}_SierraNevada.csv"
    ))
    df['time'] = pd.to_datetime(df['time'])
    df['year'] = df['time'].dt.year
    df['doy'] = df['time'].dt.dayofyear

    pivot = df.pivot(index='year', columns='doy', values='SierraNevada')
    years = pivot.index.values
    n_years = len(years)

    # === Polar plotting geometry ===
    DOY_SHIFT = 273
    full_radius_data = 100
    blank_frac = 0.25
    extra_radius = 18
    inner_radius = full_radius_data * blank_frac
    outer_data_radius = full_radius_data
    outer_radius = outer_data_radius + extra_radius
    LABEL_OFFSET_FROM_DATA = 9.0 
    LABEL_CLEARANCE = 4.0   # data-radius units; try 2.0–3.0 if needed
    OUTER_CLEARANCE = 3.0  
    label_radius = min(outer_data_radius + LABEL_OFFSET_FROM_DATA,
                   outer_radius - OUTER_CLEARANCE)
    outer_label_radius = outer_radius + 3
    r_edges = np.linspace(inner_radius, outer_data_radius, n_years + 1)

    T_plot = np.roll(pivot.values.T, -DOY_SHIFT, axis=0)
    data_for_pcolor = T_plot.T
    theta_edges = np.linspace(0, 2 * np.pi, data_for_pcolor.shape[1] + 1)

    # Color normalization
    vmin, vmax = df['SierraNevada'].min(), df['SierraNevada'].max()
    bounds = np.linspace(vmin, vmax, len(colors) + 1)
    norm = BoundaryNorm(bounds, cmap.N)

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
        ax.text(angle, label_radius, m, fontsize=12,
                ha='center', va='center', rotation=rot, rotation_mode='anchor',
                bbox=dict(facecolor='white', edgecolor='none', pad=0.15))

    # Radial month lines
    month_edges_doy = np.linspace(0, 365, 13)[:-1]
    month_radials = 2 * np.pi * ((month_edges_doy - DOY_SHIFT) % 365) / 365
    for angle in month_radials:
        ax.plot([angle, angle], [inner_radius, outer_radius],
                color='black', lw=0.3, alpha=0.25)

    # Year rings and labels every 30 years
    start_year = years[0]
    end_year = years[-1]
    year_labels = np.arange(1981, end_year + 1, 30)

    def year_to_radius(y):
        return inner_radius + (full_radius_data - inner_radius) * (y - start_year) / (end_year - start_year)

    theta_full = np.linspace(0, 2 * np.pi, 360)
    for ylbl in year_labels:
        if ylbl < start_year or ylbl > end_year:
            continue
        r_pos = year_to_radius(ylbl)
        ax.plot(theta_full, np.full_like(theta_full, r_pos),
                color='black', lw=0.3, alpha=0.35, ls='--')
        ax.text(0, r_pos, str(ylbl), color='black', fontsize=12,
                ha='right', va='center')

    ax.set_title(ssp_titles.get(ssp.lower(), ssp.upper()), fontsize=12,pad=1)

# Shared colorbar (place using figure fractions; stable under A4 sizing)
# Put it just above the bottom margin
cbar_h_in = 0.22
cbar_y_in = 0.26
cbar_left_in = LEFT_IN + 0.10
cbar_right_in = RIGHT_IN + 0.10
cbar_w_in = A4_W_IN - cbar_left_in - cbar_right_in

cbar_ax = fig.add_axes([
    cbar_left_in / A4_W_IN,
    cbar_y_in / fig_h,
    cbar_w_in / A4_W_IN,
    cbar_h_in / fig_h
])

cbar = fig.colorbar(pc, cax=cbar_ax, orientation='horizontal', boundaries=bounds)
cbar.ax.xaxis.set_label_position('top')
cbar.ax.set_xlabel(f'Daily {variable} (inches)', fontsize=12, fontweight='normal')
cbar.ax.xaxis.set_major_formatter(FormatStrFormatter('%d'))
cbar.ax.tick_params(labelsize=12, labelcolor='black', pad=2)
plt.savefig(os.path.join(outdir, "daily_SWE_SierraNevada_allSSPs_A4.png"), dpi=300, pad_inches=0.02)  # keeps exact width
plt.show()
