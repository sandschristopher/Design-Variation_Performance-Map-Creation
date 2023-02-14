from re import search
from itertools import chain
import inflect

def get_stage_components(spro_file):

    p = inflect.engine()

    # Gets volumes:
    volumes = []
    with open(spro_file, 'r') as infile:
        data = infile.readlines()
        for line in data:
            if "vc volume=" in line:
                volumes.append(line.split("\"")[1])

    volumes =  list(dict.fromkeys(volumes)) 

    CV_num = int(input("\nThe export from CFturbo to SimericsMP automatically creates expressions to calculate the total pressure difference and total efficiency of the entire device (inlet of first component to outlet of the final component) by default, but it might be pertinent to analyze a subsect control volume within the entire device.\n\nHow many subsect control volumes would you like to analyze: "))

    CV_stage_components = []

    if CV_num != 0:
        for CV_index in range(CV_num):
            for volume_index, volume in enumerate(volumes, start=1):
                print("\n" + str(volume_index) + ": " + volume)

            stage_components = []
            stage_components.append(int(input("\nEnter the number associated with the initial component of the " + str(p.ordinal(CV_index + 1)) + " CV: ")))
            stage_components.append(int(input("\nEnter the number associated with the final component of the " + str(p.ordinal(CV_index + 1)) + " CV: ")))
            CV_stage_components.append(stage_components)

        return CV_stage_components
    else:
        return 0

