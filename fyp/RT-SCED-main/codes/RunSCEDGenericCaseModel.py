"""
Created in 2016

# Author: Xingpeng Li

Website: https://rpglab.github.io/resources/RT-SCED_Python/
"""
import sys
import Diary
import ParamManager
import GeneralFunctions
import LoadInitFiles

from pyomo.environ import *
from pyomo.opt import SolverFactory
from SCEDGenericCaseModel import model as SCEDModel


# Check if a scenario file is passed as an argument
if len(sys.argv) < 2:
    print("Usage: python RunSCEDGenericCaseModel.py <scenario_file>")
    sys.exit(1)

scenario_file = sys.argv[1]
scenario_name = scenario_file.split(".")[0]  # Extract scenario name from file

# Load scenario data from the file
def load_scenario_data(file_path):
    generators = []
    try:
        with open(file_path, "r") as file:
            for line in file:
                if "SOLAR_GEN" in line or "WIND_GEN" in line:
                    parts = line.split()
                    generators.append({
                        "bus": int(parts[0]),
                        "type": parts[1],
                        "pgMax": float(parts[3]),
                        "pgMin": float(parts[4]),
                    })
    except Exception as e:
        print(f"Error reading scenario file: {e}")
        sys.exit(1)
    return generators
    


myDiary = Diary.Diary()
paramManager = ParamManager.ParamManager('configure.txt', myDiary)
isRunSCED = paramManager.getIsRunSCED()
isPyomoDataFilesAvailable = paramManager.getIsPyomoDataFilesAvailable()
generatePyomoDataFiles = paramManager.getGeneratePyomoDataFiles()
myDiary.hotlineWithLogType(7, "The generic-case data file directory is: " + paramManager.getPathGenericCase())

## Input pyomo file name
DatafileED = paramManager.getPyomoDataFormatInputFileGC()

# determine whether generate pyomo-format based file
isCodeWriteFiles = False
isCodeGeneratePyomoFiles = False
if isRunSCED == True:
    myDiary.hotline("The program will run the SCED simulation")
    if isPyomoDataFilesAvailable == True:
        myDiary.hotline("The program will first load the available pyomo-format based data files")
    else:
        isCodeWriteFiles = True
        isCodeGeneratePyomoFiles = True
        myDiary.hotline("The program will first generate the needed pyomo-format based data files")
else:
    myDiary.hotline("The program will NOT run the SCED simulation")
    isCodeWriteFiles = True
    if generatePyomoDataFiles == True:
        isCodeGeneratePyomoFiles = True
        myDiary.hotline("The program will only generate the needed pyomo-format based data files")
    else:
        myDiary.hotline("The program will only generate the regular-format based data files")

if isCodeWriteFiles == True:
    myDiary.hotline("Start to read needed data from raw file")
    pf = open(paramManager.getPathToRawFileNameGC(), "r")
    GeneralFunctions.skipNLines(pf, 3)
    buses = LoadInitFiles.loadBuses(pf, myDiary)
    loads = LoadInitFiles.loadLoads(pf, myDiary)
    gens = LoadInitFiles.loadGens(pf, myDiary)
    branches = LoadInitFiles.loadBranches(pf, myDiary)
    pf.close()
    myDiary.hotline("Finish reading needed data from raw file")

    myDiary.hotline("Ready for reading multiple-period energy ramp rate data")
    fileGenMultiRamp = open(paramManager.getPathToCostCurveMultiRampFileNameGC(), "r")
    GeneralFunctions.skipNLines(fileGenMultiRamp, 4)
    gensMultiRamp = LoadInitFiles.readCostCurveRamp(fileGenMultiRamp, myDiary)
    fileGenMultiRamp.close()

    myDiary.hotline("Ready for reading contingency-based spinning ramp rate data")
    fileGenSpinRamp = open(paramManager.getPathToCostCurveSpinRampFileNameGC(), "r")
    GeneralFunctions.skipNLines(fileGenSpinRamp, 4)
    gensSpinRamp = LoadInitFiles.readCostCurveRamp(fileGenSpinRamp, myDiary)
    fileGenSpinRamp.close()

    fileCostCurveOutput = open(paramManager.getPathToCostCurveOutputFileNameGC(), "r")
    GeneralFunctions.skipNLines(fileCostCurveOutput, 3)
    gensCostCurveOutput = LoadInitFiles.readCostCurveOutput(fileCostCurveOutput, myDiary)
    fileCostCurveOutput.close()

    import RawGenericModel
    genericModel = RawGenericModel.GenericModel(buses, loads, gens, branches, gensCostCurveOutput, gensMultiRamp, gensSpinRamp)

    import GeneratePyomoDataFiles
    dataWriter = GeneratePyomoDataFiles.generatePyomoFiles(isCodeGeneratePyomoFiles, myDiary)
    dataWriter.setGenericCaseModel(genericModel)
    dataWriter.setFileNamePyomoGC(paramManager.getPyomoDataFormatInputFileGC())
    dataWriter.setNeedHeading(paramManager.getNeedHeading())
    dataWriter.setIsPositivePgPmaxPminNeeded(paramManager.getIsPositivePgPmaxPminNeeded())
    dataWriter.writeAllDataGC()
    if isCodeGeneratePyomoFiles == True:
        DatafileED = dataWriter.getFileNamePyomoGC()

