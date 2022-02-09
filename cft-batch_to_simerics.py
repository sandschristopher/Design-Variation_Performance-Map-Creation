import shutil
import numpy as np
import re
import csv
import os
import configparser
import subprocess
from math import radians
import pandas as pd
from modify_spro import *                                                       

'''
Takes .txt file filled with parameter values and converts it into a numpy array (column vector is one geometry variation).
Dimensions should be in [m] and angles should be in [deg].

Inputs:
txt_file [string] = name of .txt file containing geometry variation parameters
delimeter [string] = delimiter used within .txt file

Outputs:
values_array [np.array] = np.array of geometry parameter values
'''
def txt_to_np(txt_file, delimiter):

    array = []

    with open(txt_file) as txt:
        data = txt.readlines()
        for line in data:
            array.append(line.split(delimiter))

    values_array = np.array(array, dtype=object)

    return values_array


'''
Takes original .cft-batch file and creates a blank .cft-batch template for parameter manipulation.

Inputs:
cft_batch_file [string] = name of original .cft-batch file exported from CFturbo software
template_file [string] = name of output .cft-batch template 

Outputs:
variables [list] = variable names associated with the manipulated geometry parameters
units [list] = variable units associated with the manipulated geometry parameters
components [list] = component names listed within the .cft-batch file
'''
def make_template(cft_batch_file, template_file):

    components = []
    formatted_components = []

    with open(cft_batch_file, "r") as cft_batch:
        data = cft_batch.readlines()
        for line_number, line in enumerate(data):
            if "ExportComponents " in line:
                num_components = int(line.split("\"")[1])

                for index in range(1, num_components + 1):
                    component = data[line_number + index].split("\"")[3]
                    components.append(component)
                    
                    if "[" in component:
                        component = component.replace("[", " ").strip()
                    
                    if "]" in component:
                        component = component.replace("]", " ").strip()

                    formatted_components.append(component)
    
        cft_batch.close()

    variables = []

    with open(cft_batch_file, "r") as cft_batch:
        data = cft_batch.readlines()
        for line_number, line in enumerate(data):
            if "Type=" in line and "</" in line and "ExportInterface" not in line and bool(set(line.split("\"")) & set(components)) == False:
                value = re.search(">(.*)</", line).group(1)
                variable = re.search("</(.*)>", line).group(1)
                newline = line.replace(value, "{" + variable + "}")
                data[line_number] = newline
                variables.append(variable)

            if "ExportComponents " in line:
                for index in range(0, num_components):
                    newline = data[line_number + index + 1].replace(components[index], formatted_components[index])
                    data[line_number + index + 1] = newline
                break

        cft_batch.close()
    
    with open(template_file, "w") as template:
        template.writelines(data)
        template.close()

    units = []

    with open(cft_batch_file, "r") as cft_batch:
        data = cft_batch.readlines()
        for line_number, line in enumerate(data):
            if "Caption=" in line and "Desc=" in line:
                if "Array" in line:
                    unit = re.search("Unit=\"(.*)\"", line).group(1)

                    var = line.split(" ")[0].lstrip()[1:]
                    key = "</" + var + ">"
            
                    count = 0
                    while True:
                        if key in data[(line_number + 1) + count]:
                            break
                        count += 1

                    units += [unit] * count 

                elif "Vector" in line:
                    count = int(re.search("([\d])", line).group(1))
                    unit = re.search("Unit=\"(.*)\"", line).group(1)
                    units += [unit] * count 

                elif "Unit" not in line:
                    unit = "-"
                    units.append(unit)

                else:
                    unit = re.search("Unit=\"(.*)\"", line).group(1)
                    units.append(unit)
        
        cft_batch.close()
       
    return variables, units, components

