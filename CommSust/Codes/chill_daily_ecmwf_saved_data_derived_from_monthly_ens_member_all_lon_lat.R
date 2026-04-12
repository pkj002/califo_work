rm(list = ls())
gc()

pacman::p_load(
  ncdf4, dplyr, future, future.apply, lubridate, abind, purrr, chillR,
  tidyr, gridExtra, zoo, parallel, furrr, readr
)

# ChillR-compatible table
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

years <- 1981:2024
cld <- data.frame(
  dt = seq(
    as.Date(paste0(years[1], "-11-01")),
    as.Date(paste0(years[length(years)], "-12-31")),
    by = "days"
  )
) %>% 
  filter(
    (year(dt) == years[1] & month(dt) %in% c(11, 12)) | 
      (year(dt) != years[length(years)] & month(dt) %in% c(11, 12, 1, 2)) | 
      (year(dt) == years[length(years)] & month(dt) %in% c(1, 2))
  )

obs_base_path <- "path_to_project_root" 
# --- File paths (copy 'plot_data_published' directory inside path) ---
tmax_path <- file.path(obs_base_path, "tmx")
tmax_file <- nc_open(file.path(tmax_path, paste0("tmmx_", years[1], ".nc")))
tmin_path <- file.path(obs_base_path, "tmin")

lats <- ncvar_get(tmax_file, "lat")
lons <- ncvar_get(tmax_file, "lon")
nc_close(tmax_file)

# Define dimensions
lon_cal <- lons[8:256]
lat_cal <- lats[178:407]

data_path <- 'path where bias corrected ECMWF data are present'
bias_cor_tmx <- readRDS(file.path(data_path, 'ECMWF_tmx_monthly_to_daily_bias_corrected_using_methods_mentioned_in_the_article.RDS'))
bias_cor_tmx <- readRDS(file.path(data_path, 'ECMWF_tmin_monthly_to_daily_bias_corrected_using_methods_mentioned_in_the_article.RDS'))

#  Check index mapping
valid_indices <- read.csv('/glade/work/prajha/data/pts_where_crops.csv')
# Fix: get actual lat/lon from full grid
valid_lons <- lons[valid_indices[, "i"]]
valid_lats <- lats[valid_indices[, "j"]]
mask <- valid_lons >= -120.5 & valid_lons <= -120 & valid_lats >= 36 & valid_lats <= 37
valid_lons <- valid_lons[mask]
valid_lats <- valid_lats[mask]

range(valid_lats)
range(valid_lons)

# NEW: Find corresponding index in subsetted lon_cal / lat_cal
# Use which() for exact match
matched_i <- match(round(valid_lons, 6), round(lon_cal, 6))  # i: longitude index
matched_j <- match(round(valid_lats, 6), round(lat_cal, 6))  # j: latitude index

# Filter out unmatched
valid_mask <- !is.na(matched_i) & !is.na(matched_j)

final_indices <- data.frame(
  i = matched_i[valid_mask],
  j = matched_j[valid_mask],
  lon = valid_lons[valid_mask],
  lat = valid_lats[valid_mask]
)

mod_outpath <- '/glade/work/prajha/data/mod_monthly_bc_daily1'
dir.create(mod_outpath, showWarnings = FALSE, recursive = TRUE)

