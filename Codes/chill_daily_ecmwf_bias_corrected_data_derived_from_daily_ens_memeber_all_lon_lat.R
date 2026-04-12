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

# Convert hourly temp table
hourtemps_long_tbl <- function(df) {
  df |>
    pivot_longer(
      cols = starts_with("Hour_"),
      names_to = "Hour",
      names_prefix = "Hour_",
      names_transform = list(Hour = as.integer),
      values_to = "temp_c"
    ) |>
    mutate(date_hour = make_datetime(Year, Month, Day, Hour,
                                     tz = "America/Los_Angeles")) |>
    select(date_hour, temp_c)
}

# Create calendar
years <- 1981:2024
cld <- data.frame(dt = seq(as.Date(paste0(years[1], "-11-01")),
                           as.Date(paste0(years[length(years)], "-12-31")),
                           by = "days")) |>
  filter(
    (year(dt) == years[1] & month(dt) %in% c(11, 12)) |
      (year(dt) != years[length(years)] & month(dt) %in% c(11, 12, 1, 2)) |
      (year(dt) == years[length(years)] & month(dt) %in% c(1, 2))
  )

# Load sample grid info
obs_base_path <- 'path to GRIDMET maximum temperature files'
tmax_file <- nc_open(file.path(obs_base_path, "tmx", paste0("tmmx_1981.nc")))
lons <- ncvar_get(tmax_file, "lon")
lats <- ncvar_get(tmax_file, "lat")
nc_close(tmax_file)

# Subset lons/lats as used in bias-corrected data
lon_cal <- lons[8:256]
lat_cal <- lats[178:407]

#  Load bias-corrected 2-member data
data_path <- 'path to bias-corrected ECMWF temperature forecasts from daily forecasts'
bias_cor_tmx <- readRDS(file.path(data_path, 'ECMWF_tmx_daily_bias_corrected_using_methods_mentioned_in_the_article.RDS'))
bias_cor_tmx <- readRDS(file.path(data_path, 'ECMWF_tmin_daily_bias_corrected_using_methods_mentioned_in_the_article.RDS'))
cat("Loaded bias_cor_tmx dims: ", paste(dim(bias_cor_tmx), collapse = " x "), "\n")

#  Check index mapping
valid_indices <- read.csv(os.path.join(path to dir 'plot_data_published', 'pts_where_crops.csv'))
# Fix: get actual lat/lon from full grid
valid_lons <- lons[valid_indices[, "i"]]
valid_lats <- lats[valid_indices[, "j"]]

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

# Output path
#mod_outpath <- '/glade/work/prajha/data/mod_daily_bc_daily'
mod_outpath <- 'path where you want to save output files'
dir.create(mod_outpath, showWarnings = FALSE, recursive = TRUE)

#  Processing function
process_grid_cell_safe <- function(i, j, lat, tmx, tmin, lat_cal, lon_cal) {
  cell_id <- sprintf("lon=%.4f, lat=%.5f", lon_cal[i], lat_cal[j])
  cat(sprintf("[%s] Processing %s\n", Sys.time(), cell_id))
  
  # Basic input checks
  if (!is.matrix(tmx) || !is.matrix(tmin)) {
    cat(sprintf("[%s] Skipped %s — tmx or tmin is not matrix\n", Sys.time(), cell_id))
    return(NULL)
  }
  if (all(is.na(tmx)) && all(is.na(tmin))) {
    cat(sprintf("[%s] Skipped %s — all NA values\n", Sys.time(), cell_id))
    return(NULL)
  }
  
  n_members <- dim(tmx)[2]
  daily_chill_list <- vector("list", n_members)
  
  for (mem in seq_len(n_members)) {
    temp_df <- data.frame(dt = cld$dt, tmin = tmin[, mem], tmx = tmx[, mem])
    chillr_obs <- chillr_tbl(temp_df)
    
    hourly_chill_obs <- tryCatch({
      chillR::make_hourly_temps(latitude = lat, year_file = chillr_obs)
    }, error = function(e) {
      cat(sprintf("[%s] Hourly failed for %s, member %d: %s\n", Sys.time(), cell_id, mem, e$message))
      return(NULL)
    })
    
    if (is.null(hourly_chill_obs)) next
    
    obs_vt_tbl <- hourtemps_long_tbl(hourly_chill_obs)
    
    # EXACT chill calculation from second script:
    chillport_tbl <- obs_vt_tbl |>
      dplyr::mutate(
        date = as.Date(date_hour),
        chillport = chillR::Dynamic_Model(temp_c)
      ) |>
      dplyr::group_by(date) |>
      dplyr::summarise(daily_chill = max(chillport) - min(chillport), .groups = "drop") |>
      dplyr::rename(!!paste0("daily_chill_", mem) := daily_chill)
    
    daily_chill_list[[mem]] <- chillport_tbl
  }
  
  # Remove NULL elements for failed members
  daily_chill_list <- daily_chill_list[!sapply(daily_chill_list, is.null)]
  
  if (length(daily_chill_list) == 0) {
    cat(sprintf("[%s] No valid member output for %s\n", Sys.time(), cell_id))
    return(NULL)
  }
  
  combined_chill <- purrr::reduce(daily_chill_list, full_join, by = "date")
  
  ensemble_daily_chill <- combined_chill |>
    dplyr::mutate(
      mean_daily_chill = round(rowMeans(dplyr::across(dplyr::starts_with("daily_chill_")), na.rm = TRUE), 3)
    ) |>
    dplyr::select(date, mean_daily_chill)
  
  filename <- sprintf("mod_daily_bc_lon%.4f_lat%.5f.csv", lon_cal[i], lat_cal[j])
  filename_safe <- gsub("-", "m", filename)
  out_file <- file.path(mod_outpath, filename_safe)
  
  readr::write_csv(ensemble_daily_chill, out_file)
  cat(sprintf("[%s] Saved %s\n", Sys.time(), out_file))
  
  gc()
  return(cell_id)
}

