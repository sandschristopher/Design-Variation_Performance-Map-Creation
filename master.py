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

    with open(cft_batch_file, 'r') as infile:
        data = infile.readlines()
        for line_number, line in enumerate(data):
            if "<ExportComponents " in line:
                num_components = int(line.split("\"")[1])
                for _ in range(1, num_components + 1):
                    for component_line in data[line_number + 1:line_number + num_components + 1]:
                        component = re.search("Caption=\"(.+?)\"", component_line).group(1)
                        index = re.search("Index=\"(.+?)\"", component_line).group(1)
                        if component not in master:
                            master[component] = {}
                            master[component]['index'] = index

    secondary_flow_path_sections = []
    mean_line_sections = []
    mer_data_sections = []

    with open(cft_batch_file, 'r') as infile, open(template_file, 'w') as outfile:
        data = infile.readlines()
        for component in master.keys():
            for line_number1, line1 in enumerate(data):
                if "Name=\"" + component in line1 and "CFturboDesign" in line1:
                    for line_number2, line2 in enumerate(data[line_number1:]):
                        section_end = "</" + line1.split(" ")[0].strip()[1:]
                        if section_end in line2:
                            section = data[line_number1:line_number1 + line_number2]
                            for line_number3, line3 in enumerate(section):

                                if "TMer2ndaryFlowPath" in line3:
                                    for line_number4, line4 in enumerate(data[(line_number1 + line_number3):]):
                                        if "</TMer2ndaryFlowPath>" in line4:
                                            secondary_flow_path_section = data[(line_number1 + line_number3):(line_number1 + line_number3 + line_number4)]
                                            break

                                    secondary_flow_path_sections.append(secondary_flow_path_section)

                                    for line_number5, line5 in enumerate(secondary_flow_path_section):
                                        if "<Wire" in line5:
                                            try:
                                                wire_name = re.search("Name=\"(.+?)\"", line5).group(1)
                                            except AttributeError:
                                                next
                                        
                                            for line_number6, line6 in enumerate(data[(line_number1 + line_number3 + line_number5):]):
                                                if "</Wire>" in line6:
                                                    wire_section = data[(line_number1 + line_number3 + line_number5):(line_number1 + line_number3 + line_number5 + line_number6)]
                                                    break

                                            for line_number7, line7 in enumerate(wire_section):
                                                
                                                if "<Connectors " in line7:
                                
                                                    for line_number8, line8 in enumerate(data[(line_number1 + line_number3 + line_number5 + line_number7):]):
                                                        
                                                        if "</Connectors>" in line8:
                                                            connectors_section = data[(line_number1 + line_number3 + line_number5 + line_number7):(line_number1 + line_number3 + line_number5 + line_number7 + line_number8)]
                                                            break

                                                    for line_number9, line9 in enumerate(connectors_section):
                                                        
                                                        if "<ConnectorPoint " in line9:
                                                            try:
                                                                point_index = re.search("Index=\"(.+?)\"", line9).group(1)
                                                            except AttributeError:
                                                                next
                                                            
                                                            for line_number10, line10 in enumerate(data[(line_number1 + line_number3 + line_number5 + line_number7 + line_number9):]):
                                                                
                                                                if "</ConnectorPoint>" in line10:
                                                                    point_section = data[(line_number1 + line_number3 + line_number5 + line_number7 + line_number9):(line_number1 + line_number3 + line_number5 + line_number7 + line_number9 + line_number10)]
                                                                    break

                                                            for line_number11, line11 in enumerate(point_section):
                                                                if "Caption=" in line11:
                                                                    variable = line11.split(" ")[0].strip()[1:]
                                                                    master[component][variable + wire_name + variable + point_index] = {}
                                                                    if "</" + variable + ">" in line11:
                                                                        try:
                                                                            var_type = re.search("Type=\"(.+?)\"", line11).group(1)
                                                                            master[component][variable + wire_name + variable + point_index]['var_type'] = var_type
                                                                        except AttributeError:
                                                                            next

                                                                        try:
                                                                            count = re.search("Count=\"(.+?)\"", line11).group(1)
                                                                            master[component][variable + wire_name + variable + point_index]['count'] = count
                                                                        except AttributeError:
                                                                            next

                                                                        try:
                                                                            caption = re.search("Caption=\"(.+?)\"", line11).group(1)
                                                                            master[component][variable + wire_name + variable + point_index]['caption'] = caption
                                                                        except AttributeError:
                                                                            next

                                                                        try:
                                                                            desc = re.search("Desc=\"(.+?)\"", line11).group(1)
                                                                            master[component][variable + wire_name + variable + point_index]['desc'] = desc
                                                                        except AttributeError:
                                                                            next
                                                                        
                                                                        try:
                                                                            unit = re.search("Unit=\"(.+?)\"", line11).group(1)
                                                                            master[component][variable + wire_name + variable + point_index]['unit'] = unit
                                                                        except AttributeError:
                                                                            next

                                                                        value = ">" + re.search(">(.*)</", line11).group(1) + "<"
                                                                        marker = ">{" + component + "_" + wire_name + "_" + variable + "_" + point_index + "_" + caption.replace(" ", '-') + "}<"
                                                                        data[line_number1 + line_number3 + line_number5 + line_number7 + line_number9 + line_number11] = data[line_number1 + line_number3 + line_number5 + line_number7 + line_number9 + line_number11].replace(value, marker)
                                                                    
                                                                        master[component][variable + wire_name + variable + point_index]['value'] = value
                                                                        master[component][variable + wire_name + variable + point_index]['marker'] = marker

                                                elif "<Curve " in line7:
                                                    try:
                                                        curve_index = re.search("Index=\"(.+?)\"", line7).group(1)
                                                    except AttributeError:
                                                        next
                                                    
                                                    for line_number8, line8 in enumerate(data[(line_number1 + line_number3 + line_number5 + line_number7):]):
                                                        if "</Curve>" in line8:
                                                            curve_section = data[(line_number1 + line_number3 + line_number5 + line_number7):(line_number1 + line_number3 + line_number5 + line_number7 + line_number8)]
                                                            break

                                                    for line_number9, line9 in enumerate(curve_section):
                                                        if "<ControlPoint" in line9:
                                                            try:
                                                                point_index = re.search("Index=\"(.+?)\"", line9).group(1)
                                                            except AttributeError:
                                                                next

                                                            for line_number10, line10 in enumerate(data[(line_number1 + line_number3 + line_number5 + line_number7 + line_number9):]):
                                                                if "</ControlPoint>" in line10:
                                                                    point_section = data[(line_number1 + line_number3 + line_number5 + line_number7 + line_number9):(line_number1 + line_number3 + line_number5 + line_number7 + line_number9 + line_number10)]
                                                                    break

                                                            for line_number11, line11 in enumerate(point_section):
                                                                if "Caption=" in line11:
                                                                    variable = line11.split(" ")[0].strip()[1:]
                                                                    master[component][variable + wire_name + "curve" + curve_index + variable + point_index] = {}
                                                                    if "</" + variable + ">" in line11:
                                                                        try:
                                                                            var_type = re.search("Type=\"(.+?)\"", line11).group(1)
                                                                            master[component][variable + wire_name + "curve" + curve_index + variable + point_index]['var_type'] = var_type
                                                                        except AttributeError:
                                                                            next

                                                                        try:
                                                                            count = re.search("Count=\"(.+?)\"", line11).group(1)
                                                                            master[component][variable + wire_name + "curve" + curve_index + variable + point_index]['count'] = count
                                                                        except AttributeError:
                                                                            next

                                                                        try:
                                                                            caption = re.search("Caption=\"(.+?)\"", line11).group(1)
                                                                            master[component][variable + wire_name + "curve" + curve_index + variable + point_index]['caption'] = caption
                                                                        except AttributeError:
                                                                            next

                                                                        try:
                                                                            desc = re.search("Desc=\"(.+?)\"", line11).group(1)
                                                                            master[component][variable + wire_name + "curve" + curve_index + variable + point_index]['desc'] = desc
                                                                        except AttributeError:
                                                                            next
                                                                        
                                                                        try:
                                                                            unit = re.search("Unit=\"(.+?)\"", line11).group(1)
                                                                            master[component][variable + wire_name + "curve" + curve_index + variable + point_index]['unit'] = unit
                                                                        except AttributeError:
                                                                            next

                                                                        value = ">" + re.search(">(.*)</", line11).group(1) + "<"
                                                                        marker = ">{" + component + "_" + wire_name + "_curve" + curve_index + "_" + variable + "_" + point_index + "_" + caption.replace(" ", '-') + "}<"
                                                                        data[line_number1 + line_number3 + line_number5 + line_number7 + line_number9 + line_number11] = data[line_number1 + line_number3 + line_number5 + line_number7 + line_number9 + line_number11].replace(value, marker)
                                                                    
                                                                        master[component][variable + wire_name + "curve" + curve_index + variable + point_index]['value'] = value
                                                                        master[component][variable + wire_name + "curve" + curve_index + variable + point_index]['marker'] = marker

                                if "<TMeanLine" in line3 and "Index=" in line3:

                                    try:
                                        index = re.search("Index=\"(.+?)\"", line3).group(1)
                                    except AttributeError:
                                        next

                                    for line_number4, line4 in enumerate(data[(line_number1 + line_number3):]):
                                        if "</TMeanLine>" in line4:
                                            mean_line_section = data[(line_number1 + line_number3):(line_number1 + line_number3 + line_number4)]
                                            break

                                    mean_line_sections.append(mean_line_section)

                                    for line_number5, line5 in enumerate(mean_line_section):
                                        if "Caption=" in line5 and "Array" in line5:

                                            markers = []
                                            values = []

                                            variable = line5.split(" ")[0].strip()[1:]
                                            master[component][variable] = {}

                                            try:
                                                var_type = re.search("Type=\"(.+?)\"", line5).group(1)
                                                master[component][variable]['var_type'] = var_type
                                            except AttributeError:
                                                next

                                            try:
                                                count = re.search("Count=\"(.+?)\"", line5).group(1)
                                                master[component][variable]['count'] = count
                                            except AttributeError:
                                                next

                                            try:
                                                caption = re.search("Caption=\"(.+?)\"", line5).group(1)
                                                master[component][variable]['caption'] = caption
                                            except AttributeError:
                                                next

                                            try:
                                                desc = re.search("Desc=\"(.+?)\"", line5).group(1)
                                                master[component][variable]['desc'] = desc
                                            except AttributeError:
                                                next
                                            
                                            try:
                                                unit = re.search("Unit=\"(.+?)\"", line5).group(1)
                                                master[component][variable]['unit'] = unit
                                            except AttributeError:
                                                next

                                            '''

                                            for line_number4, line4 in enumerate(data[(line_number1 + line_number3):]):
                                                if "</" + variable + ">" in line4:
                                                    array_section = data[(line_number1 + line_number3 + 1):(line_number1 + line_number3 + line_number4)]
                                                    break
                                            
                                            '''

                                            for line_number6, line6 in enumerate(mean_line_section):
                                                if "</" + variable + ">" in line6:
                                                    array_section = mean_line_section[line_number5:line_number6]
                                                    break

                                            for index in range(int(count)):
                                                for line_number7, line7 in enumerate(array_section):
                                                    if "Index=\"" + str(index) + "\"" in line7:
                                                        if "Type=\"" + "Vector" in line7:
                                                            for vector_index in range(1, 3):
                                                                vector_variable = data[line_number1 + line_number3 + line_number5 + line_number7 + vector_index].split(" ")[0].strip()[1:]
                                                                value = ">" + re.search(">(.*)</", data[line_number1 + line_number3 + line_number5 + line_number7 + vector_index]).group(1) + "<"
                                                                marker = ">{" + component + "_" + variable + "_" + vector_variable + "_" + str(index) + "}<"
                                                                data[line_number1 + line_number3 + line_number5 + line_number7 + vector_index] = data[line_number1 + line_number3 + line_number5 + line_number7 + vector_index].replace(value, marker)
                                                                values.append(value)
                                                                markers.append(marker)

                                            master[component][variable]['value'] = values
                                            master[component][variable]['marker'] = markers

                                            if "</" + variable + ">" in line5:

                                                try:
                                                    var_type = re.search("Type=\"(.+?)\"", line5).group(1)
                                                    master[component][variable + index]['var_type'] = var_type
                                                except AttributeError:
                                                    next

                                                try:
                                                    count = re.search("Count=\"(.+?)\"", line5).group(1)
                                                    master[component][variable + index]['count'] = count
                                                except AttributeError:
                                                    next

                                                try:
                                                    caption = re.search("Caption=\"(.+?)\"", line5).group(1)
                                                    master[component][variable + index]['caption'] = caption
                                                except AttributeError:
                                                    next

                                                try:
                                                    desc = re.search("Desc=\"(.+?)\"", line5).group(1)
                                                    master[component][variable + index]['desc'] = desc
                                                except AttributeError:
                                                    next
                                                
                                                try:
                                                    unit = re.search("Unit=\"(.+?)\"", line5).group(1)
                                                    master[component][variable + index]['unit'] = unit
                                                except AttributeError:
                                                    next

                                                value = ">" + re.search(">(.*)</", line5).group(1) + "<"
                                                marker = ">{" + component + "_" + variable + "_" + caption.replace(" ", '-') + "_" + index + "}<"
                                                data[line_number1 + line_number3 + line_number5] = data[line_number1 + line_number3 + line_number5].replace(value, marker)
                                            
                                                master[component][variable + index]['value'] = value
                                                master[component][variable + index]['marker'] = marker
                                        
                                        elif "Caption=" in line5:

                                            variable = line5.split(" ")[0].strip()[1:]
                                            master[component][variable + index] = {}
                                            if "</" + variable + ">" in line5:

                                                try:
                                                    var_type = re.search("Type=\"(.+?)\"", line5).group(1)
                                                    master[component][variable + index]['var_type'] = var_type
                                                except AttributeError:
                                                    next

                                                try:
                                                    count = re.search("Count=\"(.+?)\"", line5).group(1)
                                                    master[component][variable + index]['count'] = count
                                                except AttributeError:
                                                    next

                                                try:
                                                    caption = re.search("Caption=\"(.+?)\"", line5).group(1)
                                                    master[component][variable + index]['caption'] = caption
                                                except AttributeError:
                                                    next

                                                try:
                                                    desc = re.search("Desc=\"(.+?)\"", line5).group(1)
                                                    master[component][variable + index]['desc'] = desc
                                                except AttributeError:
                                                    next
                                                
                                                try:
                                                    unit = re.search("Unit=\"(.+?)\"", line5).group(1)
                                                    master[component][variable + index]['unit'] = unit
                                                except AttributeError:
                                                    next

                                                value = ">" + re.search(">(.*)</", line5).group(1) + "<"
                                                marker = ">{" + component + "_" + variable + "_" + caption.replace(" ", '-') + "_" + index + "}<"
                                                data[line_number1 + line_number3 + line_number5] = data[line_number1 + line_number3 + line_number5].replace(value, marker)
                                            
                                                master[component][variable + index]['value'] = value
                                                master[component][variable + index]['marker'] = marker

                                elif "MerEdge" in line3 and "Name" in line3:
                                    try:
                                        name = re.search("Name=\"(.+?)\"", line3).group(1)
                                    except AttributeError:
                                        next
                                    
                                    for line_number4, line4 in enumerate(data[(line_number1 + line_number3):]):
                                        if "</" + "MerEdge>" in line4:
                                            mer_edge_section = data[(line_number1 + line_number3 + 1):(line_number1 + line_number3 + line_number4)]
                                            break

                                    for line_number5, line5 in enumerate(mer_edge_section):
                                        
                                        variable = line5.split(" ")[0].strip()[1:]
                                        master[component][variable + name.replace(" ", "-")] = {}

                                        try:
                                            var_type = re.search("Type=\"(.+?)\"", line5).group(1)
                                            master[component][variable + name.replace(" ", "-")]['var_type'] = var_type
                                        except AttributeError:
                                            next

                                        try:
                                            count = re.search("Count=\"(.+?)\"", line5).group(1)
                                            master[component][variable + name.replace(" ", "-")]['count'] = count
                                        except AttributeError:
                                            next

                                        try:
                                            caption = re.search("Caption=\"(.+?)\"", line5).group(1)
                                            master[component][variable + name.replace(" ", "-")]['caption'] = caption
                                        except AttributeError:
                                            next

                                        try:
                                            desc = re.search("Desc=\"(.+?)\"", line5).group(1)
                                            master[component][variable + name.replace(" ", "-")]['desc'] = desc
                                        except AttributeError:
                                            next
                                        
                                        try:
                                            unit = re.search("Unit=\"(.+?)\"", line5).group(1)
                                            master[component][variable + name.replace(" ", "-")]['unit'] = unit
                                        except AttributeError:
                                            next

                                        try:    

                                            value = ">" + re.search(">(.*)</", line5).group(1) + "<"
                                            marker = ">{" + component + "_" + variable + "_" + caption.replace(" ", '-') + "_" + name.replace(" ", '-') + "}<"
                                            data[line_number1 + line_number3 + line_number5 + 1] = data[line_number1 + line_number3 + line_number5 + 1].replace(value, marker)
                                        except AttributeError:
                                            continue

                                        master[component][variable + name.replace(" ", "-")]['value'] = value
                                        master[component][variable + name.replace(" ", "-")]['marker'] = marker

                                elif "MerData" in line3 and "Name" in line3:

                                    try:
                                        name = re.search("Name=\"(.+?)\"", line3).group(1)
                                    except AttributeError:
                                        next

                                    for line_number4, line4 in enumerate(data[(line_number1 + line_number3):]):
                                        if "</" + "MerData>" in line4:
                                            mer_data_section = data[(line_number1 + line_number3 + 1):(line_number1 + line_number3 + line_number4)]
                                            break

                                    mer_data_sections.append(mer_data_section)

                                    for line_number5, line5 in enumerate(mer_data_section):
                                        if "Vector2" in line5:

                                            markers = []
                                            values = []

                                            variable = line5.split(" ")[0].strip()[1:]
                                            master[component][name.replace(" ", "-") + variable] = {}

                                            try:
                                                var_type = re.search("Type=\"(.+?)\"", line5).group(1)
                                                master[component][name.replace(" ", "-") + variable] ['var_type'] = var_type
                                            except AttributeError:
                                                next

                                            try:
                                                count = re.search("Count=\"(.+?)\"", line5).group(1)
                                                master[component][name.replace(" ", "-") + variable] ['count'] = count
                                            except AttributeError:
                                                next

                                            try:
                                                caption = re.search("Caption=\"(.+?)\"", line5).group(1)
                                                master[component][name.replace(" ", "-") + variable] ['caption'] = caption
                                            except AttributeError:
                                                next

                                            try:
                                                desc = re.search("Desc=\"(.+?)\"", line5).group(1)
                                                master[component][name.replace(" ", "-") + variable]['desc'] = desc
                                            except AttributeError:
                                                next
                                            
                                            try:
                                                unit = re.search("Unit=\"(.+?)\"", line5).group(1)
                                                master[component][name.replace(" ", "-") + variable]['unit'] = unit
                                            except AttributeError:
                                                next

                                            for vector_index in range(1, 3):
                                                vector_variable = data[line_number1 + line_number3 + line_number5 + vector_index + 1].split(" ")[0].strip()[1:]
                                                value = ">" + re.search(">(.*)</", data[line_number1 + line_number3 + line_number5 + vector_index + 1]).group(1) + "<"
                                                marker = ">{" + component + "_" + name.replace(" ", "-") + "_" + variable + "_" + caption.replace(" ", '-') + "_" + vector_variable + "}<"
                                                data[line_number1 + line_number3 + line_number5 + vector_index + 1] = data[line_number1 + line_number3 + line_number5 + vector_index + 1].replace(value, marker)
                                                values.append(value)
                                                markers.append(marker)

                                            master[component][name.replace(" ", "-") + variable]['value'] = values
                                            master[component][name.replace(" ", "-") + variable]['marker'] = markers   
                

                                elif "Caption=" in line3:
                                    if not any(line3 in string for string in mean_line_sections) and not any(line3 in string for string in secondary_flow_path_sections):
                                        variable = line3.split(" ")[0].strip()[1:]

                                        try:
                                            caption = re.search("Caption=\"(.+?)\"", line3).group(1)
                                        except AttributeError:
                                            next

                                        master[component][variable + caption.replace(" ", "-")] = {}

                                        if "</" + variable + ">" in line3:

                                            try:
                                                var_type = re.search("Type=\"(.+?)\"", line3).group(1)
                                                master[component][variable + caption.replace(" ", "-")]['var_type'] = var_type
                                            except AttributeError:
                                                next

                                            try:
                                                count = re.search("Count=\"(.+?)\"", line3).group(1)
                                                master[component][variable + caption.replace(" ", "-")]['count'] = count
                                            except AttributeError:
                                                next

                                            try:
                                                caption = re.search("Caption=\"(.+?)\"", line3).group(1)
                                                master[component][variable + caption.replace(" ", "-")]['caption'] = caption
                                            except AttributeError:
                                                next
                                            

                                            try:
                                                desc = re.search("Desc=\"(.+?)\"", line3).group(1)
                                                master[component][variable + caption.replace(" ", "-")]['desc'] = desc
                                            except AttributeError:
                                                next
                                            
                                            try:
                                                unit = re.search("Unit=\"(.+?)\"", line3).group(1)
                                                master[component][variable + caption.replace(" ", "-")]['unit'] = unit
                                            except AttributeError:
                                                next

                                            value = ">" + re.search(">(.*)</", line3).group(1) + "<"
                                            marker = ">{" + component + "_" + variable + "_" + caption.replace(" ", '-') + "}<"
                                            data[line_number1 + line_number3] = data[line_number1 + line_number3].replace(value, marker)
                                            master[component][variable + caption.replace(" ", "-")]['value'] = value
                                            master[component][variable + caption.replace(" ", "-")]['marker'] = marker   

                                        elif "Array1" in line3:

                                            markers = []
                                            values = []

                                            variable = line3.split(" ")[0].strip()[1:]
                                            master[component][variable] = {}

                                            try:
                                                var_type = re.search("Type=\"(.+?)\"", line3).group(1)
                                                master[component][variable]['var_type'] = var_type
                                            except AttributeError:
                                                next

                                            try:
                                                count = re.search("Count=\"(.+?)\"", line3).group(1)
                                                master[component][variable]['count'] = count
                                            except AttributeError:
                                                next

                                            try:
                                                caption = re.search("Caption=\"(.+?)\"", line3).group(1)
                                                master[component][variable]['caption'] = caption
                                            except AttributeError:
                                                next

                                            try:
                                                desc = re.search("Desc=\"(.+?)\"", line3).group(1)
                                                master[component][variable]['desc'] = desc
                                            except AttributeError:
                                                next
                                            
                                            try:
                                                unit = re.search("Unit=\"(.+?)\"", line3).group(1)
                                                master[component][variable]['unit'] = unit
                                            except AttributeError:
                                                next

                                            for line_number4, line4 in enumerate(data[(line_number1 + line_number3):]):
                                                if "</" + variable + ">" in line4:
                                                    array_section = data[(line_number1 + line_number3 + 1):(line_number1 + line_number3 + line_number4)]
                                                    break

                                            for index in range(int(count)):
                                                for line_number5, line5 in enumerate(array_section):
                                                    if "Index=\"" + str(index) + "\"" in line5:
                                                        if "Type=\"" + "Vector" in line5:
                                                            for vector_index in range(1, 3):
                                                                vector_variable = data[line_number1 + line_number3 + line_number5 + 1 + vector_index].split(" ")[0].strip()[1:]
                                                                value = ">" + re.search(">(.*)</", data[line_number1 + line_number3 + line_number5 + 1 + vector_index]).group(1) + "<"
                                                                marker = ">{" + component + "_" + variable + "_" + vector_variable + "_" + str(index) + "}<"
                                                                data[line_number1 + line_number3 + line_number5 + 1 + vector_index] = data[line_number1 + line_number3 + line_number5 + 1 + vector_index].replace(value, marker)
                                                                values.append(value)
                                                                markers.append(marker)

                                                    
                                                        elif "Type=\"" + "Float" + "\"" in line5:
                                                            value = ">" + re.search(">(.*)</", data[line_number1 + line_number3 + line_number5 + 1]).group(1) + "<"
                                                            marker = ">{" + component + "_" + variable + "_" + caption.replace(" ", '-') + "_" + str(index) + "}<"
                                                            data[line_number1 + line_number3 + line_number5 + 1] = data[line_number1 + line_number3 + line_number5 + 1].replace(value, marker)
                                                            values.append(value)
                                                            markers.append(marker)

                                            master[component][variable]['value'] = values
                                            master[component][variable]['marker'] = markers   

                                        elif "Vector2" in line3:
                                            if not any(line3 in string for string in mer_data_sections):

                                                markers = []
                                                values = []

                                                variable = line3.split(" ")[0].strip()[1:]
                                                master[component][variable] = {}

                                                try:
                                                    var_type = re.search("Type=\"(.+?)\"", line3).group(1)
                                                    master[component][variable]['var_type'] = var_type
                                                except AttributeError:
                                                    next

                                                try:
                                                    count = re.search("Count=\"(.+?)\"", line3).group(1)
                                                    master[component][variable]['count'] = count
                                                except AttributeError:
                                                    next

                                                try:
                                                    caption = re.search("Caption=\"(.+?)\"", line3).group(1)
                                                    master[component][variable]['caption'] = caption
                                                except AttributeError:
                                                    next

                                                try:
                                                    desc = re.search("Desc=\"(.+?)\"", line3).group(1)
                                                    master[component][variable]['desc'] = desc
                                                except AttributeError:
                                                    next
                                                
                                                try:
                                                    unit = re.search("Unit=\"(.+?)\"", line3).group(1)
                                                    master[component][variable]['unit'] = unit
                                                except AttributeError:
                                                    next

                                                for vector_index in range(1, 3):
                                                    vector_variable = data[line_number1 + line_number3 + vector_index].split(" ")[0].strip()[1:]
                                                    value = ">" + re.search(">(.*)</", data[line_number1 + line_number3 + vector_index]).group(1) + "<"
                                                    marker = ">{" + component + "_" + variable + "_" + caption.replace(" ", '-') + "_" + vector_variable + "}<"
                                                    data[line_number1 + line_number3 + vector_index] = data[line_number1 + line_number3 + vector_index].replace(value, marker)
                                                    values.append(value)
                                                    markers.append(marker)

                                                master[component][variable]['value'] = values
                                                master[component][variable]['marker'] = markers   
  
                            break

        outfile.writelines(data)

    simple = {}

    for component in master.keys():
        for variable in master[component].keys():
            if variable != "index":
                marker = master[component][variable].get('marker')
                unit = master[component][variable].get('unit')
                if type(marker) == str:
                    value = master[component][variable].get('value')
                    simple[marker] = (value, unit)
                if type(marker) == list:
                    for _ in range(len(marker)):
                        value = master[component][variable].get('value')[_]
                        simple[marker[_]] = (value, unit)

    return master, simple