'''
Assigns geometry variation parameters to new .cft-batch files.

Inputs:
cft_batch_file [string] = name of original .cft-batch file exported from CFturbo software
template_file [string] = name of output .cft-batch template 
variables [list] = variable names associated with the manipulated geometry parameters
units [list] = variable units associated with the manipulated geometry parameters
components [list] = component names listed within the .cft-batch file
values_array [np.array] = np.array of geometry parameter values
base_name [string] = base name of folder containing .stp files

Outputs:
variations [list] = list of variation file names
'''
def make_variations(cft_batch_file, template_file, variables, units, components, values_array, base_name):

    original_values = [[] for i in range(len(units))]

    with open(cft_batch_file, "r") as cft_batch:
        data = cft_batch.readlines()
        count = 0
        for line_number, line in enumerate(data):
            if "Type=" in line and "</" in line and "ExportInterface" not in line and bool(set(line.split("\"")) & set(components)) == False:
                value = re.search(">(.*)</", line).group(1)
                original_values[count] = [value]
                count += 1

    original_values = np.array(original_values)

    variations = []

    entire_values_array = np.hstack((original_values, values_array))

    for i, column in enumerate(entire_values_array.T):

        with open(template_file, "r") as template:
            data = template.readlines()

            for j, value in enumerate(column):

                if units[j] == "rad" and i != 0:
                    value = str(radians(float(value)))

                key = "{" + variables[j] + "}"
                 
                for line_number, line in enumerate(data):
                    if key in line:
                        data[line_number] = line.replace(key, value)
                        break

            for line_number, line in enumerate(data):
                '''
                if "<WorkingDir>" in line:
                    old_directory = re.search("<WorkingDir>(.*)</WorkingDir>", line).group(1)
                    new_directory = ".\\" + output_folder + "\\"
                    data[line_number] = line.replace(old_directory, new_directory)
                '''

                if "<BaseFileName>" in line:
                    old_name = re.search("<BaseFileName>(.*)</BaseFileName>", line).group(1)
                    solver_type = old_name.split("_")[-1]
                    data[line_number] = line.replace(old_name, base_name + str(i) + "_" + solver_type)

            new_file = base_name + str(i) + "_" + solver_type + ".cft-batch"

            with open(new_file, "w+") as new:
                new.writelines(data)
                new.close()

            template.close()

        variations.append(new_file)

    return variations


'''
Places each variation into a .bat file then runs .bat file to create respective .cft variations.

Inputs:
cft_batch_file [string] = output .bat file (CFturbo)
variations [list] = variation file names
'''
def make_batch(cft_bat_file, variations):

    base_steady_spro_files = []
    base_transient_spro_files = []
    
    with open(cft_bat_file, "a+") as batch:
        for index, variation in enumerate(variations):
            if index == 0:
                batch.truncate(0)

            batch.write("\"C:\Program Files\CFturbo 2021.2.0\CFturbo.exe\" -batch \"" + variation + "\"\n")
            if "steady" in variation:
                base_steady_spro_files.append(variation.replace(".cft-batch", ".spro"))
            if "transient" in variation:
                base_transient_spro_files.append(variation.replace(".cft-batch", ".spro"))

        batch.close()

    batch_path = os.path.abspath(cft_bat_file)
    folder_path = os.path.abspath(variations[0].split("_")[0])
    spro_path = os.path.abspath(variations[0].replace(".cft-batch", ".spro"))
    if not os.path.exists(spro_path) and not os.path.exists(folder_path):
        subprocess.call(batch_path)

    return base_steady_spro_files, base_transient_spro_files

'''
Alters the .spro files of the design variations and creates multiple .spro files for a design performance map.

Inputs:
base_name [string] = base name of folder containing .stp files
variations [list] = variation file names
rpm_type [string]
rpm_values [list]
flowrate_type [string]
flowrate_values [list]

Outputs:
spro_steady_files [list]
spro_transient_files [list]
'''
def performance_map(run_design_variation, stage_components, base_name, variations, rpm_data, rpm_values, flowrate_data, flowrate_values):

    already_run = False

    steady_spro_files = []
    transient_spro_files = []

    parent_path = os.getcwd()

    for file in os.listdir(parent_path):
        if ".spro" in file and "rpm" not in file:
            modify_spro(file, stage_components)
            with open(file, 'r') as infile:
                for line in infile:
                    if "vflow_out = " in line:
                        flowrate_design = float(line.split(" ")[-1].strip())
                        continue
                    if "Omega" in line and " = " in line:
                        rpm_design = float(line.split(" ")[-1].strip())
                        impeller_number = re.search("Omega(\d) = ", line).group(1)
                        break
            
            if rpm_data.lower() == "relative":
                rpm_list = [float(rpm_value)*rpm_design for rpm_value in rpm_values]
            elif rpm_data.lower() == "absolute":
                rpm_list = rpm_values
            else:
                print("Please choose either relative or absolute for rpm_type.")
                exit()

            if flowrate_data.lower() == "relative":
                flowrate_list = [float(flowrate_value)*flowrate_design for flowrate_value in flowrate_values]
            elif flowrate_data.lower() == "absolute":
                flowrate_list = flowrate_values
            else:
                print("Please choose either relative or absolute for flowrate_type.")
                exit()

            for check in os.listdir(parent_path):
                if str(flowrate_list[-1]) in check and str(round(rpm_list[-1]*9.54929)) in check and base_name + str(len(variations) - 1) in check:
                    already_run = True

            for rpm in rpm_list:
                for flowrate in flowrate_list:
                    new_file = file.split(".")[0] + "_" + str(round(rpm*9.54929)) + "rpm_" + str(flowrate).replace(".", "-") + "m3s.spro"
                    if already_run == False:
                        with open(file, 'r') as infile, open(new_file, 'w') as outfile: 
                            for line in infile:                                                                     
                                if ("Omega" + impeller_number + " = ") in line:                                                 
                                    outfile.write("\t\t" + "Omega" + impeller_number + " = " + str(rpm) + "\n")                 
                                elif ("vflow_out = ") in line:
                                    outfile.write("\t\t" + "vflow_out = " + str(flowrate) + "\n") 
                                else:
                                    outfile.write(line)

                    if "steady" in new_file:
                        steady_spro_files.append(new_file)
                    elif "transient" in new_file:
                        transient_spro_files.append(new_file)   

    if run_design_variation.lower() == "true":
        steady_spro_files = sorted(steady_spro_files, key=lambda file: int(re.search(base_name + "(\d+)", file).group(1)))
        transient_spro_files = sorted(transient_spro_files, key=lambda file: int(re.search(base_name + "(\d+)", file).group(1)))

    return steady_spro_files, transient_spro_files


