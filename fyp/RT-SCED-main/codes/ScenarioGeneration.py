import pandas as pd
from sklearn.cluster import KMeans

# Load Austrian data
data = pd.read_csv("Austria_data_2016-2019.csv")

# Check if there's a time column and convert it
if 'utc_timestamp' not in data.columns:
    raise KeyError("The column 'utc_timestamp' does not exist in the dataset. Check the column name.")
data['utc_timestamp'] = pd.to_datetime(data['utc_timestamp'])
data.set_index('utc_timestamp', inplace=True)

# Validate solar and wind column names
if 'solar' not in data.columns or 'wind' not in data.columns:
    raise KeyError("The columns 'solar' and 'wind' do not exist in the dataset. Check the column names.")

solar_data = data['solar']
wind_data = data['wind']

# Scale the data to the desired max values
data['solar'] = solar_data / solar_data.max() * 50.0  # Scale to 50 MW for solar
data['wind'] = wind_data / wind_data.max() * 70.0     # Scale to 70 MW for wind

# Resample data (daily average)
solar_daily = data['solar'].resample('D').mean()
wind_daily = data['wind'].resample('D').mean()

# Combine solar and wind data
combined = pd.DataFrame({'solar': solar_daily, 'wind': wind_daily}).dropna()

# Apply k-means clustering for scenario reduction (4 scenarios for each)
kmeans_solar = KMeans(n_clusters=4, random_state=42).fit(combined[['solar']])
kmeans_wind = KMeans(n_clusters=4, random_state=42).fit(combined[['wind']])

# Extract scenarios (cluster centers)
solar_scenarios = kmeans_solar.cluster_centers_.flatten()
wind_scenarios = kmeans_wind.cluster_centers_.flatten()

# Create a structured DataFrame with scenario_index instead of Scenario names
scenario_data = []
scenario_index = 1
for solar in solar_scenarios:
    for wind in wind_scenarios:
        scenario_data.append({
            "Scenario_Index": scenario_index,
            "Solar_Generation": round(solar, 2),
            "Wind_Generation": round(wind, 2)
        })
        scenario_index += 1

# Convert to DataFrame
scenario_table = pd.DataFrame(scenario_data)

# Save the table to a .dat file
output_file = "structured_scenarios.dat"
with open(output_file, 'w') as f:
    f.write("# Scenario Table for Solar and Wind Generation\n")
    f.write("param: Scenario_Index Solar_Generation Wind_Generation :=\n")
    for _, row in scenario_table.iterrows():
        f.write(f"{row['Scenario_Index']} {row['Solar_Generation']} {row['Wind_Generation']}\n")
    f.write(";\n")

print(f"Scenarios have been saved to {output_file}")