def csv_to_np(simple, csv_file, project_name):

    header = ["Design#"] + [marker[2:-2] for marker in simple.keys()]

    first_row = [1] 
    units_row = ['-']
    
    for (original, unit) in simple.values():
        if unit == 'rad':
            first_row.append(str(round(degrees(float(original[1:-1])), 3)))
            units_row.append('deg')
        elif unit == None:
            first_row.append(str(original[1:-1]))
            units_row.append('-')
        else:
            first_row.append(str(original[1:-1]))
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
                            data[line_number] = line.replace(marker[1:-1], str(radians(float(row[value_number]))))
                        else:
                            data[line_number] = line.replace(marker[1:-1], row[value_number])
                            
                    if "<BaseFileName>" in line:
                        old_name = re.search("<BaseFileName>(.*)</BaseFileName>", line).group(1)
                        data[line_number] = line.replace(old_name, design_file.replace(".cft-batch", ""))

                    if "<OutputFile>" in line:
                        old_name = re.search("<OutputFile>(.*)</OutputFile>", line).group(1)
                        data[line_number] = line.replace(old_name, design_file.replace(".cft-batch", ".cft"))

            outfile.writelines(data)

        designs.append(design_file)

    return designs


def run_design_variation(designs, cft_version):

    spro_files = []

    for design in designs:

        spro_file = design.replace(".cft-batch", ".spro")
        spro_files.append(spro_file)

        if not os.path.exists(design.replace(".cft-batch", ".log")):

            cfturbo_command = "\"C:\Program Files\CFturbo " + cft_version + "\CFturbo.exe\" -batch \"" + design + "\"\n"
            print("\n" + cfturbo_command + "\n")
            subprocess.run(cfturbo_command)

    return spro_files