'''
Asks the user to input the integer numbers associated with the starting and ending stage components.
Modifies the .spro files to include relevant user expressions for post-processing.
Places each variation into a .bat file then runs .bat file using Simerics.

Inputs:
spro_steady_files [list]
spro_transient_files [list]
simerics_batch_file [string] = name of output .bat file (Simerics)
output_folder [string] = name of output folder containing the resulting geometry variations
base_name [string] = base name of folder containing .stp files

Outputs:
spro_files [list] = .spro files
'''
def run_simerics_batch(stage_components, steady_spro_files, transient_spro_files, run_transient, simerics_batch_file, base_name):

    if os.path.exists(base_name + "0") == False and os.path.exists(steady_spro_files[0].replace(".spro", ".sres")) == False:

        for spro in steady_spro_files:
            modify_spro(spro, stage_components)

            with open(simerics_batch_file, "a+") as batch:
                for index, spro in enumerate(steady_spro_files):
                    if index == 0:
                        batch.truncate(0)
                    
                    batch.write("\"C:\Program Files\Simerics\SimericsMP.exe\" -run \"" + spro + "\"\n")

                batch.close()

        batch_path = os.path.abspath(simerics_batch_file)
        subprocess.call(batch_path)

    if run_transient == True and (os.path.exists(base_name + "0") == False and os.path.exists(transient_spro_files[0].replace(".spro", ".sres")) == False):

        for spro in transient_spro_files:
            modify_spro(spro, stage_components)

            with open(simerics_batch_file, "a+") as batch:
                for index, spro in enumerate(transient_spro_files):
                    if index == 0:
                        batch.truncate(0)

                    batch.write("\"C:\Program Files\Simerics\SimericsMP.exe\" -run \"" + spro + "\" " + "\"" + steady_spro_files[index].replace(".spro", ".sres") + "\"\n")
                    
                batch.close()

        batch_path = os.path.abspath(simerics_batch_file)
        subprocess.call(batch_path)

    return steady_spro_files + transient_spro_files

