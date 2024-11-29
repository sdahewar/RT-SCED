import subprocess
import os

# Output folder for results
output_folder = "scenario_results"
os.makedirs(output_folder, exist_ok=True)

# Get all the reduced scenario files
reduced_scenario_files = [f"reduced_scenario_{i+1}.dat" for i in range(25)]

# Store results
results = []

# Loop through each reduced scenario file
for scenario_idx, scenario_file in enumerate(reduced_scenario_files, start=1):
    print(f"Processing {scenario_file}...")

    # Create a sub-folder for each scenario to store the results
    scenario_folder = os.path.join(output_folder, f"scenario_{scenario_idx}")
    os.makedirs(scenario_folder, exist_ok=True)

    # Run the SCED model using subprocess
    try:
        # Run the simulation with the corresponding scenario file
        subprocess.run(
            ["python", "RunSCEDGenericCaseModel.py", scenario_file],
            check=True,
            capture_output=True,
        )

        # Save results uniquely inside the scenario-specific folder
        result_file = os.path.join(scenario_folder, f"results_scenario_{scenario_idx}.txt")
        if os.path.exists("results.txt"):
            os.rename("results.txt", result_file)
        print(f"Results for scenario {scenario_idx} saved to {result_file}")
        results.append(f"Scenario {scenario_idx}: Success")

    except subprocess.CalledProcessError as e:
        print(f"Error running SCED for scenario {scenario_idx}: {e}")
        results.append(f"Scenario {scenario_idx}: Failed")

# Write all results to a consolidated results file inside the main output folder
with open(os.path.join(output_folder, "scenario_results_summary.txt"), "w") as summary_file:
    for result in results:
        summary_file.write(result + "\n")

print("All scenarios processed.")
