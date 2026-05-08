# C5CCA_SN: Sierra Nevada Chapter 2 (Climate Science, Historical and Projectected Trends) Figure Scripts
This repository contains Python scripts used to generate figures for the Climate Science, Historical and Projected Trends chapter of the **California Fifth Climate Change Assessment (C5CCA)** regional report for the **Sierra Nevada region**.

The scripts reproduce climate projection analyses and visualizations presented in the report, including temperature, precipitation, snow water equivalent (SWE), runoff, snowmelt, and soil moisture changes under multiple CMIP6 Shared Socioeconomic Pathways (SSP).

Repository:  
https://github.com/pkj002/califo_work/tree/main/C5CCA_SN

---

## Overview
The scripts primarily use:
- Python
- xarray
- numpy
- pandas
- matplotlib
- cartopy

Climate projection datasets are mainly derived from:
- LOCA2 downscaled CMIP6 climate projections
- VIC (Variable Infiltration Capacity) hydrologic model outputs

The scripts were developed on a Windows operating system.

## Directory Contents

| Script | Figures Generated | Description |
|---|---|---|
| `Figure 2.1.py` | Figure 2.1 | Historical baseline maps of Tmax, Tmin, and precipitation |
| `Figures 2.2_2.3.py` | Figures 2.2–2.3 | Future projected changes in Tmax and Tmin |
| `Figure 2.4.py` | Figure 2.4 | Subregional temperature variability across SSP scenarios |
| `Figure 2.5.py` | Figure 2.5 | Future projected precipitation changes |
| `Figure 2.6.py` | Figure 2.6 | Subregional precipitation variability |
| `Figure 2.7.py` | Figure 2.7 | SWE visualization across water years |
| `Figures 2.8_2.9.py` | Figures 2.8–2.9 | Snowmelt and runoff projections |
| `Figure 2.10.py` | Figure 2.10 | Seasonal soil moisture changes |
| `Figure 3.5.py` | Figure 3.5 | April 1 SWE % change projections |
| `Appendix Figure A1-3.py` | Figures A1–A3 | SWE evolution under SSP scenarios |
| `Appendix Figure A4.py` | Figure A4 | April 1 SWE change projections |

---
## Data Sources
### Climate Projections
- LOCA2 downscaled CMIP6 projections:  
  https://loca.ucsd.edu/

### Hydrologic Variables
Hydrologic variables such as SWE, runoff, snowmelt, and soil moisture were obtained from VIC model simulations forced by CMIP6 climate projections available through the WRF-CMIP6 AWS Open Data repository (s3://wrf-cmip6/lusu/CEC/VIC_SIMULATIONS/GCMs/).

Processed metadata and supporting datasets are publicly available through Zenodo:
https://doi.org/10.5281/zenodo.20073440

---
## Study Region
The analyses focus on the Sierra Nevada region of California, including the following subregions:
- Northern Sierra Nevada
- Northeastern Sierra Nevada
- Southern Sierra Nevada
- Southeastern Sierra Nevada

---

## Example Dependencies

Install required packages using:

```bash
pip install xarray numpy pandas matplotlib cartopy netcdf4
