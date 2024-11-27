import pandas as pd
import subprocess
import os

# Load the scenario table
scenario_table = pd.read_csv("structured_scenarios.dat", sep=" ", comment="#",
                             names=["Scenario", "Solar_Generation", "Wind_Generation"], skiprows=1, skipfooter=1, engine='python')

results = []  # Store results for all scenarios

# Iterate through each row in the scenario table
for idx, row in scenario_table.iterrows():  
    if isinstance(idx, tuple):  # Handle tuple case
        idx = idx[0]

    scenario_name = row["Scenario"]
    solar_gen = row["Solar_Generation"]
    wind_gen = row["Wind_Generation"]

    # Generate a Pyomo-compatible .dat file for this scenario
    scenario_file = f"scenario_{idx + 1}.dat"
    with open(scenario_file, "w") as f:
        f.write(f"param: GEN: :=\n")
        f.write(f"10 'SOLAR_GEN' 1 {solar_gen} 50.0 0.0 5.0 0.0 0\n")
        f.write(f"3 'WIND_GEN' 1 {wind_gen} 70.0 0.0 10.0 0.0 0\n")
        f.write(";\n")

    # Run the SCED model for this scenario
    print(f"Running SCED for {scenario_name}...")
    try:
        subprocess.run(["python", "RunSCEDGenericCaseModel.py", scenario_file], check=True)

        # Assuming results are written to results.txt, rename it for this scenario
        result_file = f"results_scenario_{idx + 1}.txt"
        if os.path.exists("results.txt"):
            os.rename("results.txt", result_file)

        # Collect the results for the scenario
        with open(result_file, "r") as rf:
            scenario_result = rf.read()
            results.append({"Scenario": scenario_name, "Results": scenario_result})

    except subprocess.CalledProcessError as e:
        print(f"Error running SCED for scenario {scenario_name}: {e}")
        results.append({"Scenario": scenario_name, "Results": "Error"})

# Write all results to a consolidated table
with open("scenario_results.txt", "w") as result_file:
    for result in results:
        result_file.write(f"Scenario: {result['Scenario']}\n")
        result_file.write(f"Results:\n{result['Results']}\n")
        result_file.write("="*50 + "\n")
