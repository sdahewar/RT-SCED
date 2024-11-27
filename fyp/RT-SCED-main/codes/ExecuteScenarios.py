import pandas as pd
import subprocess
import os

# Filepath for the structured scenarios
structured_scenarios_file = "structured_scenarios.dat"

# Output folder for results
output_folder = "scenario_results"
os.makedirs(output_folder, exist_ok=True)

# Read the file while skipping header and footer lines
with open(structured_scenarios_file, "r") as f:
    lines = f.readlines()

# Extract only the rows with scenario data (ignoring header and footer)
scenario_data_lines = lines[2:-1]  # Skip first 2 lines (header) and the last line (footer)

# Convert lines into a DataFrame
scenario_data = pd.DataFrame(
    [line.strip().split() for line in scenario_data_lines],
    columns=["Scenario_Index", "Solar_Generation", "Wind_Generation"]
)

# Debug: Print raw DataFrame after reading
print("\nRaw Data Loaded:")
print(scenario_data)

# Convert columns to appropriate types
scenario_data["Scenario_Index"] = scenario_data["Scenario_Index"].astype(int)
scenario_data["Solar_Generation"] = scenario_data["Solar_Generation"].astype(float)
scenario_data["Wind_Generation"] = scenario_data["Wind_Generation"].astype(float)

# Debug: Print filtered DataFrame
print("\nFiltered Data:")
print(scenario_data)

# Ensure data is not empty
if scenario_data.empty:
    raise ValueError("Filtered data is empty. Check the structured_scenarios.dat file format.")

# Generate scenario .dat files and run simulations
results = []
for _, row in scenario_data.iterrows():
    scenario_idx = int(row["Scenario_Index"])
    solar_gen = row["Solar_Generation"]
    wind_gen = row["Wind_Generation"]

    # Create .dat file for this scenario
    scenario_file = f"scenario_{scenario_idx}.dat"
    with open(scenario_file, "w") as f:
        f.write(f"param: GEN: :=\n")
        f.write(f"10 'SOLAR_GEN' 1 {solar_gen} 50.0 0.0 5.0 0.0 0\n")
        f.write(f"3 'WIND_GEN' 1 {wind_gen} 70.0 0.0 10.0 0.0 0\n")
        f.write(";\n")
    print(f"Generated {scenario_file}")

    # Run the SCED model
    try:
        subprocess.run(
            ["python", "RunSCEDGenericCaseModel.py", scenario_file],
            check=True,
            capture_output=True,
        )

        # Save results uniquely
        result_file = os.path.join(output_folder, f"results_scenario_{scenario_idx}.txt")
        if os.path.exists("results.txt"):
            os.rename("results.txt", result_file)
        print(f"Results for scenario {scenario_idx} saved to {result_file}")
        results.append(f"Scenario {scenario_idx}: Success")

    except subprocess.CalledProcessError as e:
        print(f"Error running SCED for scenario {scenario_idx}: {e}")
        results.append(f"Scenario {scenario_idx}: Failed")

# Write all results to a consolidated results file
with open(os.path.join(output_folder, "scenario_results_summary.txt"), "w") as summary_file:
    for result in results:
        summary_file.write(result + "\n")

print("All scenarios processed.")