def run_performance_map(run_performance_map_bool, spro_files, CV_stage_components, volumes, rpm_type, rpm_values, flowrate_type, flowrate_values):

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

        modify_spro(spro_file, CV_stage_components, volumes)
        [(flow_out_design_value), (omega_design_value, omega_design_units)], isMassFlow = get_design_point(spro_file)

        if run_performance_map_bool.lower() == "true":
            if omega_design_units.lower() == "rad/s":
                if rpm_type.lower() == "relative":
                    omega_list = [round(float(rpm_value)*omega_design_value, 1) for rpm_value in rpm_values]
                    rpm_list = [round(omega_value*(30/pi)) for omega_value in omega_list]
                elif rpm_type.lower() == "absolute":
                    rpm_list = [float(rpm_value) for rpm_value in rpm_values]
                    omega_list = [rpm_value/(30/pi) for rpm_value in rpm_list]
                else:
                    print("Please choose either relative or absolute for rpm_type.")
                    exit()
                values_list = omega_list
            elif omega_design_units.lower() == "rpm":
                if rpm_type.lower() == "relative":
                    rpm_list = [round(float(rpm_value)*omega_design_value) for rpm_value in rpm_values]
                    omega_list = [round(rpm_value*(pi/30), 1) for rpm_value in rpm_list]
                elif rpm_type.lower() == "absolute":
                    rpm_list = [float(rpm_value) for rpm_value in rpm_values]
                    omega_list = [rpm_value/(30/pi) for rpm_value in rpm_list]
                else:
                    print("Please choose either relative or absolute for rpm_type.")
                    exit()
                values_list = rpm_list

            if flowrate_type.lower() == "relative":
                flowrate_list = [round(float(flowrate_value)*flow_out_design_value, 8) for flowrate_value in flowrate_values]
            elif flowrate_type.lower() == "absolute":
                flowrate_list = [float(flowrate_value) for flowrate_value in flowrate_values]
            else:
                print("Please choose either relative or absolute for flowrate_type.")
                exit()
        else:
            if omega_design_units.lower() == "rad/s":
                omega_list = [omega_design_value]
                rpm_list = [round(omega_design_value*(30/pi))]
                flowrate_list = [flow_out_design_value]
                values_list = omega_list
            elif omega_design_units.lower() == "rpm":
                rpm_list = [omega_design_value]
                omega_list = [round(omega_design_value*(pi/30), 5)]
                flowrate_list = [flow_out_design_value]
                values_list = rpm_list

        if "steady" in spro_file:
            solver_type = "steady"
        elif "transient" in spro_file and solver_switch == False:
            solver_type = "transient"
            solver_index = 0
            solver_switch = True
        elif "transient" in spro_file and solver_switch == True:
            solver_type = "transient"

        for index, value in enumerate(values_list):
            for flowrate in flowrate_list:
                if run_performance_map_bool.lower() == "true":
                    if isMassFlow == False:
                        new_spro_file = spro_file.split(".")[0] + "_" + str(rpm_list[index]).replace(".", "-") + "rpm_" + str(flowrate).replace(".", "-") + "m3s.spro"
                    else:
                        new_spro_file = spro_file.split(".")[0] + "_" + str(rpm_list[index]).replace(".", "-") + "rpm_" + str(flowrate).replace(".", "-") + "kgs.spro"
                else:
                    new_spro_file = spro_file

                spro_dict = {
                    'file_name': new_spro_file,
                    'solver_type': solver_type,
                    'solver_index': solver_index,
                    'value': value,
                    'omega': omega_list[index],
                    'rpm': rpm_list[index],
                    'flow_out': flowrate
                }
                
                if not os.path.exists(new_spro_file):
                    with open(spro_file, 'r') as infile, open(new_spro_file, 'w') as outfile:
                        data = infile.readlines()
                        for line_number, line in enumerate(data):
                            if "vflow_out = " in line:
                                outfile.write("\t\t" + "vflow_out = " + str(flowrate) + "\n")
                            elif "mflow = " in line:
                                outfile.write("\t\t" + "mflow = " + str(flowrate) + "\n")
                            elif "#Angular velocity" in line:
                                impeller_number = re.search("Omega(\d) = ", data[line_number + 1]).group(1)
                                data[line_number + 1] = ""
                                outfile.write(line + "\t\t" + "Omega" + impeller_number + " = " + str(value) + "\n")    
                            else:
                                outfile.write(line)
                
                spro_dicts.append(spro_dict)

                solver_index = solver_index + 1

    return spro_dicts

