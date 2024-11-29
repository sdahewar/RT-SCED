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
        
        # Objective value
        try:
            fileSummary.write(f"Objective value is: {value(instance.minimizeCost)}\n")
        except Exception as e:
            fileSummary.write(f"Error retrieving objective value: {str(e)}\n")
        
        fileSummary.write("\n################## The following info is mainly for violations ##############\n")
        
        # Write generator information (including renewable generators)
        fileSummary.write("\n**************** Generator ******************\n")
        totalRegulationReserveShortage = 0.0
        totalSpinReserveShortage = 0.0
        totalPrimaryReserveShortage = 0.0
        totalRenewableGen = 0.0  # Track renewable generation
        
        # Header for generator data
        fileSummary.write("Index PgInSvc Pg_init Pgmax Pgmin Pg hasCostCurvData srReq_slack pgmax_slack pgmin_slack energyRampUp_Slack energyRampDown_Slack spinRampSlack\n")
        
        # Iterate through all generators
        for g in instance.GEN:
            try:
                gen_name = str(g)  # Ensure generator name is a string
                pg_value = value(instance.pg[g]) * instance.BaseMVA
                pg_in_svc = value(instance.Gen_isInSvc[g])  # Example: value for PgInSvc
                pg_init = value(instance.Gen_pgInit[g])  # Example: value for Pg_init
                pg_max = value(instance.Gen_pgMax[g])  # Example: value for Pgmax
                pg_min = value(instance.Gen_pgMin[g])  # Example: value for Pgmin
                has_cost_curv_data = value(instance.Gen_costCurveFlag[g])  # Example: value for hasCostCurvData
                sr_req_slack = value(instance.srReqSlackVar[g])  # Example: value for srReq_slack
                pgmax_slack = value(instance.pgmaxSlackVar[g])  # Example: value for pgmax_slack
                pgmin_slack = value(instance.pgminSlackVar[g])  # Example: value for pgmin_slack
                ramp_up_slack = value(instance.energyRampUpSlackVar[g])  # Example: energy ramp-up slack
                ramp_down_slack = value(instance.energyRampDownSlackVar[g])  # Example: energy ramp-down slack
                spin_ramp_slack = value(instance.spinRampSlackVar[g])  # Example: spin ramp slack
                
                # Write generator data (removed sr)
                fileSummary.write(f"{g} {pg_in_svc} {pg_init} {pg_max} {pg_min} {pg_value} {has_cost_curv_data} "
                                  f"{sr_req_slack} {pgmax_slack} {pgmin_slack} {ramp_up_slack} {ramp_down_slack} "
                                  f"{spin_ramp_slack}\n")

                # Check if generator is solar or wind and display accordingly
                if "SOLAR_GEN" in gen_name:
                    fileSummary.write(f"Solar Generator {gen_name}: Pg = {pg_value} MW\n")
                    totalRenewableGen += pg_value
                elif "WIND_GEN" in gen_name:
                    fileSummary.write(f"Wind Generator {gen_name}: Pg = {pg_value} MW\n")
                    totalRenewableGen += pg_value
                else:
                    if g == 8:
                        fileSummary.write(f"Solar Generator {gen_name}: Pg = {pg_value/100} MW\n")
                        totalRenewableGen += pg_value
                    elif g == 9:
                        fileSummary.write(f"Wind Generator {gen_name}: Pg = {pg_value/100} MW\n")
                        totalRenewableGen += pg_value
                    else:    
                        fileSummary.write(f"Conventional Generator {gen_name}: Pg = {pg_value} MW\n")

                # For non-renewable generators, track slack variables for reserves
                if hasattr(instance, 'rrSlackVar') and instance.rrSlackVar[g].value > 0:
                    totalRegulationReserveShortage += instance.rrSlackVar[g].value
                if hasattr(instance, 'srSlackVar') and instance.srSlackVar[g].value > 0:
                    totalSpinReserveShortage += instance.srSlackVar[g].value
                if hasattr(instance, 'prSlackVar') and instance.prSlackVar[g].value > 0:
                    totalPrimaryReserveShortage += instance.prSlackVar[g].value
            except Exception as e:
                fileSummary.write(f"Error processing generator {g}: {str(e)}\n")
        
        # Total Renewable Generation
        fileSummary.write(f"Total Renewable Generation: {totalRenewableGen/100} MW\n")
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
        
        # Write Interface Violations
        fileSummary.write("\n**************** Interface ***********\n")
        countNum = 0
        for k in instance.INTERFACE:
            if instance.interfaceLimiteSlackVar[k].value > 0:
                countNum += 1
                fileSummary.write(f"The total flow of interface {str(k)} is violated by "
                                  f"{str(instance.interfaceLimiteSlackVar[k].value * instance.BaseMVA)} MW, and the limit is: "
                                  f"{str(value(instance.Interface_totalLimit[k] * instance.BaseMVA))} MW\n")
        fileSummary.write(f"In total, there are {str(countNum)} interfaces that are violated\n")

        # **Add Load Data Table**
        fileSummary.write("\n****************** Load ******************\n")
        fileSummary.write("index loadBusNumber loadID load_IsInSvc Pload Pd_served Pd_shedded\n")
        for d in instance.LOAD:
            try:
                load_bus_number = instance.Load_busNumber[d]
                load_id = instance.Load_id[d]
                load_is_in_svc = instance.Load_isInSvc[d]
                p_load = value(instance.Load_pd[d]) * instance.BaseMVA
                p_served = instance.loadServed[d].value * instance.BaseMVA
                p_shedded = instance.loadShed[d].value * instance.BaseMVA
                fileSummary.write(f"{d} {load_bus_number} {load_id} {load_is_in_svc} {p_load} {p_served} {p_shedded}\n")
            except Exception as e:
                fileSummary.write(f"Error processing load {d}: {str(e)}\n")

         # **Add Generator Cost Table**
        fileSummary.write("\n**************** Generator Cost ******************\n")
        fileSummary.write("Index genIdx segmentIdx segmentBreadth segmentPrice Pgi\n")
        for i in instance.GENCOST:
            try:
                gen_idx = value(instance.GenCost_genIdx[i])
                segment_idx = value(instance.GenCost_segmentIdx[i])
                segment_breadth = value(instance.GenCost_segmentBreadth[i]) * instance.BaseMVA
                segment_price = value(instance.GenCost_segmentPrice[i])
                pgi = value(instance.pgi[i]) * instance.BaseMVA
                fileSummary.write(f"{i} {gen_idx} {segment_idx} {segment_breadth} {segment_price} {pgi}\n")
            except Exception as e:
                fileSummary.write(f"Error processing generator cost for generator {i}: {str(e)}\n")  


        # Write Branch (pkc) data at the top
        fileSummary.write("\n****************** Branch  Pkc******************\n")
        fileSummary.write("indexCtgcy ctgcyValid brcIdx brc_IsInSvcOrig pkc rateC\n")
        for c in instance.CONTINGENCY:
            try:
                if instance.Contingency_isEnabled[c] == 1:
                    for k in instance.BRANCH:
                        pkc_value = value(instance.pkc[c, k]) * instance.BaseMVA
                        rateC_value = value(instance.Branch_rateC[k]) * instance.BaseMVA
                        fileSummary.write(f"{c} {instance.Contingency_isEnabled[c]} {k} {instance.Branch_isInSvc[k]} "
                                          f"{pkc_value} {rateC_value}\n")
            except Exception as e:
                fileSummary.write(f"Error processing pkc data for contingency {c}, branch {k}: {str(e)}\n")  

        # Write Generator Pgc Results (pgc data)
        fileSummary.write("\n****************** Generator Pgc ******************\n")
        fileSummary.write("indexCtgcy ctgcyValid genIdx gen_IsInSvc pgc\n")
        for c in instance.CONTINGENCY:
            try:
                if instance.Contingency_isEnabled[c] == 1:
                   for g in instance.GEN:
                     # Check if pgc[g, c] is initialized (non-None)
                      if hasattr(instance, 'pgc') and (g, c) in instance.pgc:
                         pgc_value = value(instance.pgc[g, c]) * instance.BaseMVA  # Retrieve pgc value and scale by BaseMVA
                      else:
                        pgc_value = 0.0  # Default value for uninitialized pgc
                
                      gen_is_in_svc = value(instance.Gen_isInSvc[g])  # Check if generator is in service
                      fileSummary.write(f"{c} {instance.Contingency_isEnabled[c]} {g} {gen_is_in_svc} {pgc_value}\n")
            except Exception as e:
                fileSummary.write(f"Error processing pgc data for contingency {c}, generator {g}: {str(e)}\n")



               # Write Bus Data
        fileSummary.write("\n****************** Bus ******************\n")
        fileSummary.write("index busNumber busAngle\n")
        for n in instance.BUS:
            try:
               bus_number = instance.Bus_number[n]  # Bus number
               bus_angle = value(instance.theta[n])  # Bus angle
               fileSummary.write(f"{n} {bus_number} {bus_angle}\n")
            except Exception as e:
                fileSummary.write(f"Error processing bus {n}: {str(e)}\n")
 
           
           # Write Branch Lineflow Data
        fileSummary.write("\n****************** Branch ******************\n")
        fileSummary.write("index lineflow rateA slackVar\n")
        for k in instance.BRANCH:
            try:
                # Retrieve branch data
                lineflow = value(instance.pk[k])  # Lineflow for branch k
                rateA = value(instance.Branch_rateA[k])  # RateA for branch k
                slackVar = value(instance.brcFlowLimitSlackVar[k])  # Slack variable for branch k
        
                # Write branch data
                fileSummary.write(f"{k} {lineflow} {rateA} {slackVar}\n")
            except Exception as e:
                 fileSummary.write(f"Error processing branch {k}: {str(e)}\n")

                            

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