if isRunSCED == True:
    myDiary.hotlineWithLogType(7, "The name of the case data file loaded is: " + DatafileED)
    myDiary.hotlineWithLogType(5, "Start to load input data for pyomo simulation")
    print("Start to load original input data for pyomo simulation")
    # Read scenario-specific generators
# Load scenario-specific generators (solar and wind)
new_generators = []
with open(scenario_file, "r") as sf:
    for line in sf:
        # For solar and wind generation, extract the relevant data
        if "SOLAR_GEN" in line or "WIND_GEN" in line:
            parts = line.split()
            new_generators.append({
                "bus": int(parts[0]),           # Bus number
                "type": parts[1],               # Type (SOLAR_GEN or WIND_GEN)
                "pgMax": float(parts[3]),       # Maximum generation
                "pgMin": float(parts[4]),       # Minimum generation
                "pg_init": float(parts[10])     # Initial generation
            })

instanceSCED = SCEDModel.create_instance(DatafileED)

# Ensure the "Gen_type" and "Gen_costCurveFlag" parameters exist
if not hasattr(instanceSCED, "Gen_type"):
    instanceSCED.add_component("Gen_type", Param(instanceSCED.GEN, mutable=True))
if not hasattr(instanceSCED, "Gen_costCurveFlag"):
    instanceSCED.add_component("Gen_costCurveFlag", Param(instanceSCED.GEN, mutable=True, default=0))

# Load scenario-specific generators (solar and wind)
new_generators = []
with open(scenario_file, "r") as sf:
    for line in sf:
        # For solar and wind generation, extract the relevant data
        if "SOLAR_GEN" in line or "WIND_GEN" in line:
            parts = line.split()
            new_generators.append({
                "bus": int(parts[0]),           # Bus number
                "type": parts[1],               # Type (SOLAR_GEN or WIND_GEN)
                "pgMax": float(parts[3]),       # Maximum generation
                "pgMin": float(parts[4]),       # Minimum generation
                "pg_init": float(parts[10])     # Initial generation
            })

# Create the instance of the model with the given data file
instanceSCED = SCEDModel.create_instance(DatafileED)