def post_process(run_design_variation_bool, project_name, spro_dict, steady_avg_window, transient_avg_window):

    integrals_file = spro_dict.get('file_name').replace(".spro", "_integrals.txt")

    units_dict, desc_dict, isMassFlow = get_Dicts(spro_dict.get("file_name"))

    [(vflow_out_design_value), (omega_design_value, omega_design_units)], isMassFlow = get_design_point(spro_dict.get("file_name"))

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
                if key is not None:
                    if 'userdef.' in key:
                        if key[8:] not in result_dict:
                            try:
                                result_dict[key[8:]] = float(value)
                            except ValueError:
                                print("NaN for " + key[8:] + " in " + spro_dict.get('file_name'))
                                continue
                        else:
                            try:                                                       
                                result_dict[key[8:]] += float(value)
                            except ValueError:
                                print("NaN for " + key + " in " + spro_dict.get('file_name'))
                                continue

        infile.close()

    for key, value in result_dict.items():
        result_dict[key] = value/avg_window

    result_dict['rpm'] = spro_dict.get('rpm')
    result_dict['omega'] = spro_dict.get('omega')
    result_dict['flow_out'] = spro_dict.get('flow_out')

    units_dict['rpm'] = '[rev/min]'
    units_dict['omega'] = '[rad/s]'

    desc_dict['rpm'] = 'Revolutions per minute'
    desc_dict['omega'] = 'Angular velocity'

    if isMassFlow == False:
        desc_dict['flow_out'] = 'Outlet volumetric flux'
        units_dict['flow_out'] = '[m3/s]'
    else:
        desc_dict['flow_out'] = 'Outlet mass flux'
        units_dict['flow_out'] = '[kg/s]'

    stage_keys = []

    for key in units_dict.keys():
        if "CV" in key and "CVI" not in key:
            stage_keys.append(key)

    stage_keys = sorted(stage_keys, key=lambda x:(x[-1], x))

    order = ['rpm', 'omega', 'flow_out', 'DPtt', 'Eff_tt'] + stage_keys

    if run_design_variation_bool.lower() == "true":
        design_number = "Design" + spro_dict.get('file_name').split("Design")[1].split("_" + spro_dict.get('solver_type'))[0]
        result_dict['Design No.'] = design_number
        units_dict['Design No.'] = '[-]'
        desc_dict['Design No.'] = '[-]'
        order.insert(0, 'Design No.')

    for key, value in desc_dict.items():
        if "imp" in value.lower() and "delta p" in value and "passage" not in value:
            order.append(key)
            imp_num = re.findall(r'\d+', key)[0]
            order.append("Eff_tt_" + imp_num + "_i")
            order.append("PC" + imp_num)
            order.append("Torque" + imp_num)
    
    for key, value in desc_dict.items():
        if "power" in value and "passage" not in value and key not in order:
            order.append(key)
        elif "torque" in value and "passage" not in value and key not in order:
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