# Setup parallel
setup_parallel <- function(max_cores = 16, max_mem_gb = 8, chunk_size = 10) {
  pbs_cores <- as.integer(Sys.getenv("PBS_NUM_PPN", unset = NA))
  if (!is.na(pbs_cores)) max_cores <- pbs_cores
  Sys.setenv(R_FUTURE_AVAILABLECORES_FALLBACK = max_cores)
  
  available_cores <- future::availableCores()
  n_cores <- min(max_cores, available_cores)
  options(future.globals.maxSize = max_mem_gb * 1024^3)
  future::plan(future::multisession, workers = n_cores)
  
  cat(sprintf("[%s] Parallel plan set: %d cores (%d available), %d GB per worker\n",
              Sys.time(), n_cores, available_cores, max_mem_gb))
  return(list(n_cores = n_cores, chunk_size = chunk_size))
}

# Run chunks
params <- setup_parallel(max_cores = 16, max_mem_gb = 8, chunk_size = 10)
chunk_size <- params$chunk_size
chunks <- split(final_indices, ceiling(seq_len(nrow(final_indices)) / chunk_size))

for (chunk in chunks) {
  cat(sprintf("[%s] Processing new chunk (%d cells)\n", Sys.time(), nrow(chunk)))
  
  chunk$tmax_slice <- purrr::map2(chunk$i, chunk$j, function(x, y) {
    arr <- bias_cor_tmx[x, y, , ]
    if (is.null(dim(arr))) {
      matrix(NA, nrow = dim(bias_cor_tmx)[3], ncol = dim(bias_cor_tmx)[4])
    } else {
      arr
    }
  })
  
  chunk$tmin_slice <- purrr::map2(chunk$i, chunk$j, function(x, y) {
    arr <- bias_cor_tmin[x, y, , ]
    if (is.null(dim(arr))) {
      matrix(NA, nrow = dim(bias_cor_tmin)[3], ncol = dim(bias_cor_tmin)[4])
    } else {
      arr
    }
  })
  
  chunk$lat_slice  <- lat_cal[chunk$j]
  
  
  tryCatch({
    results <- furrr::future_pmap(
      list(
        i = chunk$i,
        j = chunk$j,
        tmx = chunk$tmax_slice,
        tmin = chunk$tmin_slice,
        lat = chunk$lat_slice
      ),
      function(i, j, tmx, tmin, lat) {
        process_grid_cell_safe(i, j, lat, tmx, tmin, lat_cal, lon_cal)
      }
    )
    cat(sprintf("[%s] Completed chunk, %d cells processed\n", Sys.time(), length(compact(results))))
  }, error = function(e) {
    cat(sprintf("[%s]  Error in chunk: %s\n", Sys.time(), e$message), "\n")
  })
  
  gc()
}

future::plan(sequential)
