rm(list=ls())
pacman::p_load(ncdf4,dplyr,lubridate,abind,raster,purrr,chillR,tidyr,sf,terra,zoo,gridExtra)
# Load required packages

#######################################################################################################################
###################################### Part 1: Loading the tmx and tmin data from PRISM ###############################
# Paths to data
obs_base_path <- "directory where annual GRIDMET tmax and tmin files are present"
tmax_path <- file.path(obs_base_path, "tmx")
tmin_path <- file.path(obs_base_path, "tmin")

# Observation Years
obs_years <- 1979:2024  # Adjusted for the specified years
## Make hourly temp. Latitude is needed to make hourly temp
hourtemps_long_tbl <- function(df){
  df_long <- df |>
    pivot_longer(cols = starts_with("Hour_"),
                 names_to = "Hour",
                 names_prefix = "Hour_",
                 names_transform = list(Hour = as.integer),
                 values_to = "temp_c") |>
    mutate(date_hour = lubridate::make_datetime(year = Year, month = Month,
                                                day = Day, hour = Hour,
                                                tz = "America/Los_Angeles")) |>
    dplyr::select(date_hour, temp_c)
  return(df_long)
}

chillr_tbl <- function(df){
  minmax_chillr_tbl <- 
    df |> 
    mutate(Year = lubridate::year(dt),
           Month = lubridate::month(dt),
           Day = lubridate::day(dt),
           Tmax = as.numeric(tmx),
           Tmin = as.numeric(tmin)) |> 
    dplyr::select(DATE = dt, Year, Month, Day, Tmax, Tmin)
  return(minmax_chillr_tbl)
}

# Initialize lists to store data
daily_tmax_all <- list()
daily_tmin_all <- list()

# Loop through each year to load and process the data
for (year in obs_years) {
  # Define file paths for Tmax and Tmin data
  filename_tmax <- file.path(tmax_path, paste0("tmmx_", year, ".nc"))
  filename_tmin <- file.path(tmin_path, paste0("tmmn_", year, ".nc"))
  
  # Load Tmax data
  nc_tmax <- nc_open(filename_tmax)
  lat <- ncvar_get(nc_tmax, "lat")
  lon <- ncvar_get(nc_tmax, "lon")
  tmax <- ncvar_get(nc_tmax, "air_temperature")
  missing_value <- ncatt_get(nc_tmax, "air_temperature", "missing_value")$value
   # Convert to Celsius
  tmax_subset_celsius <- tmax - 273.15
  
  # Store Tmax data for the current year
  daily_tmax_all[[as.character(year)]] <- tmax_subset_celsius
  
  # Close the Tmax netCDF file
  nc_close(nc_tmax)
  
  # Load Tmin data
  nc_tmin <- nc_open(filename_tmin)
  tmin <- ncvar_get(nc_tmin, "air_temperature")
  missing_value_tmin <- ncatt_get(nc_tmin, "air_temperature", "missing_value")$value
  
  # Mask missing values in Tmin data
  tmin[tmin == missing_value_tmin] <- NA
  
  # Convert to Celsius
  tmin_subset_celsius <- tmin - 273.15
  
  # Store Tmin data for the current year
  daily_tmin_all[[as.character(year)]] <- tmin_subset_celsius
  
  # Close the Tmin netCDF file
  nc_close(nc_tmin)
  print(year)
}

# Define the dimensions for the 4D array
lon_dim <- dim(daily_tmax_all[[1]])[1]  # Number of longitude points
lat_dim <- dim(daily_tmax_all[[1]])[2]  # Number of latitude points
year_dim <- length(names(daily_tmax_all))  # Number of years

# Assuming daily_chill_values will store the chill values for all lon, lat, and year combinations
daily_chill_values <- array(NA, dim = c(year_dim, 121), 
                            dimnames = list(
                              year = names(daily_tmax_all),
                              day = seq_len(121)  # Max possible days (121 for leap year, 120 for non-leap year)
                            ))

# Initialize an empty list to store data frames for each [lon, lat] combination
results_array <- vector("list", length = lon_dim * lat_dim)
names(results_array) <- paste0("lon_", rep(seq_len(lon_dim), each = lat_dim), 
                               "_lat_", rep(seq_len(lat_dim), times = lon_dim))

# Save lat and lon as CSV files
write.csv(lat, "latitude.csv", row.names = FALSE)
write.csv(lon, "longitude.csv", row.names = FALSE)

# Initialize an empty list for storing processed results
results_list <- list()