# Add new generators (solar and wind) to the model
for gen in new_generators:
    gen_bus = gen["bus"]
    gen_type = gen["type"]
    pg_max = gen["pgMax"]
    pg_min = gen["pgMin"]
    pg_init = gen["pg_init"]
    
    # Add generator to the model
    instanceSCED.GEN.add(gen_bus)
    instanceSCED.Gen_isInSvc[gen_bus] = 1  # Set in-service status

    # Initialize parameters for this generator
    instanceSCED.Gen_pgMax[gen_bus] = pg_max
    instanceSCED.Gen_pgInit[gen_bus] = pg_init
    instanceSCED.Gen_pgMin[gen_bus] = pg_min
    instanceSCED.Gen_type[gen_bus] = gen_type
    instanceSCED.Gen_costCurveFlag[gen_bus] = 0  # Set to 0 by default

    # Add to Solar or Wind generators
    if gen_type == 'SOLAR_GEN':
        instanceSCED.SOLAR_GEN.add(gen_bus)
        instanceSCED.Solar_pgMax[gen_bus] = pg_max  # Solar pgMax
        instanceSCED.Solar_pgMin[gen_bus] = pg_min  # Solar pgMin
        instanceSCED.Solar_pg[gen_bus] = pg_init    # Initialize solar generation
    elif gen_type == 'WIND_GEN':
        instanceSCED.WIND_GEN.add(gen_bus)
        instanceSCED.Wind_pgMax[gen_bus] = pg_max  # Wind pgMax
        instanceSCED.Wind_pgMin[gen_bus] = pg_min  # Wind pgMin
        instanceSCED.Wind_pg[gen_bus] = pg_init    # Initialize wind generation

# **Explicitly initialize the renewable generation values**
# Ensure solar generation is initialized
if hasattr(instanceSCED, "Solar_pg"):
    for s in instanceSCED.SOLAR_GEN:
        # Initialize with the pg_init value for solar generation
        if instanceSCED.Solar_pg[s].value is None:  # Check if it's uninitialized
            instanceSCED.Solar_pg[s] = pg_init  # Assign initial value if uninitialized

# Ensure wind generation is initialized
if hasattr(instanceSCED, "Wind_pg"):
    for w in instanceSCED.WIND_GEN:
        # Initialize with the pg_init value for wind generation
        if instanceSCED.Wind_pg[w].value is None:  # Check if it's uninitialized
            instanceSCED.Wind_pg[w] = pg_init  # Assign initial value if uninitialized

# Ensure conventional generators (pg) are initialized with pg_init
for g in instanceSCED.GEN:
    if instanceSCED.pg[g].value is None:  # Check if it's uninitialized
        instanceSCED.pg[g] = instanceSCED.Gen_pgInit[g]  # Initialize with pg_init value

# Print out the generation of each generator for debugging
print("\nGenerator Output (Generation Values):\n")
# Print conventional generators
for g in instanceSCED.GEN:
    gen_name = str(g)  # Convert generator id to string for readability
    pg_value = value(instanceSCED.pg[g])  # Get the value of conventional generator's generation
    print(f"Generator {gen_name} Output (pg): {pg_value} MW")

# Print solar generation output
if hasattr(instanceSCED, "Solar_pg"):
    for s in instanceSCED.SOLAR_GEN:
        solar_pg_value = value(instanceSCED.Solar_pg[s])  # Get the value of solar generation
        print(f"Solar Generator {s} Output (Solar_pg): {solar_pg_value} MW")

# Print wind generation output
if hasattr(instanceSCED, "Wind_pg"):
    for w in instanceSCED.WIND_GEN:
        wind_pg_value = value(instanceSCED.Wind_pg[w])  # Get the value of wind generation
        print(f"Wind Generator {w} Output (Wind_pg): {wind_pg_value} MW")

print("New generators have been successfully added and initialized.")

# Now the model can proceed to preprocessing and solving
instanceSCED.preprocess()  # Preprocess the model before solving


# After loading the input data, perform additional steps if necessary
myDiary.hotlineWithLogType(5, "Finish loading input data for pyomo simulation - an instance has been created")
print("Finish loading original input data for pyomo simulation")

