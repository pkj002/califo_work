pacman::p_load(
  ncdf4, dplyr, lubridate, chillR, tidyr, readr, future, furrr, tidyverse 
)

# convert to chillR format
chillr_tbl <- function(df) {
  df |>
    mutate(Year = year(dt), Month = month(dt), Day = day(dt),
           Tmax = as.numeric(tmx), Tmin = as.numeric(tmin)) |>
    dplyr::select(DATE = dt, Year, Month, Day, Tmax, Tmin)
}

hourtemps_long_tbl <- function(df) {
  df |>
    pivot_longer(
      cols = starts_with("Hour_"),
      names_to = "Hour",
      names_prefix = "Hour_",
      names_transform = list(Hour = as.integer),
      values_to = "temp_c"
    ) |>
    mutate(date_hour = make_datetime(year = Year, month = Month, day = Day, hour = Hour,
                                     tz = "America/Los_Angeles")) |>
    dplyr::select(date_hour, temp_c)
}

crop = 'walnut'
process_gcm <- function(gcm) {
# File paths
# --------------------
  # File paths (dynamic)
  # --------------------
  tasmax_file <- paste0(
    "directory where CMIP6 Tmax files are present",
    "tasmax_", gcm, "_", scenario, "_", member, ".nc"
  )

  tasmin_file <- paste0(
    "directory where CMIP6 Tmin files are present",
    "tasmin_", gcm, "_", scenario, "_", member, ".nc"
  )

target_coords <- read.csv(paste0('path to plot_data_published dir', crop,"_lat_lon_in_Calif.csv"))

# Load lat/lon from NetCDF
nc_tmx <- nc_open(tasmax_file)
lat <- ncvar_get(nc_tmx, "lat")
lon <- ncvar_get(nc_tmx, "lon")
time <- ncvar_get(nc_tmx, "time")  # Days since some origin
nc_close(nc_tmx)

# Output directory
 # --------------------
  # Output dir per GCM
  # --------------------
  output_dir <- paste0(
    "directory where you want to save outputs",
    gcm, "/"
  )
  dir.create(output_dir, showWarnings = FALSE, recursive = TRUE)

# Helper function to extract time series at grid point
extract_time_series <- function(nc_path, varname, lon_idx, lat_idx) {
  nc <- nc_open(nc_path)
  vals <- ncvar_get(nc, varid = varname, start = c(lon_idx, lat_idx, 1, 1), count = c(1, 1, -1, 1))
  nc_close(nc)
  return(as.vector(vals))
}

process_grid_point <- function(lat_pt, lon_pt) {
  # Load necessary libraries INSIDE the function
  library(ncdf4)
  library(dplyr)
  library(lubridate)
  library(chillR)
  library(readr)

  tryCatch({
    # Find nearest grid indices
    lat_index <- which.min(abs(lat - lat_pt))
    lon_index <- which.min(abs(lon - lon_pt))

    # Extract temperature series and convert to °C
    tmin_series <- round(extract_time_series(tasmin_file, "tasmin", lon_index, lat_index) - 273.15, 4)
    tmax_series <- round(extract_time_series(tasmax_file, "tasmax", lon_index, lat_index) - 273.15, 4)

    # Build full date sequence (ensure 'time' is in global scope or passed in)
    date_seq <- seq.Date(as.Date("2040-01-01"), by = "day", length.out = length(tmin_series))

    temp_df_full <- data.frame(
      dt = date_seq,
      tmin = tmin_series,
      tmx = tmax_series
    )

    # Filter for target date range
    temp_df <- temp_df_full %>%
      filter(dt >= as.Date("2040-01-01") & dt <= as.Date("2100-12-31"))

    # Construct chillR-compatible table
    chillr_obs <- chillr_tbl(temp_df)
	
	# Generate hourly temperatures from daily data
		hourly_chill_obs <- tryCatch({
		  chillR::make_hourly_temps(latitude = lat_pt, year_file = chillr_obs)
		}, error = function(e) return(NULL))

		# Check if hourly generation failed
		if (is.null(hourly_chill_obs)) {
		  message(sprintf("Skipping lat = %.4f, lon = %.4f: hourly generation failed", lat_pt, lon_pt))
		  return(NULL)
		}

   # Step 1: Pivot from wide to long to create temp_c
	hourly_long <- hourly_chill_obs %>%
	  tidyr::pivot_longer(
		cols = starts_with("Hour_"),
		names_to = "hour",
		names_prefix = "Hour_",
		names_transform = list(hour = as.integer),
		values_to = "temp_c"
	  ) %>%
	  dplyr::mutate(
		date = as.Date(DATE),
		date_hour = lubridate::ymd_h(paste(date, hour))
	  ) %>%
	  dplyr::arrange(date_hour)

	if (is.null(hourly_long)) next
   
  	# Step 2: Run Dynamic_Model on temp_c
	if (crop == "grape") {
	  obs_chillport_tbl <- hourly_long %>%
		mutate(
		  cHour = chillR::Chilling_Hours(temp_c, summ = FALSE),
		  date = as_date(date_hour)
		) %>%
		select(date, cHour)
	} else {
	  obs_chillport_tbl <- hourly_long %>%
		dplyr::mutate(
		  CP = round(chillR::Dynamic_Model(temp_c, summ = FALSE), 4)
		) %>%
		dplyr::select(date = date_hour, CP)
	}

    # Save output
    out_path <- file.path(output_dir, paste0(crop, "_fut_chill_portion_lat_", round(lat_pt, 4), "_lon_", round(lon_pt, 4), ".csv"))
    write_csv(obs_chillport_tbl, out_path)

    return(out_path)

  }, error = function(e) {
    message(sprintf("Error at lat = %.4f, lon = %.4f: %s", lat_pt, lon_pt, e$message))
    return(NULL)
  })
}

# Prepare coordinate list
coord_list <- target_coords %>% select(lat, lon)

# Plan parallel session
future::plan(multisession, workers = parallel::detectCores() - 1)

# Run the parallel process
output_files <- furrr::future_pmap(
  list(coord_list$lat, coord_list$lon),
  process_grid_point
)
}