'''
Averages the each .sres file results and places the values in .csv file.

Inputs:
spro_files [list] = .spro files
output_folder [string] = name of output folder containing the resulting geometry variations
base_name [string] = base name of folder containing .stp files
avgWindow [int] = number of iterations to calculate average values
'''
def post_process(run_design_variation, spro_files, base_name, steady_avg_window, transient_avg_window):

    switch = False
    index = 0
    
    for spro in spro_files:

        if "transient" in spro and switch == False:
            index = 0
            switch = True

        design_number = re.search(base_name + "(\d+)", spro).group(1)

        solver_type = spro.split("_")[1]
        
        if solver_type == "steady":
            avgWindow = int(steady_avg_window)
        if solver_type == "transient":
            avgWindow = int(transient_avg_window)

        with open (spro, 'r') as infile:

            for line in infile.readlines():
                if "vflow_out" in line:
                    vflow_out = float(line.split("=")[1])
                    continue
                if "Omega" in line:
                    impeller_Number = re.search("Omega(\d) = ", line).group(1)
                    rpm = round(float(line.split("=")[1])*9.5493)
                    break

        integral_file = spro.split(".")[0] + "_integrals.txt"

        result_Dict = {}
        formatted_result_Dict = {}
        units_Dict, desc_Dict = get_Dicts(spro)
        with open (integral_file, 'r') as infile:                                   
            result_List = list(infile)                                                                  
            del result_List[1:-avgWindow]                                  
            reader = csv.DictReader(result_List, delimiter="\t")
            for row in reader:
                for key, value in row.items():
                    if 'userdef.' in key:                                                               
                        if key in result_Dict:                                                           
                            result_Dict[key] += float(value)                              
                        else:
                            result_Dict[key] = float(value)
            if run_design_variation.lower() == "true":
                formatted_result_Dict[base_name] = design_number
                units_Dict[base_name] = '-'
                desc_Dict[base_name] = '-'
            formatted_result_Dict['vflow_out'] = vflow_out
            units_Dict['vflow_out'] = '[m3/s]'
            desc_Dict['vflow_out'] = 'Outlet volumetric flux'
            formatted_result_Dict['Revolutions'] = rpm
            units_Dict['Revolutions'] = '[rpm]'
            desc_Dict['Revolutions'] = 'Outlet volumetric flux'
            for key, value in result_Dict.items():
                if 'userdef.' in key:
                    if "DPtt" + impeller_Number in key:
                        formatted_result_Dict['DPtt_imp'] = result_Dict[key]/avgWindow  
                    elif "Eff_tt_" + impeller_Number in key:
                        formatted_result_Dict['Eff_tt_imp'] = result_Dict[key]/(avgWindow)    
                    else:
                        formatted_result_Dict[key[8:]] = result_Dict[key]/(avgWindow)
        if run_design_variation.lower() == "true":                              
            order = [base_name, 'Revolutions', 'vflow_out', 'DPtt', 'DPtt_stage', 'DPtt_imp', 'Eff_tt', 'Eff_tt_stage', 'Eff_tt_imp', 'PC' + impeller_Number, 'Torque' + impeller_Number, 'H', 'H' + impeller_Number]
        else:
            order = ['Revolutions', 'vflow_out', 'DPtt', 'DPtt_stage', 'DPtt_imp', 'Eff_tt', 'Eff_tt_stage', 'Eff_tt_imp', 'PC' + impeller_Number, 'Torque' + impeller_Number, 'H', 'H' + impeller_Number]
        for var in formatted_result_Dict.keys():
            if var not in order:
                order.append(var)
        order_dict = {k: formatted_result_Dict[k] for k in order}
        with open ('results_' + solver_type + '.csv', 'a+', newline='') as outfile:                             
            writer = csv.DictWriter(outfile, fieldnames=order_dict.keys(), delimiter=",")             
            if index == 0:                                                        
                outfile.truncate(0)
                writer.writeheader()
                writer.writerow(units_Dict)
                writer.writerow(desc_Dict)                                                                    
            writer.writerow(formatted_result_Dict)
        index = index + 1

    return 0

def combine_csv(base_file_name):

    parent_path = os.getcwd()
    csv_files = []

    for file in os.listdir(parent_path):
        if 'results' in file and '.csv' in file:
            csv_files.append(file)

    writer = pd.ExcelWriter(base_file_name + '_results.xlsx', engine='xlsxwriter', engine_kwargs={'options': {'strings_to_numbers': True}})
    for csv in csv_files:
        solver_type = csv.split(".")[0].split("_")[-1]
        df = pd.read_csv(csv)
        df.to_excel(writer, sheet_name=solver_type, index=False)
    writer.save()

    return 0

'''
Organizes the files into folders based on design variations.

Inputs:
variations [list] = variation file names
output_folder [string] = name of output folder containing the resulting geometry variations
base_name [string] = base name of folder containing .stp files
'''
def organize_file_structure(variations, base_name):

    parent_path = os.getcwd()

    for index in range(len(variations)):
        for file in os.listdir(parent_path):
            if base_name in file:
                if re.match(base_name + "(\d+)", file).group(1) == str(index) and not os.path.isdir(file) and "steady" in file:
                    old_path = os.path.join(parent_path, file)
                    design_folder = os.path.join(parent_path, base_name + str(index))
                    if not os.path.exists(design_folder):
                        os.makedirs(design_folder)
                    steady_folder = os.path.join(design_folder, "steady")
                    if not os.path.exists(steady_folder):
                        os.makedirs(steady_folder)
                    new_path = os.path.join(steady_folder, file)        
                    shutil.move(old_path, new_path)
                
                if re.match(base_name + "(\d+)", file).group(1) == str(index) and not os.path.isdir(file) and "transient" in file:
                    old_path = os.path.join(parent_path, file)
                    design_folder = os.path.join(parent_path, base_name + str(index))
                    if not os.path.exists(design_folder):
                        os.makedirs(design_folder)
                    steady_folder = os.path.join(design_folder, "transient")
                    if not os.path.exists(steady_folder):
                        os.makedirs(steady_folder)
                    new_path = os.path.join(steady_folder, file)        
                    shutil.move(old_path, new_path)
         
    return 0

