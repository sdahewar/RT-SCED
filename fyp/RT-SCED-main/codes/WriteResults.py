from pyomo.environ import *
import os

def Write_GenInfo(instance, fileName, isDataForRC, myDiary, scenario_name):
    """
    Writes detailed results for a given scenario to a summary file and master log.
    """
    # Add scenario name to the summary file name
    fileNameSummary = f"{fileName}_{scenario_name}_summary.txt"
    deleteOldFiles(fileNameSummary, myDiary)
    with open(fileNameSummary, 'a') as fileSummary:
        myDiary.hotline(f"A new file {fileNameSummary} has been created")
        fileSummary.write(f"****************** Summary for {scenario_name} ******************\n")
        fileSummary.write(f"Scenario: {scenario_name}\n")
        
        try:
            fileSummary.write("Objective value is:  %s\n" % (value(instance.minimizeCost)))
        except Exception as e:
            fileSummary.write("Error retrieving objective value: %s\n" % str(e))

        fileSummary.write("\n################## The following info is mainly for violations ##############\n")
        
        # Write generator information including renewables
        fileSummary.write("\n**************** Generator ******************\n")
        totalRegulationReserveShortage = 0.0
        totalSpinReserveShortage = 0.0
        totalPrimaryReserveShortage = 0.0
        totalRenewableGen = 0.0  # Track renewable generation

        for g in instance.GEN:
            try:
                gen_name = str(g)  # Ensure generator name is a string
                pg_value = value(instance.pg[g]) * instance.BaseMVA

                if "SOLAR_GEN" in gen_name or "WIND_GEN" in gen_name:
                    totalRenewableGen += pg_value
                    fileSummary.write(f"Renewable Generator {gen_name}: Pg = {pg_value} MW\n")
                else:
                    if instance.rrSlackVar[g].value > 0:
                        totalRegulationReserveShortage += instance.rrSlackVar[g].value
                    if instance.srSlackVar[g].value > 0:
                        totalSpinReserveShortage += instance.srSlackVar[g].value
                    if instance.prSlackVar[g].value > 0:
                        totalPrimaryReserveShortage += instance.prSlackVar[g].value
            except Exception as e:
                fileSummary.write(f"Error processing generator {g}: {str(e)}\n")

        fileSummary.write(f"Total Renewable Generation: {totalRenewableGen} MW\n")
        fileSummary.write(f"Total Regulation Reserve Shortage: {totalRegulationReserveShortage * instance.BaseMVA} MW\n")
        fileSummary.write(f"Total Spinning Reserve Shortage: {totalSpinReserveShortage * instance.BaseMVA} MW\n")
        fileSummary.write(f"Total Primary Reserve Shortage: {totalPrimaryReserveShortage * instance.BaseMVA} MW\n")
        
        # Write load shedding information
        fileSummary.write("\n*************** Load Shedding ************\n")
        totalLoadShed = 0.0
        for d in instance.LOAD:
            try:
                if instance.loadShed[d].value > 0:
                    totalLoadShed += instance.loadShed[d].value
                    fileSummary.write(f"Load {d}: Shedded = {instance.loadShed[d].value * instance.BaseMVA} MW\n")
            except Exception as e:
                fileSummary.write(f"Error processing load {d}: {str(e)}\n")
        fileSummary.write(f"Total Shedded Load: {totalLoadShed * instance.BaseMVA} MW\n")
        
        # Contingency-specific results
        fileSummary.write("\n*************** Contingency Results ************\n")
        for c in instance.CONTINGENCY:
            try:
                if instance.Contingency_isEnabled[c] == 1:
                    totalLoadShed_c = sum(value(instance.loadShed_c[c, d]) for d in instance.LOAD)
                    fileSummary.write(f"Contingency {c}: Total Shedded Load = {totalLoadShed_c * instance.BaseMVA} MW\n")
            except Exception as e:
                fileSummary.write(f"Error processing contingency {c}: {str(e)}\n")
        
        fileSummary.write("End of scenario results.\n")

    # Append results to a master summary file
    master_summary_file = "master_summary.txt"
    with open(master_summary_file, 'a') as masterFile:
        try:
            masterFile.write(f"{scenario_name}: Objective = {value(instance.minimizeCost)} MW, "
                             f"Total Renewable Generation = {totalRenewableGen} MW, "
                             f"Total Load Shed = {totalLoadShed * instance.BaseMVA} MW\n")
        except Exception as e:
            masterFile.write(f"{scenario_name}: Error writing master summary: {str(e)}\n")

    myDiary.hotlineWithLogType(5, f"Results for {scenario_name} have been written.")

def deleteOldFiles(fileName, myDiary):
    """
    Deletes old files if they exist.
    """
    if os.path.isfile(fileName):
        os.remove(fileName)
        myDiary.hotline("Original file " + fileName + " has been deleted")