# Auto-fix data if required
autoFixData = True
if autoFixData:
    for idx in instanceSCED.GenCost_segmentBreadth.index_set():
        if value(instanceSCED.GenCost_segmentBreadth[idx]) < 0:
            instanceSCED.GenCost_segmentBreadth[idx] = 0
            myDiary.hotlineWithLogType(1, f"For GenCost segment input data item with index of {idx}, the segment breadth is negative, so it is set to 0")


    handle_CostCurveSegment_Pgmin = paramManager.getHandle_CostCurveSegment_Pgmin()
    if handle_CostCurveSegment_Pgmin == True:
        PgmaxTemp_fromCostCurve = {}
        for idx in instanceSCED.GenCost_genIdx.index_set():
            idxGen = value(instanceSCED.GenCost_genIdx[idx])
            if idxGen in PgmaxTemp_fromCostCurve:

                PgmaxTemp_fromCostCurve[idxGen] = PgmaxTemp_fromCostCurve[idxGen] + value(instanceSCED.GenCost_segmentBreadth[idx])
            else:
                PgmaxTemp_fromCostCurve[idxGen] = value(instanceSCED.GenCost_segmentBreadth[idx])
        for idxGen, Pgmax_fromCostCurve in PgmaxTemp_fromCostCurve.items():
            if value(instanceSCED.Gen_pgMin[idxGen]) > Pgmax_fromCostCurve:
                instanceSCED.Gen_pgMin[idxGen] = Pgmax_fromCostCurve
                myDiary.hotlineWithLogType(1, "The Pgmin of generator with index "+str(idxGen)+ " is inconsistent with the cost curve, so it is set to " + str(Pgmax_fromCostCurve))

    if autoFixData == True:
        isPositivePgPmaxPminNeeded = paramManager.getIsPositivePgPmaxPminNeeded()
        for idx in instanceSCED.Gen_pgInit.index_set():
            if value(instanceSCED.Gen_isInSvc[idx]) == 0:
                instanceSCED.Gen_pgInit[idx] = 0
            elif value(instanceSCED.Gen_pgMax[idx]) < value(instanceSCED.Gen_pgMin[idx]):
                instanceSCED.Gen_pgInit[idx] = (value(instanceSCED.Gen_pgMin[idx]) + value(instanceSCED.Gen_pgMax[idx]))/2
                instanceSCED.Gen_pgMin[idx] = value(instanceSCED.Gen_pgInit[idx])
                instanceSCED.Gen_pgMax[idx] = value(instanceSCED.Gen_pgInit[idx])
                myDiary.hotlineWithLogType(1, "For online generator "+str(idx)+" Pgmax < Pgmin, thus, they are set to (Pgmax+Pgmin)/2, as well as Pginit")
            elif value(instanceSCED.Gen_pgInit[idx]) < value(instanceSCED.Gen_pgMin[idx]):
                instanceSCED.Gen_pgInit[idx] = value(instanceSCED.Gen_pgMin[idx])
                myDiary.hotlineWithLogType(1, "For online generator "+str(idx)+" Gen_pgInit < Pgmin, thus, Gen_pgInit = Pgmin")
            elif value(instanceSCED.Gen_pgInit[idx]) > value(instanceSCED.Gen_pgMax[idx]):
                instanceSCED.Gen_pgInit[idx] = value(instanceSCED.Gen_pgMax[idx])
                myDiary.hotlineWithLogType(1, "For online generator "+str(idx)+" Gen_pgInit > Pgmax, thus, Gen_pgInit = Pgmax")
            if value(instanceSCED.Gen_energyRamp[idx]) < 0:
                instanceSCED.Gen_energyRamp[idx] = 0
                myDiary.hotlineWithLogType(1, "For generator "+str(idx)+" Gen_energyRamp is negative, thus, Gen_energyRamp = 0")
            if value(instanceSCED.Gen_spinRamp[idx]) < 0:
                instanceSCED.Gen_spinRamp[idx] = 0
                myDiary.hotlineWithLogType(1, "For generator "+str(idx)+" Gen_spinRamp is negative, thus, Gen_spinRamp = 0")
            if isPositivePgPmaxPminNeeded == True:
                if value(instanceSCED.Gen_pgMax[idx]) < 0:
                    instanceSCED.Gen_pgMax[idx] = 0
                    myDiary.hotlineWithLogType(1, "For generator "+str(idx)+" Gen_pgMax is negative, thus, Gen_pgMax = 0")
                if value(instanceSCED.Gen_pgMin[idx]) < 0:
                    instanceSCED.Gen_pgMin[idx] = 0
                    myDiary.hotlineWithLogType(1, "For generator "+str(idx)+" Gen_pgMin is negative, thus, Gen_pgMin = 0")
                if value(instanceSCED.Gen_pgInit[idx]) < 0:
                    instanceSCED.Gen_pgInit[idx] = 0
                    myDiary.hotlineWithLogType(1, "For generator "+str(idx)+" Gen_pgInit is negative, thus, Gen_pgMin = 0")

    baseMVA = 100  # in the objective function in the model.py code, manual change is needed if this number is not 100.
    for idx in instanceSCED.Load_pd.index_set():
        instanceSCED.Load_pd[idx] = value(instanceSCED.Load_pd[idx])/baseMVA
    for idx in instanceSCED.Gen_pgInit.index_set():
        instanceSCED.Gen_pgInit[idx] = value(instanceSCED.Gen_pgInit[idx])/baseMVA
        instanceSCED.Gen_pgMax[idx] = value(instanceSCED.Gen_pgMax[idx])/baseMVA
        instanceSCED.Gen_pgMin[idx] = value(instanceSCED.Gen_pgMin[idx])/baseMVA
        instanceSCED.Gen_energyRamp[idx] = value(instanceSCED.Gen_energyRamp[idx])/baseMVA
        instanceSCED.Gen_spinRamp[idx] = value(instanceSCED.Gen_spinRamp[idx])/baseMVA
    for idx in instanceSCED.GenCost_segmentBreadth.index_set():
        instanceSCED.GenCost_segmentBreadth[idx] = value(instanceSCED.GenCost_segmentBreadth[idx])/baseMVA
    for idx in instanceSCED.Branch_pkInit.index_set():
        instanceSCED.Branch_pkInit[idx] = value(instanceSCED.Branch_pkInit[idx])/baseMVA
        instanceSCED.Branch_rateA[idx] = value(instanceSCED.Branch_rateA[idx])/baseMVA
        instanceSCED.Branch_rateB[idx] = value(instanceSCED.Branch_rateB[idx])/baseMVA
        instanceSCED.Branch_rateC[idx] = value(instanceSCED.Branch_rateC[idx])/baseMVA
    for idx in instanceSCED.Interface_totalLimit.index_set():
        instanceSCED.Interface_totalLimit[idx] = value(instanceSCED.Interface_totalLimit[idx])/baseMVA

    TotalLoad = 0
    for idx in instanceSCED.Load_pd.index_set():
        if value(instanceSCED.Load_isInSvc[idx]) == 1:
            TotalLoad = TotalLoad + value(instanceSCED.Load_pd[idx])
    myDiary.hotlineWithLogType(6, "The total load for this case is: " + str(TotalLoad*baseMVA) + " MW")
    
    TotalGenInit = 0
    for idx in instanceSCED.Gen_pgInit.index_set():
        if value(instanceSCED.Gen_isInSvc[idx]) == 1:
            TotalGenInit = TotalGenInit + value(instanceSCED.Gen_pgInit[idx])
    myDiary.hotlineWithLogType(6, "The total generation for this case is: " + str(TotalGenInit*baseMVA) + " MW")

    TotalGenMax = 0
    for idx in instanceSCED.Gen_pgMax.index_set():
        if value(instanceSCED.Gen_isInSvc[idx]) == 1:
            TotalGenMax = TotalGenMax + value(instanceSCED.Gen_pgMax[idx])
    myDiary.hotlineWithLogType(6, "The total online generation capacity for this case is: " + str(TotalGenMax*baseMVA) + " MW")

    # the following adjustment may be needed for a lossy power flow model
    ratioGenLoad = TotalGenInit/TotalLoad
    for idx in instanceSCED.Load_pd.index_set():
        instanceSCED.Load_pd[idx] = value(instanceSCED.Load_pd[idx])*ratioGenLoad
    myDiary.hotlineWithLogType(6, "To consider loss, each load is increased by : " + str(ratioGenLoad*100-100) + "%")
    
    
    print ("Finish input data auto-adjustment process for pyomo simulation")
    instanceSCED.preprocess()
    #instanceSCED.pprint()   # will print all original data/constraints before opt-run
    
    opt = SolverFactory(paramManager.getSolverName())
    opt.options.tmlim = paramManager.getSolverTimLimit() # tmlim is for glpk
    opt.options.mipgap = paramManager.getSolverOptGap()
    myDiary.hotlineWithLogType(0, "The solver used is: " + paramManager.getSolverName())
    myDiary.hotlineWithLogType(0, "The solver time limit is: " + paramManager.getSolverTimLimit() + " seconds")
    myDiary.hotlineWithLogType(0, "The solver optimization gap is: " + paramManager.getSolverOptGap())

    myDiary.hotlineWithLogType(5, "Start to solve pyomo case")
    results = opt.solve(instanceSCED, suffixes=['rc','dual'],tee=True)
    
    myDiary.hotlineWithLogType(5, "Finish solving pyomo case")

    myDiary.hotlineWithLogType(6, "results.Solution.Status: " + str(results.Solution.Status))
    myDiary.hotlineWithLogType(6, "results.solver.status: " + str(results.solver.status))
    myDiary.hotlineWithLogType(6, "results.solver.termination_condition: " + str(results.solver.termination_condition))
    myDiary.hotlineWithLogType(6, "results.solver.termination_message: " + str(results.solver.termination_message))

    print ("\nresults.Solution.Status: "), results.Solution.Status
    print ("Solver status:"), results.solver.status
    print ("Solver Termination Condition:"), results.solver.termination_condition
    print ("Solver Termination message :"), results.solver.termination_message
    #instanceSCED.display()  # all results will be shown, if we need all of them, we'd better redirect them to a file.

    # After the solver runs, print the values of renewable generation (Solar and Wind)