def main():

    stage_components = []
    stage_components.append(int(input("Enter the number associated with the initial stage component: ")))
    stage_components.append(int(input("Enter the number associated with the final stage component: ")))

    def Get_ConfigValue(ConfigSection, ConfigKey):                                                      
        ConfigValue = CFconfig[ConfigSection][ConfigKey]
        return ConfigValue

    CFconfig = configparser.ConfigParser()                                                             
    CFconfig.read("master.cftconf")
    base_file_name = Get_ConfigValue("DesignVariation","base_name")
    run_design_variation = Get_ConfigValue("DesignVariation","run_design_variation")  
    delimiter = Get_ConfigValue("DesignVariation","text_file_delimiter")  
    run_simerics = Get_ConfigValue("Simerics","run_simerics")
    run_performance_map = Get_ConfigValue("Simerics","run_performance_map")
    rpm_data = Get_ConfigValue("Simerics","rpm_data")
    rpm_values = Get_ConfigValue("Simerics","rpm_values").split(" ") 
    flowrate_data = Get_ConfigValue("Simerics","flowrate_data")
    flowrate_values = Get_ConfigValue("Simerics","flowrate_values").split(" ") 
    steady_avg_window = Get_ConfigValue("steady","avg_window")
    run_transient = Get_ConfigValue("transient","run_transient")
    transient_avg_window = Get_ConfigValue("transient","avg_window")

    if run_design_variation.lower() == "true":
        values_array = txt_to_np(base_file_name + ".txt", delimiter)
        variables, units, components = make_template(base_file_name + "_steady.cft-batch", "template_steady.cft-batch")
        variations = make_variations(base_file_name + "_steady.cft-batch", "template_steady.cft-batch", variables, units, components, values_array, "Design")

        if run_transient.lower() == "true":
            variables, units, components = make_template(base_file_name + "_transient.cft-batch", "template_transient.cft-batch")
            variations = variations + make_variations(base_file_name + "_transient.cft-batch", "template_transient.cft-batch", variables, units, components, values_array, "Design")

        base_steady_spro_files, base_transient_spro_files = make_batch(base_file_name + ".bat", variations)

        if run_simerics.lower() == "true":
            if run_performance_map.lower() == "true":
                steady_spro_files, transient_spro_files = performance_map(run_design_variation, stage_components, "Design", variations, rpm_data, rpm_values, flowrate_data, flowrate_values)
                spro_files = run_simerics_batch(stage_components, steady_spro_files, transient_spro_files, run_transient, base_file_name + "_simerics.bat", "Design")
            else:
                spro_files = run_simerics_batch(stage_components, base_steady_spro_files, base_transient_spro_files, run_transient, base_file_name + "_simerics.bat", "Design")

            post_process(run_design_variation, spro_files, "Design", steady_avg_window, transient_avg_window)
            combine_csv(base_file_name)
            organize_file_structure(variations, "Design")

    elif run_design_variation.lower() == "false" and run_simerics.lower() == "true":
        if run_performance_map.lower() == "true":
            steady_spro_files, transient_spro_files = performance_map(run_design_variation, stage_components, "Design", base_file_name + ".spro", rpm_data, rpm_values, flowrate_data, flowrate_values)
            spro_files = run_simerics_batch(stage_components, steady_spro_files, transient_spro_files, run_transient, base_file_name + "_simerics.bat", "Design")
        else:
            spro_files = run_simerics_batch(stage_components, base_file_name + "_steady.spro", base_file_name + "_transient.spro", run_transient, base_file_name + "_simerics.bat", "Design")

        post_process(run_design_variation, spro_files, "Design", steady_avg_window, transient_avg_window)
        combine_csv(base_file_name)

    else:
        exit()

main()