def run_simerics(run_design_variation_bool, project_name, spro_dicts, steady_avg_window, transient_avg_window):

    spro_files = [spro_dict.get('file_name').strip() for spro_dict in spro_dicts]  

    for index, spro_file in enumerate(spro_files):
        if ("steady" in spro_file and not os.path.exists(spro_file.replace(".spro", ".sres"))) or ("transient" in spro_file and not os.path.exists(spro_file.replace(".spro", "_integrals.txt"))):
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
        
        post_process(run_design_variation_bool, project_name, spro_dicts[index], steady_avg_window, transient_avg_window)

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
    writer.close()

    return 0

def main():

    def Get_ConfigValue(ConfigSection, ConfigKey):                                                      
        ConfigValue = CFconfig[ConfigSection][ConfigKey]
        return ConfigValue

    CFconfig = configparser.ConfigParser()                                                             
    CFconfig.read("master.cftconf")

    project_name = Get_ConfigValue("Project", "project_name")
    run_design_variation_bool = Get_ConfigValue("DesignVariation", "run_design_variation_bool")
    cft_version = Get_ConfigValue("DesignVariation", "cft_version")
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
        values_array = csv_to_np(simple, project_name + "_design_parameters.csv", project_name)
        designs = build_designs(project_name, "steady", "template_steady.cft-batch", values_array, simple)
        spro_files = run_design_variation(designs, cft_version)

        if run_transient_bool.lower() == "true":
            master, simple = build_template(project_name + "_transient.cft-batch", "template_transient.cft-batch")
            values_array = csv_to_np(simple, project_name + "_design_parameters.csv", project_name)
            designs = build_designs(project_name, "transient", "template_transient.cft-batch", values_array, simple)
            spro_files = spro_files + run_design_variation(designs, cft_version)

    else:
        spro_files = [project_name + "_steady.spro"]

        if run_transient_bool.lower() == "true":
            spro_files = spro_files + [project_name + "_transient.spro"]

    CV_stage_components, volumes = get_stage_components(spro_files[0])

    if run_simerics_bool.lower() == "true":
        spro_dicts = run_performance_map(run_performance_map_bool, spro_files, CV_stage_components, volumes, rpm_type, rpm_values, flowrate_type, flowrate_values)
        run_simerics(run_design_variation_bool, project_name, spro_dicts, steady_avg_window, transient_avg_window)
        combine_csv(project_name)

main()