print("\nRenewable Generation After Solver:\n")

# Print Solar generation values after the solver
solar_gen_value = value(instanceSCED.pg[8])
print(f"Solar Generator 8 Output (Solar_pg) After Solver: {solar_gen_value} MW")

# Print Wind generation values after the solver
wind_gen_value = value(instanceSCED.pg[9])
print(f"Wind Generator 9 Output (Wind_pg) After Solver: {wind_gen_value} MW")

# File writing for generator data
import os
fileNameTmp = "genDataGC_Actually.txt"
if os.path.isfile(fileNameTmp):
    os.remove(fileNameTmp)

with open(fileNameTmp, 'a') as fileTmp:
    heading = " Index PgInSvc Pg_init Pgmax Pgmin EnergyRamp SpinRamp HasCostCurveData"
    heading = heading + "\n"
    fileTmp.write(heading)
    
    # Write the details of each generator in the model
    for g in instanceSCED.GEN:
        fileTmp.write("%s %d" % (" ", g))
        fileTmp.write("%s %d" % (" ", value(instanceSCED.Gen_isInSvc[g])))
        fileTmp.write("%s %f" % (" ", value(instanceSCED.Gen_pgInit[g]*baseMVA)))
        fileTmp.write("%s %f" % (" ", value(instanceSCED.Gen_pgMax[g]*baseMVA)))
        fileTmp.write("%s %f" % (" ", value(instanceSCED.Gen_pgMin[g]*baseMVA)))
        fileTmp.write("%s %f" % (" ", value(instanceSCED.Gen_energyRamp[g]*baseMVA)))
        fileTmp.write("%s %f" % (" ", value(instanceSCED.Gen_spinRamp[g]*baseMVA)))
        fileTmp.write("%s %d" % (" ", value(instanceSCED.Gen_costCurveFlag[g])))
        fileTmp.write("%s" % ("\n"))

import WriteResults
fileName = "resultsGC"
isDataForRC = False
WriteResults.Write_GenInfo(instanceSCED, fileName, isDataForRC, myDiary, scenario_name)

myDiary.close()