def modify_spro(spro_file, CV_stage_components):

    # Gets patch names for each componenet:
    patches = []
    with open(spro_file, 'r') as infile:
        data = infile.readlines()
        for line_number, line in enumerate(data):
            if "<mgi name=" in line:
                MGI_tuple = (data[line_number + 1].split("\"")[1],  data[line_number + 2].split("\"")[1])
                patches.append(MGI_tuple)
        
        for line_number, line in enumerate(data):
            if "plot.DPtt = " in line:
                patches.insert(0, line.split("\"")[3])
                patches.append(line.split("\"")[1])

    # Gets the mismatched grid interface names:
    MGIs = []
    with open(spro_file, 'r') as infile:
        data = infile.readlines()
        for line_number, line in enumerate(data):
            if "<bc patch=\"MGI" in line:
                MGIs.append(line.strip().split("\"")[1])

    # Gets the interface names for each control volume:
    CVIs = list(MGIs)
    with open(spro_file, 'r') as infile:
        for line in infile.readlines():
            if "plot.DPtt = " in line:
                final = line.split("\"")[3]
                initial = line.split("\"")[1]
    
    if "Inflow" in final:
        CVIs.insert(0, final)
        CVIs.append(initial)
    else:
        CVIs.insert(0, initial)
        CVIs.append(final)

    # Gets name/number associated with impellers:
    impellers = []
    with open(spro_file, 'r') as infile:
        data = infile.readlines()
        for line_number, line in enumerate(data):
            if "#plot.PC" in line and "imp" in line or "#plot.PC" in line and "Imp" in line:
                impeller_number = search("#plot.PC(\d)", line).group(1)
                impeller_name = data[line_number - 1].split("\"")[1].split("-")[0]
                impellers.append((impeller_name, impeller_number))

    # Gets the indentation of each expression:
    with open(spro_file, 'r') as infile:
        for line in infile.readlines():
            if "#Outlet volumetric flux [m3/s]" in line or "#Mass flow [kg/s]" in line:
                indent = line.split("#")[0]
                break

    # Ensures consistent .sgrd file:
    with open(spro_file, 'r') as infile:
        data = infile.readlines()
        for line_number, line in enumerate(data):
            if ".sgrd" in line:
                data[line_number] = line.replace("transient", "steady")
                break
    
    # Gets name of leakage interface:
        with open(spro_file, 'r') as infile:
            for line in infile.readlines():
                if "OutletInterface" in line:
                    leakage_interface = line.split("\"")[1].strip()
                else:
                    leakage_interface = 0

    with open(spro_file, 'w') as outfile:
        data = "".join(data)
        outfile.write(data)

    # Adds new, nonduplicate expression to .spro file:
    
    def insert_line(addition):

        with open(spro_file, 'r') as infile:
            data = infile.readlines()
            for line_number, line in enumerate(data):
                if "<expressions>" in line:
                    domain_start = line_number + 1
                if "</expressions>" in line:
                    domain_end = line_number

        exists_already = False

        with open(spro_file, 'r') as infile:
            data = infile.readlines()
            for line_number, line in enumerate(data[domain_start:domain_end]):
                if "=" in line:
                    if addition.split("\n")[1].split("=")[1].strip() == line.split("=")[1].strip():
                        exists_already = True
                    
        if exists_already == False:
            with open(spro_file, 'r') as infile:
                data = infile.readlines()
                for line_number, line in enumerate(data):
                    if "</expressions>" in line:
                        data.insert(line_number, "\n" + addition + "\n")
                        break

            with open(spro_file, 'w') as outfile:
                data = "".join(data)
                outfile.write(data)

    insert_line(indent + "#head [m]" + "\n" + indent + "plot.H = plot.DPtt/rho/9.81 \n" + indent + "#plot.H:head [m]")

    if CV_stage_components != 0:
        for CV_index, stage_components in enumerate(CV_stage_components, start=1):

            stage_patches = list(chain(*patches[(stage_components[0] - 1):(stage_components[-1] + 1)]))

            stage_power_components = []

            for patch in stage_patches[1:-1]:
                for impeller in impellers:
                    if impeller[0] in patch:
                        stage_power_components.append("plot.PC" + impeller[1])

            stage_power_components = list(set(stage_power_components))
            
            if len(stage_power_components) == 0:
                stage_power = False
            elif len(stage_power_components) == 1:
                stage_power = stage_power_components[0]
            else:
                stage_power = " + ".join(stage_power_components)

            insert_line(indent + "#delta p (t-t), stage" + str(CV_index) + " [Pa]" + "\n" + indent + "plot.DPtt_stage" + str(CV_index) + " = flow.mpt@\"" \
                + CVIs[stage_components[-1]] + "\"-flow.mpt@\"" + CVIs[(stage_components[0] - 1)] + "\"\n" + indent + "#plot.DPtt_stage" + str(CV_index) + ":delta p (t-t), stage" + str(CV_index) + " [Pa]")
            
            if stage_power != False:
                insert_line(indent + "#efficiency (t-t), stage" + str(CV_index) + " [-]" + "\n" + indent + "plot.Eff_tt_stage" + str(CV_index) + " = flow.q@\"" \
                    + CVIs[stage_components[-1]] + "\"*plot.DPtt_stage" + str(CV_index) + "/rho/(" + stage_power + ")\n" + indent + "#plot.Eff_tt_stage" + str(CV_index) + ":efficiency (t-t), stage" + str(CV_index) + " [-]")

    for i in range(1, len(CVIs)):
        insert_line(indent + "#delta p (t-t), CV" + str(i) + " [Pa]" + "\n" + indent + "plot.DPttCV" + str(i) + " = flow.mpt@\"" \
            + CVIs[i] + "\"-flow.mpt@\"" + CVIs[i - 1] + "\"\n" + indent + "#plot.DPttCV" + str(i) + ":delta p (t-t), CV" \
            + str(i) + " [Pa]")

    for i, CVI in enumerate(CVIs):
        insert_line(indent + "#pressure (t), CVI" + str(i) + " [Pa]" + "\n" + indent + "plot.PtCVI" + str(i) + " = flow.mpt@\"" \
            + CVI + "\"\n" + indent + "#plot.PtCVI" + str(i) + ":pressure (t), CVI" + str(i) + " [Pa]")

        insert_line(indent + "#pressure (s), CVI" + str(i) + " [Pa]" + "\n" + indent + "plot.PsCVI" + str(i) + " = flow.p@\"" \
            + CVI + "\"\n" + indent + "#plot.PsCVI" + str(i) + ":pressure (s), CVI" + str(i) + " [Pa]")

    if leakage_interface != 0:

        insert_line(indent + "#mass flow, shroud leakage, relative [-]" + "\n" + indent + "plot.mShroudLeakageRel = (flow.q@\"" \
            + leakage_interface + "\" - flow.q@\"" + CVIs[-1] + "\")/(flow.q@\"" + CVIs[-1] + "\")" + "\n" + indent + "#plot.mShroudLeakageRel:mass flow, shroud leakage, relative [-]")

        insert_line(indent + "#mass flow, shroud leakage, absolute [kg/s]" + "\n" + indent + "plot.mShroudLeakageAbs = flow.q@\"" \
            + leakage_interface + "\" - flow.q@\"" + CVIs[-1] + "\"\n" + indent + "#plot.mShroudLeakageAbs:mass flow, shroud leakage, absolute [kg/s]")

        insert_line(indent + "#volumetric flow, shroud leakage, relative [-]" + "\n" + indent + "plot.vShroudLeakageRel = (flow.qv@\"" \
            + leakage_interface + "\" - flow.qv@\"" + CVIs[-1] + "\")/(flow.qv@\"" + CVIs[-1] + "\")" + "\n" + indent + "#plot.vShroudLeakageRel:volumetric flow, shroud leakage, relative [-]")

        insert_line(indent + "#volumetric flow, shroud leakage, absolute [m3/s]" + "\n" + indent + "plot.vShroudLeakageAbs = flow.qv@\"" \
            + leakage_interface + "\" - flow.qv@\"" + CVIs[-1] + "\"\n" + indent + "#plot.vShroudLeakageAbs:volumetric flow, shroud leakage, absolute [m3/s]")

        insert_line(indent + "#efficiency (t-t), imp1 passage [-]" + "\n" + indent + "plot.Eff_tt_" + impeller_number + "Passage = flow.qv@\"" \
            + leakage_interface + "\"*plot.DPtt" + impeller_number + "Passage/plot.PC" + impeller_number + "Passage" + "\n" + indent + "#plot.Eff_tt_" + impeller_number + "Passage:efficiency (t-t), imp1 passage [-]")

        insert_line(indent + "#power, imp1 passage [W]" + "\n" + indent + "plot.PC" + impeller_number + "Passage = abs(flow.power@\"" + impeller_name + "-Hub\"" \
            + " + flow.power@\"" + impeller_name + "-Shroud\" + flow.power@\"" + impeller_name + "-BladeSides\" + flow.power@\"" + impeller_name + "-BladeLE\" + flow.power@\"" + impeller_name + "-BladeTE\")" \
            + "\n" + indent + "#plot.PC" + impeller_number + "Passage:power, imp1 passage [W]")

        insert_line(indent + "#delta p (t-t), imp1 passage [Pa]" + "\n" + indent + "plot.DPtt2Passage = flow.mpt@\"" \
            + leakage_interface + "\" - flow.mpt@\"" + MGIs[0] + "\"\n" + indent + "#plot.DPtt2Passage:delta p (t-t), imp1 passage [Pa]")

        insert_line(indent + "#volumetric flow, OutletInterface, absolute [m3/s]" + "\n" + indent + "plot.vOutletInterface = flow.qv@\"" \
            + leakage_interface + "\"\n" + indent + "#plot.vOutletInterface:#volumetric flow, OutletInterface, absolute [m3/s]")

        insert_line(indent + "#volumetric flow, OutletExtension, absolute [m3/s]" + "\n" + indent + "plot.vOutletExtension = flow.qv@\"" \
            + CVIs[-1] + "\"\n" + indent + "#plot.vOutletExtension:#volumetric flow, OutletExtension, absolute [m3/s]")

    return 0