# Function to process a single grid cell
process_grid_cell_safe <- function(i, j, lat, tmx, tmin, lat_cal, lon_cal) {
  cell_id <- sprintf("lon=%.4f, lat=%.5f", lon_cal[i], lat_cal[j])
  cat(sprintf("[%s] Processing %s\n", Sys.time(), cell_id))
  
  n_members <- dim(tmx)[2]
  mon_chill_list <- list()
  
  for (mem in 1:n_members) {
    temp_direct_df <- data.frame(
      dt = cld$dt,
      tmin = tmin[, mem],
      tmx = tmx[, mem]
    )
    
    chillr_obs <- chillr_tbl(temp_direct_df)
    
    hourly_chill_obs <- tryCatch({
      chillR::make_hourly_temps(latitude = lat, year_file = chillr_obs)
    }, error = function(e) {
      cat(sprintf("[%s]   Failed hourly temp for member %d (%s): %s\n",
                  Sys.time(), mem, cell_id, e$message))
      return(NULL)
    })
    
    if (is.null(hourly_chill_obs)) next
    
    obs_vt_tbl <- hourtemps_long_tbl(hourly_chill_obs)
    
    # Compute chill portions as cumulative value
    obs_chillport_tbl <- obs_vt_tbl %>%
      dplyr::mutate(
        date = as.Date(date_hour),
        chillport = chillR::Dynamic_Model(temp_c)
      ) %>%
      dplyr::group_by(date) %>%
      dplyr::summarise(
        daily_chill = max(chillport) - min(chillport),
        .groups = "drop"
      ) %>%
      rename(!!paste0("daily_chill_", mem) := daily_chill)
    
    mon_chill_list[[mem]] <- obs_chillport_tbl
  }
  
  # Join all on date
  combined_chill <- purrr::reduce(mon_chill_list, full_join, by = "date")
  
  # Compute ensemble mean (row-wise mean across daily_chill columns)
  ensemble_daily_chill <- combined_chill %>%
    dplyr::mutate(
      mean_daily_chill = round(rowMeans(across(starts_with("daily_chill")), na.rm = TRUE), 3)
    ) %>%
    dplyr::select(date, mean_daily_chill)
  
  filename <- sprintf("mod_monthly_bc_lon%.4f_lat%.5f.csv", lon_cal[i], lat_cal[j])
  filename_safe <- gsub("-", "m", filename)
  out_file <- file.path(mod_outpath, filename_safe)
  readr::write_csv(ensemble_daily_chill, out_file)
  cat(sprintf("[%s] Finished cell %s, saved to %s\n", Sys.time(), cell_id, out_file))
  
  gc()
  return(NULL)
}

# ---- Setup Parallel Environment ----
Sys.setenv(R_FUTURE_AVAILABLECORES_FALLBACK = 16)

available_cores <- future::availableCores()
n_cores <- min(16, available_cores)

options(future.globals.maxSize = 20 * 1024^3)  # Increase if needed
future::plan(future::multisession, workers = n_cores)

cat(sprintf("[%s] Using %d cores for parallel execution\n", Sys.time(), n_cores))

# ---- Set Chunk Size ----
chunk_size <- 10

# ---- Split Grid into Chunks ----
chunks <- split(final_indices, ceiling(seq_len(nrow(final_indices)) / chunk_size))

# ---- Process Each Chunk in Parallel ----
for (chunk in chunks) {
  chunk_data <- list(
    i = chunk$i,
    j = chunk$j,
    # bias_cor arrays are [lon, lat, time], so swap i/j when slicing:
    tmx = purrr::map2(chunk$i, chunk$j, ~ bias_cor_tmx[.x, .y, , ]),
    tmin = purrr::map2(chunk$i, chunk$j, ~ bias_cor_tmin[.x, .y, , ]),
    lat = lat_cal[chunk$j]
  )
  
  tryCatch({
    furrr::future_pmap(
      list(
        i = chunk_data$i,
        j = chunk_data$j,
        tmx = chunk_data$tmx,
        tmin = chunk_data$tmin,
        lat = chunk_data$lat
      ),
      function(i, j, tmx, tmin, lat) {
        process_grid_cell_safe(
          i = i,
          j = j,
          lat = lat,
          tmx = tmx,
          tmin = tmin,
          lat_cal = lat_cal,
          lon_cal = lon_cal
        )
      }
    )
  }, error = function(e) {
    cat(sprintf("[%s] Error in chunk: %s\n", Sys.time(), e$message))
  })
  
  gc()
}

# ---- Reset Plan ----
future::plan(sequential)
