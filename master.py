import pandas as pd
import numpy as np
import configparser
import re
import csv
import os
import subprocess
from math import degrees, radians, pi
from modify_spro import *

def build_template(cft_batch_file, template_file):

    master = {}

    with open(cft_batch_file, 'r') as infile, open(template_file, 'w') as outfile:
        data = infile.readlines()
        for line_number1, line1 in enumerate(data):
            if "<ExportComponents " in line1:
                num_components = int(line1.split("\"")[1])
                for index in range(1, num_components + 1):
                    for line_number2, line2 in enumerate(data):
                        component = re.search("Caption=\"(.+?)\"", data[line_number1 + index]).group(1)
                        formatted_component = "".join(char for char in component if char.isalnum() or char in "_-")
                        if formatted_component not in master:
                            master[formatted_component] = {}
                        if "Name=\"" + component in line2:
                            book_end = line2.split(" ")[0].strip()[1:]
                            for line_number3, line3 in enumerate(data):
                                if "</" + book_end in line3:
                                    section = data[line_number2:line_number3]
                                    for line_number4, line4 in enumerate(section):
                                        if "Caption=" in line4:
                                            variable = line4.split(" ")[0].strip()[1:]
                                            master[formatted_component][variable] = {}

                                            try:
                                                var_type = re.search("Type=\"(.+?)\"", line4).group(1)
                                                master[formatted_component][variable]['var_type'] = var_type
                                            except AttributeError:
                                                next

                                            try:
                                                count = re.search("Count=\"(.+?)\"", line4).group(1)
                                                master[formatted_component][variable]['count'] = count
                                            except AttributeError:
                                                next

                                            try:
                                                caption = re.search("Caption=\"(.+?)\"", line4).group(1)
                                                master[formatted_component][variable]['caption'] = caption
                                            except AttributeError:
                                                next

                                            try:
                                                desc = re.search("Desc=\"(.+?)\"", line4).group(1)
                                                master[formatted_component][variable]['desc'] = desc
                                            except AttributeError:
                                                next
                                            
                                            try:
                                                unit = re.search("Unit=\"(.+?)\"", line4).group(1)
                                                master[formatted_component][variable]['unit'] = unit
                                            except AttributeError:
                                                next

                                            values = []
                                            markers = []

                                            if "<TMeanLine" in section[line_number4 - 1]:
                                                index = int(re.search("Index=\"(.+?)\"", section[line_number4 - 1]).group(1)) + 1
                                                value = float(re.search(">(.*)</", line4).group(1))
                                                marker = "{" + formatted_component + "_" + variable + "_MeanLine" + str(index) + "}"

                                                data[line_number2 + line_number4] = data[line_number2 + line_number4].replace(str(value), marker)
                                                master[formatted_component][variable]['value'] = value
                                                master[formatted_component][variable]['marker'] = marker

                                            elif var_type == "Array1":
                                                for line_number5, line5 in enumerate(section):
                                                    if "</" + variable + ">" in line5:
                                                        for line_number6, line6 in enumerate(section[(line_number4 + 1):line_number5]):
                                                            try:
                                                                index = line_number6 + 1
                                                                value = float(re.search(">(.*)</", line6).group(1))
                                                                marker = "{" + formatted_component + "_" + variable + "_MeanLine" + str(index) + "}"
                                                                values.append(value)
                                                                markers.append(marker)
                                                            except AttributeError:
                                                                next

                                                            data[line_number2 + line_number4 + 1 + line_number6] = data[line_number2 + line_number4 + 1 + line_number6].replace(str(value), marker)
                                                        
                                                        master[formatted_component][variable]['value'] = values
                                                        master[formatted_component][variable]['marker'] = markers
                                            
                                            elif var_type == "Vector2":
                                                for line_number5, line5 in enumerate(section):
                                                    if "</" + variable + ">" in line5:
                                                        for line_number6, line6 in enumerate(section[(line_number4 + 1):line_number5]):
                                                            try:
                                                                coordinate = line6.split(" ")[0].strip()[1:]
                                                                value = float(re.search(">(.*)</", line6).group(1))
                                                                marker = "{" + formatted_component + "_" + variable + "_" + coordinate + "}"
                                                                values.append(value)
                                                                markers.append(marker)
                                                            except AttributeError:
                                                                next

                                                            data[line_number2 + line_number4 + 1 + line_number6] = data[line_number2 + line_number4 + 1 + line_number6].replace(str(value), marker)
                                                        
                                                        master[formatted_component][variable]['value'] = values
                                                        master[formatted_component][variable]['marker'] = markers

                                            else:
                                                try:
                                                    if var_type == "Integer":
                                                        value = int(re.search(">(.*)</", line4).group(1))
                                                    else: 
                                                        value = float(re.search(">(.*)</", line4).group(1))
                                                    
                                                    marker = "{" + formatted_component + "_" + variable + "}"
                                                except AttributeError:
                                                    next

                                                data[line_number2 + line_number4] = data[line_number2 + line_number4].replace(str(value), marker)
                                                
                                                master[formatted_component][variable]['value'] = value
                                                master[formatted_component][variable]['marker'] = marker

        outfile.writelines(data)

    simple = {}

    for formatted_component in master.keys():
        for variable in master[formatted_component].keys():
            marker = master[formatted_component][variable].get('marker')
            unit = master[formatted_component][variable].get('unit')
            if type(marker) == str:
                value = master[formatted_component][variable].get('value')
                simple[marker] = (value, unit)
            if type(marker) == list:
                for index, item in enumerate(marker):
                    value = master[formatted_component][variable].get('value')[index]
                    simple[marker[index]] = (value, unit)

    return master, simple