for (i in seq_len(lon_dim)) {  # Loop over longitude
  for (j in seq_len(lat_dim)) {  # Loop over latitude
    # Skip processing if the entire grid point contains NA values for all years
    all_na <- all(sapply(names(daily_tmax_all), function(year) {
      all(is.na(daily_tmax_all[[year]][i, j, ])) && 
        all(is.na(daily_tmin_all[[year]][i, j, ]))
    }))
    
    if (all_na) {
      next  # Skip this grid point and move to the next iteration
    }
    
    # Inner loop: Iterate over all years for the current grid point
    grid_data <- data.frame()
    for (k in seq_along(names(daily_tmax_all))) {
      year <- names(daily_tmax_all)[k]
      
      # Extract the corresponding Tmax and Tmin data for the current year and grid point
      tmax <- daily_tmax_all[[year]][i, j, ]  # 1D array: [day]
      tmin <- daily_tmin_all[[year]][i, j, ]  # 1D array: [day]
      
      # Generate a sequence of dates for the current year
      all_dates <- seq(as.Date(paste0(year, "-01-01")), as.Date(paste0(year, "-12-31")), by = "days")
      valid_indices <- which(format(all_dates, "%m") %in% c("11", "12", "01", "02"))  # Nov-Feb
      year_dates <- all_dates[valid_indices]  # Filtered dates
      
      # Filter Tmax and Tmin for the selected months
      tmax_series <- tmax[valid_indices]
      tmin_series <- tmin[valid_indices]
      
      # Combine the data into a single data frame for the current year
      year_df <- data.frame(
        dt = year_dates,
        tmx = tmax_series,
        tmin = tmin_series
      )
      
      # Convert the daily data to chillR format
      daily_mdl_chillr_tbl <- chillr_tbl(year_df)
      
      # Compute hourly temperatures
      hour_mod_daily_wide_tbl <- make_hourly_temps(
        latitude = lat[j],
        year_file = daily_mdl_chillr_tbl
      )
      
      # Convert hourly temperatures to long format
      mdl_vt_tbl <- hourtemps_long_tbl(hour_mod_daily_wide_tbl)
      
      # Compute chill portions for Nov-Feb
      chill_summary <- mdl_vt_tbl %>%
        mutate(chillport_acc = chillR::Dynamic_Model(temp_c)) %>%
        group_by(date = lubridate::date(date_hour)) %>%
        summarize(daily_chill = max(chillport_acc, na.rm = TRUE), .groups = "drop") %>%
        mutate(month = lubridate::month(date))  # Add month column to chill_summary
      
      # Get the appropriate daily chill values for Nov-Dec-Jan-Feb
      if (k == 1) {
        # Identify the starting row for November 1
        nov_start <- which(chill_summary$date == as.Date(paste0(obs_years[1],"-11-01")))
        
        # Create the new column for nocum_daily_chill
        chill_summary <- chill_summary %>%
          mutate(
            nocum_daily_chill = ifelse(
              row_number() < nov_start, 
              0, # Set all values before November 1 to 0
              daily_chill - lag(daily_chill, default = 0) # Calculate daily differences from November 1 onward
            )
          ) %>%
          dplyr::select(-daily_chill) %>%   # Remove the 'daily_chill' column
          rename(daily_chill = nocum_daily_chill)  # Rename 'nocum_daily_chill' to 'daily_chill'
        
        # Adjust the first value on November 1 to 0
        chill_summary$daily_chill[nov_start] <- 0
        
        # First year: only Nov-Dec
        daily_chill_for_grid_year <- chill_summary$daily_chill[chill_summary$month %in% c(11, 12)]
        
      } else if (k == year_dim) {
        # Last year: only jan-feb
        daily_chill_for_grid_year <- chill_summary$daily_chill[chill_summary$month %in% c(1, 2)]
      } else {
        # Intermediate years: Nov-Feb
        daily_chill_for_grid_year <- chill_summary$daily_chill[chill_summary$month %in% c(11, 12, 1, 2)]
      }
      
      # Store the daily chill values in the array
      daily_chill_values[k, 1:length(daily_chill_for_grid_year)] <- daily_chill_for_grid_year
    }
    chill_column <- t(daily_chill_values) %>% as.vector(.)
    
    # Define the range of years and days of year
    years <- obs_years
    # Define the years
    year1 <- years[1]
    year2_year3 <- (years[1]+1):years[length(years)]
    
    # Define DOY ranges
    doy_year1 <- 305:365  # DOY from 305 to 366 for year year1 (62 values)
    doy_year2_year3 <- c(1:59, 305:366)  # DOY from 1 to 59 (Jan-Feb) and 305 to 366 (Nov-Dec) for years 1980 and 1981 (121 values)
    
    # Create the year columns for year1, 1980, and 1981
    year_year1 <- rep(year1, length(doy_year1))  # Replicate year year1 for DOYs 305-366
    rep_years=length(years)-1
    rep_doy_year2_year3 = rep(doy_year2_year3, rep_years)
    rep_year2_3 <- rep(year2_year3, each=length(doy_year2_year3))
    # Combine year and DOY columns
    year_combined <- c(year_year1, rep_year2_3)
    doy_combined <- c(doy_year1, rep_doy_year2_year3)
    # Create the dataframe with the correct structure
    chill_dataframe <- data.frame(Year = year_combined, Day_of_Year = doy_combined, Chill = c(chill_column[1:61], chill_column[122:length(chill_column)]))
    #grid_data <- data.frame(Year = year_combined, Day_of_Year = doy_combined, Chill = c(chill_column[1:61], chill_column[122:length(chill_column)]))
    ## Chill of 1979 was not accumlated. Accumulate it.
    # Identify rows corresponding to the year 1979
    rows_1979 <- chill_dataframe$Year == 1979
    
    # Accumulate Chill values for the year 1979
    chill_dataframe$Chill[rows_1979] <- cumsum(chill_dataframe$Chill[rows_1979])
    
        ## correct Day of year in a way to reset at Nov 1 of each year and compute cumsum of nov-dec-jan-feb
    calculate_chill_adjusted <- function(df) {
      df <- df %>% arrange(Year, Day_of_Year) # Ensure data is ordered
      df$Chill_Adjusted <- NA                # Initialize new column
      
      # Function to check if a year is a leap year
      is_leap_year <- function(year) {
        (year %% 4 == 0 && year %% 100 != 0) || (year %% 400 == 0)
      }
      
      # Carry cumulative sum across years with resets
      for (rr in 1:nrow(df)) {
        if (rr == 1) {
          # Initialize the first row
          df$Chill_Adjusted[rr] <- df$Chill[rr]
        } else {
          prev_row <- df[rr - 1, ]
          current_row <- df[rr, ]
          
          # Determine the last day of the previous year (365 or 366)
          last_day_of_year <- ifelse(is_leap_year(prev_row$Year), 366, 365)
          
          # Determine the reset day of the current year (305 or 306)
          reset_day <- ifelse(is_leap_year(current_row$Year), 306, 305)
          
          # Reset or carry over logic
          if (current_row$Year != prev_row$Year && current_row$Day_of_Year == 1) {
            # Day 1 of a new year: carry over Chill from last day of previous year
            last_year_chill <- df[df$Year == prev_row$Year & df$Day_of_Year == last_day_of_year, "Chill"]
            if (!is.na(df$Chill_Adjusted[rr - 1])) {
              df$Chill_Adjusted[rr] <- current_row$Chill + df$Chill_Adjusted[rr - 1]
            } else {
              # Handle the case where previous Chill_Adjusted is NaN
              df$Chill_Adjusted[rr] <- current_row$Chill + df$Chill_Adjusted[rr - 2]
            }
          } else if (current_row$Day_of_Year == reset_day) {
            # Reset day: reset Chill_Adjusted based on the difference
            df$Chill_Adjusted[rr] <- df$Chill[rr] - prev_row$Chill
          } else {
            # Accumulation on normal days
            df$Chill_Adjusted[rr] <- prev_row$Chill_Adjusted + (df$Chill[rr] - prev_row$Chill)
          }
        }
      }
      return(df)
    }
    
    # Now use the function
    result <- calculate_chill_adjusted(chill_dataframe)
    # Define leap years based on the range of years in your dataset
    leap_years <- unique(result$Year[result$Year %% 4 == 0 & (result$Year %% 100 != 0 | result$Year %% 400 == 0)])
    
    # Modify Day_of_Year for leap years
    result <- result %>%
      mutate(Day_of_Year = ifelse(Year %in% leap_years & Day_of_Year == 305, 60, Day_of_Year)) %>% dplyr::select(-Chill) %>%                     # Remove the Chill column
      rename(Chill = Chill_Adjusted)
    
     # Round the "Chill" column to 2 decimal places
     result$Chill <- round(result$Chill, 2)    
    # Save grid-specific data to a CSV file
    filename <- sprintf("grid_lon_%d_lat_%d.csv", i, j)
    write.csv(result, file.path("chill_data", filename), row.names = FALSE)
    results_list[[paste0("lon_", i, "_lat_", j)]] <- filename
    
    }
  print(paste("Processed longitude:", i))  # Optional progress update
}

# Save the list of filenames as a JSON file
jsonlite::write_json(results_list, "results_metadata.json")
print("Processing complete. Data saved in 'processed_data/' and metadata saved as 'results_metadata.json'.")