def get_Dicts(spro_file):

    isMassFlow = False

    with open(spro_file, "r") as infile:
        units_dict = {}
        desc_dict = {}
        data = infile.readlines()
        for line in data:
            if "#plot." in line:
                key = line.split(":")[0].split(".")[1].strip()
                units_dict[key] = line.split(" ")[-1].strip() 
                desc_dict[key] = line.split("[")[0].split(":")[1].strip()

    if "Outlet volumetric flux" in desc_dict.items():
        isMassFlow = False
    else:
        isMassFlow = True

    return units_dict, desc_dict, isMassFlow

def get_design_point(spro_file):

    isMassFlow = False

    with open(spro_file, 'r') as infile:
        data = infile.readlines()
        for line_number, line in enumerate(data):
            if "vflow_out = " in line:
                vflow_out_design_value = float(line.split("=")[1].strip())
            elif "mflow = " in line:
                isMassFlow = True
                vflow_out_design_value = float(line.split("=")[1].strip())

            if "#Angular velocity" in line and "[" in line:
                omega_design_value = float(data[line_number + 1].split("=")[1].strip())
                omega_design_units = line.split("[")[-1].strip()[:-1]
                break

            if "#Angular velocity" in line and "(" in line:
                omega_design_value = float(data[line_number + 1].split("=")[1].strip())
                omega_design_units = line.split("(")[-1].strip()[:-1]
                break
        
        infile.close()

    return [(vflow_out_design_value), (omega_design_value, omega_design_units)], isMassFlow