def csv_to_np(simple, csv_file):

    header = ["Design#"] + [marker[1:-1] for marker in simple.keys()]

    first_row = [1] 
    units_row = ['-']
    
    for (original, unit) in simple.values():
        if unit == 'rad':
            first_row.append(str(round(degrees(original), 3)))
            units_row.append('deg')
        elif unit == None:
            first_row.append(str(original))
            units_row.append('-')
        else:
            first_row.append(str(original))
            units_row.append(unit)

    if not os.path.exists(csv_file):
        with open(csv_file, "w", newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow((header))
            writer.writerow((units_row))
            writer.writerow((first_row))
            csvfile.close()

        pause = input("Fill the CSV file with the design parameters. Once complete, press the <ENTER> key to continue.")
    
    values_array = (np.genfromtxt(csv_file, dtype=str, delimiter=',', skip_header=2).T)[1:]

    return values_array


def build_designs(project_name, solver_type, template_file, values_array, simple):

    designs = []

    for design_number, row in enumerate(values_array.T, start=1):

        design_file = project_name + "_" + "Design" + str(design_number) + "_" + solver_type + ".cft-batch"

        with open(template_file, 'r') as infile, open(design_file, 'w') as outfile:
            data = infile.readlines()

            for value_number, (marker, (original, unit)) in enumerate(simple.items()):
                for line_number, line in enumerate(data):        
                    if marker in line:
                        if unit == 'rad':
                            data[line_number] = line.replace(marker, str(radians(float(row[value_number]))))
                        else:
                            data[line_number] = line.replace(marker, row[value_number])

                    if "InputFile=" in line:
                        old_InputFile = re.search("InputFile=\"(.*)\"", line).group(1)
                        new_InputFile = ".\\" + project_name + "_" + solver_type + ".cft"
                        data[line_number] = line.replace(old_InputFile, new_InputFile)

                    if "<WorkingDir>" in line:
                        old_WorkingDir = re.search("<WorkingDir>(.*)</WorkingDir>", line).group(1)
                        new_WorkingDir = ".\\"
                        data[line_number] = line.replace(old_WorkingDir, new_WorkingDir)
                            
                    if "<BaseFileName>" in line:
                        old_BaseFileName = re.search("<BaseFileName>(.*)</BaseFileName>", line).group(1)
                        data[line_number] = line.replace(old_BaseFileName, design_file.replace(".cft-batch", ""))
                        
                    if "<OutputFile>" in line:
                        old_OutputFile = re.search("<OutputFile>(.*)</OutputFile>", line).group(1)
                        data[line_number] = line.replace(old_OutputFile, design_file.replace(".cft-batch", ".cft"))

            outfile.writelines(data)

        designs.append(design_file)

    return designs


def run_design_variation(designs):

    spro_files = []

    for design in designs:

        spro_file = design.replace(".cft-batch", ".spro")
        spro_files.append(spro_file)

        if not os.path.exists(design.replace(".cft-batch", ".log")):

            cfturbo_command = "\"C:\Program Files\CFturbo 2021.2.2\CFturbo.exe\" -batch \"" + design + "\"\n"
            print("\n" + cfturbo_command + "\n")
            subprocess.run(cfturbo_command)

    return spro_files

def run_performance_map(run_performance_map_bool, spro_files, CV_stage_components, rpm_type, rpm_values, flowrate_type, flowrate_values):

    spro_dicts = []

    solver_index = 0
    solver_switch = False

    for spro_file in spro_files:
        if not os.path.exists(spro_file.replace(".spro", ".sgrd")):
            with open("simerics.bat", "w") as batch:
                batch.truncate(0)
                simerics_command = "\"C:\Program Files\Simerics\SimericsMP.exe\" \"" + spro_file + "\" -saveAs \"" + spro_file.replace(".spro", "") + "\"\n"
                batch.write(simerics_command)

                batch.close()

            subprocess.call(os.path.abspath("simerics.bat"))

    for spro_file in spro_files:

        modify_spro(spro_file, CV_stage_components)

        with open(spro_file, 'r') as infile:
            data = infile.readlines()
            for line_number, line in enumerate(data):
                if "vflow_out = " in line:
                    vflow_out_design = float(line.split("=")[1].strip())
                if "#Angular velocity" in line:
                    omega_design = float(data[line_number + 1].split("=")[1].strip())
                    break

            infile.close()

        if run_performance_map_bool.lower() == "true":
            if rpm_type.lower() == "relative":
                omega_list = [float(rpm_value)*omega_design for rpm_value in rpm_values]
                rpm_list = [round(omega_value*(30/pi)) for omega_value in omega_list]
            elif rpm_type.lower() == "absolute":
                rpm_list = [round(float(rpm_value)) for rpm_value in rpm_values]
                omega_list = [rpm_value/(30/pi) for rpm_value in rpm_list]
            else:
                print("Please choose either relative or absolute for rpm_type.")
                exit()

            if flowrate_type.lower() == "relative":
                flowrate_list = [round(float(flowrate_value)*vflow_out_design, 5) for flowrate_value in flowrate_values]
            elif flowrate_type.lower() == "absolute":
                flowrate_list = [float(flowrate_value) for flowrate_value in flowrate_values]
            else:
                print("Please choose either relative or absolute for flowrate_type.")
                exit()
        else:
            omega_list = [omega_design]
            rpm_list = [round(omega_design*(30/pi))]
            flowrate_list = [vflow_out_design]

        if "steady" in spro_file:
            solver_type = "steady"
        elif "transient" in spro_file and solver_switch == False:
            solver_type = "transient"
            solver_index = 0
            solver_switch = True
        elif "transient" in spro_file and solver_switch == True:
            solver_type = "transient"

        for index, omega in enumerate(omega_list):
            for flowrate in flowrate_list:
                if run_performance_map_bool.lower() == "true":
                    new_spro_file = spro_file.split(".")[0] + "_" + str(rpm_list[index]) + "rpm_" + str(flowrate).replace(".", "-") + "m3s.spro"
                else:
                    new_spro_file = spro_file

                spro_dict = {
                    'file_name': new_spro_file,
                    'solver_type': solver_type,
                    'solver_index': solver_index,
                    'omega': omega,
                    'rpm': rpm_list[index],
                    'vflow_out': flowrate
                }
                
                if not os.path.exists(new_spro_file):
                    with open(spro_file, 'r') as infile, open(new_spro_file, 'w') as outfile:
                        data = infile.readlines()
                        for line_number, line in enumerate(data):
                            if "vflow_out = " in line:
                                outfile.write("\t\t" + "vflow_out = " + str(flowrate) + "\n") 
                            elif "#Angular velocity" in line:
                                impeller_number = re.search("Omega(\d) = ", data[line_number + 1]).group(1)
                                data[line_number + 1] = ""
                                outfile.write(line + "\t\t" + "Omega" + impeller_number + " = " + str(omega) + "\n")    
                            else:
                                outfile.write(line)
                
                spro_dicts.append(spro_dict)

                solver_index = solver_index + 1

    return spro_dicts

def post_process(project_name, spro_dict, steady_avg_window, transient_avg_window):

    integrals_file = spro_dict.get('file_name').replace(".spro", "_integrals.txt")

    units_dict, desc_dict = get_Dicts(spro_dict.get("file_name"))

    if spro_dict.get('solver_type').lower() == "steady":
        avg_window = int(steady_avg_window)
    elif spro_dict.get('solver_type').lower() == "transient":
        avg_window = int(transient_avg_window)

    result_dict = {}

    with open(integrals_file, 'r') as infile:
        result_List = list(infile)                                                                  
        del result_List[1:-avg_window]                                  
        reader = csv.DictReader(result_List, delimiter="\t")
        for row in reader:
            for key, value in row.items():
                if 'userdef.' in key:
                    if key in result_dict:
                        try:                                                           
                            result_dict[key[8:]] += float(value)
                        except ValueError:
                            print("NaN for " + key + " in " + spro_dict.get('file_name'))
                            continue
                    else:
                        try:
                            result_dict[key[8:]] = float(value)
                        except ValueError:
                            print("NaN for " + key[8:] + " in " + spro_dict.get('file_name'))
                            continue

        infile.close()

    result_dict['rpm'] = spro_dict.get('rpm')
    result_dict['omega'] = spro_dict.get('omega')
    result_dict['vflow_out'] = spro_dict.get('vflow_out')

    units_dict['rpm'] = '[rev/min]'
    units_dict['omega'] = '[rad/s]'
    units_dict['vflow_out'] = '[m3/s]'

    desc_dict['rpm'] = 'Revolutions per minute'
    desc_dict['omega'] = 'Angular velocity'
    desc_dict['vflow_out'] = 'Outlet volumetric flux'

    stage_keys = []

    for key in units_dict.keys():
        if "stage" in key:
            stage_keys.append(key)

    stage_keys = sorted(stage_keys, key=lambda x:(x[-1], x))

    order = ['rpm', 'omega', 'vflow_out', 'DPtt', 'Eff_tt'] + stage_keys

    for key, value in desc_dict.items():
        if "imp" in value and "delta p" in value:
            order.append(key)
            order.append("Eff_tt_" + key[-1] + "_i")
            order.append("PC" + key[-1])
            order.append("Torque" + key[-1])
    
    for key, value in desc_dict.items():
        if "power" in value and key not in order:
            order.append(key)
        elif "torque" in value and key not in order:
            order.append(key)

    for key in result_dict.keys():
        if key not in order:
            order.append(key)

    result_dict = {k: result_dict[k] for k in order}

    with open (project_name + '_results_' + spro_dict.get("solver_type") + '.csv', 'a+', newline='') as outfile:                             
        writer = csv.DictWriter(outfile, fieldnames=result_dict.keys(), delimiter=",")             
        if spro_dict.get("solver_index") == 0:                                                        
            outfile.truncate(0)
            writer.writeheader()
            writer.writerow(desc_dict)
            writer.writerow(units_dict)                                                                    
        writer.writerow(result_dict)

    return 0


def run_simerics(project_name, spro_dicts, steady_avg_window, transient_avg_window):

    spro_files = [spro_dict.get('file_name').strip() for spro_dict in spro_dicts]  

    for index, spro_file in enumerate(spro_files):
        if not os.path.exists(spro_file.replace(".spro", ".sres")):
            with open("simerics.bat", "w") as batch:
                batch.truncate(0)
                if "steady" in spro_file:
                    simerics_command = "\"C:\Program Files\Simerics\SimericsMP.exe\" -run \"" + spro_file + "\""
                    batch.write(simerics_command)
            
                elif "transient" in spro_file:
                    simerics_command = "\"C:\Program Files\Simerics\SimericsMP.exe\" -run \"" + spro_file + "\" \"" + spro_file.replace("transient", "steady").replace(".spro", ".sres") + "\"\n"
                    batch.write(simerics_command)

                batch.close()

            subprocess.call(os.path.abspath("simerics.bat"))
        
        post_process(project_name, spro_dicts[index], steady_avg_window, transient_avg_window)

    return 0


def combine_csv(project_name):

    parent_path = os.getcwd()
    csv_files = []

    for file in os.listdir(parent_path):
        if 'results' in file and '.csv' in file:
            csv_files.append(file)

    writer = pd.ExcelWriter(project_name + '_results.xlsx', engine='xlsxwriter', engine_kwargs={'options': {'strings_to_numbers': True}})
    for csv in csv_files:
        solver_type = csv.split(".")[0].split("_")[-1]
        df = pd.read_csv(csv)
        df.to_excel(writer, sheet_name=solver_type, index=False)
    writer.save()

    return 0

def main():

    def Get_ConfigValue(ConfigSection, ConfigKey):                                                      
        ConfigValue = CFconfig[ConfigSection][ConfigKey]
        return ConfigValue

    CFconfig = configparser.ConfigParser()                                                             
    CFconfig.read("master.cftconf")

    project_name = Get_ConfigValue("Project", "project_name")
    run_design_variation_bool = Get_ConfigValue("DesignVariation", "run_design_variation_bool")
    run_simerics_bool = Get_ConfigValue("Simerics", "run_simerics_bool")
    steady_avg_window = Get_ConfigValue("steady", "avg_window")
    run_transient_bool = Get_ConfigValue("transient", "run_transient_bool")
    transient_avg_window = Get_ConfigValue("transient", "avg_window")
    run_performance_map_bool = Get_ConfigValue("PerformanceMap", "run_performance_map_bool")
    rpm_type = Get_ConfigValue("PerformanceMap", "rpm_type")
    rpm_values = Get_ConfigValue("PerformanceMap", "rpm_values").split(" ") 
    flowrate_type = Get_ConfigValue("PerformanceMap", "flowrate_type")
    flowrate_values = Get_ConfigValue("PerformanceMap", "flowrate_values").split(" ") 

    if run_design_variation_bool.lower() == "true":
        master, simple = build_template(project_name + "_steady.cft-batch", "template_steady.cft-batch")
        values_array = csv_to_np(simple, project_name + "_design_parameters.csv")
        designs = build_designs(project_name, "steady", "template_steady.cft-batch", values_array, simple)
        spro_files = run_design_variation(designs)

        if run_transient_bool.lower() == "true":
            master, simple = build_template(project_name + "_transient.cft-batch", "template_transient.cft-batch")
            values_array = csv_to_np(simple, project_name + "_design_parameters.csv")
            designs = build_designs(project_name, "transient", "template_transient.cft-batch", values_array, simple)
            spro_files = spro_files + run_design_variation(designs)

    else:
        spro_files = [project_name + "_steady.spro"]

        if run_transient_bool.lower() == "true":
            spro_files = spro_files + [project_name + "_transient.spro"]

    CV_stage_components = get_stage_components(spro_files[0])

    if run_simerics_bool.lower() == "true":
        spro_dicts = run_performance_map(run_performance_map_bool, spro_files, CV_stage_components, rpm_type, rpm_values, flowrate_type, flowrate_values)
        run_simerics(project_name, spro_dicts, steady_avg_window, transient_avg_window)
        combine_csv(project_name)

main()