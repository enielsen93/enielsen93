# Tool for reading DFS0 or KM2 files and creating LTS files from it
# Created by Emil Nielsen
# Contact: 
# E-mail: enielsen93@hotmail.com

import arcpy
import os
import sys
thisFolder = os.path.dirname(__file__)
scriptFolder = os.path.join(thisFolder, r"scripts")
sys.path.append(scriptFolder)
import generate_lts
reload(generate_lts)  # add a forced reload

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Long Term Statistics"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [LTSGenerator,LTSCombiner]


class LTSGenerator(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Create LTS-file"
        self.description = "Generate a Mike Urban LTS (Long Term Statistics) file from a DFS0 or KM2 file for a rain gauge. \n\nCreated by: Emil Nielsen \nContact: enielsen93@hotmail.com"
        self.canRunInBackground = False

    def getParameterInfo(self):
		#Define parameter definitions

		# First parameter
		param0 = arcpy.Parameter(
			displayName="Input DFS0 or KM2 file (Rain series)",
			name="input_file",
			datatype="File",
			parameterType="Required",
			direction="Input")
		param0.filter.list=["dfs0","km2"]
			
		param2 = arcpy.Parameter(
			displayName="Output MOUSE job list (MJL) file",
			name="output_mjl",
			datatype="File",
			parameterType="Required",
			direction="Output")
		param2.filter.list=["MJL"]
		
		param3 = arcpy.Parameter(
			displayName="Use time aggregates",
			name="time_aggregate_enable",
			datatype="Boolean",
			parameterType="optional",
			direction="Output")
		param3.value = False
		param3.category = "Time Aggregate"
			
		param4 = arcpy.Parameter(
			displayName="Time aggregates: [min]",
			name="time_aggregate_periods",
			datatype="Long",
			parameterType="Optional",
			direction="Input",
			multiValue=True)
		param4.value = [10,30,60,180,360]
		param4.enabled = False
		param4.filter.type = "Range"
		param4.filter.list = [1, 100000]
		param4.category = "Time Aggregate"
		
		param5 = arcpy.Parameter(
			displayName="Include all rain events with total rain depth above: [mm]",
			name="include_events_total_rain_depth",
			datatype="double",
			parameterType="Optional",
			direction="Input")
		
		param6 = arcpy.Parameter(
			displayName="Soft start time [min]",
			name="soft_start_time",
			datatype="double",
			parameterType="Optional",
			direction="Input")
		param6.value = 0
		
		param7 = arcpy.Parameter(
			displayName="Soft stop time [min]",
			name="soft_stop_time",
			datatype="double",
			parameterType="Optional",
			direction="Input")
		param7.value = 0
		
		param8 = arcpy.Parameter(
			displayName="Include all rain events with return period above: [year]",
			name="include_events_return_period",
			datatype="String",
			parameterType="Optional",
			direction="Input")
			
		param9 = arcpy.Parameter(
			displayName="Return period above: [year]",
			name="time_aggregate_return_period",
			datatype="String",
			parameterType="Optional",
			direction="Input")
		param9.category = "Time Aggregate"
		
		param10 = arcpy.Parameter(
			displayName="Number of included events for each aggregate:",
			name="time_aggregate_number_events",
			datatype="long",
			parameterType="Optional",
			direction="Input")
		param10.category = "Time Aggregate"
		
		param11 = arcpy.Parameter(
			displayName="Duration of time series: [years]",
			name="time_series_duration",
			datatype="double",
			parameterType="Optional",
			direction="Input")
			
		param12 = arcpy.Parameter(
			displayName="Select only rain events between these two dates:",
			name="date_criteria",
			datatype="String",
			parameterType="Optional",
			direction="Input")	
		
		param13 = arcpy.Parameter(
			displayName="Save DFS0 file",
			name="dfs0_output_enable",
			datatype="Boolean",
			parameterType="Optional",
			direction="Input")	
		param13.category = "Save DFS0 file"
		
		param14 = arcpy.Parameter(
			displayName="Output DFS0 file",
			name="dfs_output",
			datatype="File",
			parameterType="Optional",
			direction="Output")
		param14.category = "Save DFS0 file"
		param14.enabled = False
		# param14.filter.list=["dfs0"]
		
		param15 = arcpy.Parameter(
			displayName="Merge rain events over dry periods",
			name="rain_event_merge",
			datatype="Boolean",
			parameterType="Optional",
			direction="input")
		param15.category = "Merge rain events"
		
		param16 = arcpy.Parameter(
			displayName="Merge rain events with dry periods shorter than [min]",
			name="rain_event_merge_duration",
			datatype="double",
			parameterType="Optional",
			direction="input")
		param16.category = "Merge rain events"
		param16.enabled = False
		param16.value = 60
		
		# param15 = arcpy.Parameter(
			# displayName="Shorten DFS0 file",
			# name="dfs0_shorten_enable",
			# datatype="Boolean",
			# parameterType="Optional",
			# direction="Input")
	
		#	0	param0: Input DFS0-file (Rain series) 
		#	1	param2: Output MOUSE job list (MJL) file
		#	10	param3: Use time aggregates
		#	9	param4: Time aggregates: [min]
		#	3	param5: Include all rain events with total rain depth above: [mm]
		#	5	param6: Soft start time [min]
		#	6	param7: Soft stop time [min]
		#	4	param8: Include all rain events with return period for total rain depth above: [year]
		#	7	param9: Return period above: [year]
		#	8	param10: Number of included events for each aggregate:
		#	2	param11: Duration of time series: [years]


		params = [param0, param2, param11, param12, param5, param8, param6, param7, param3, param9, param10, param4, param13, param14, param15, param16] #, param13, param14, param15

		return params

    def isLicensed(self):
		return True

    def updateParameters(self, parameters):		
		# Set the default distance threshold to 1/100 of the larger of the width
		#  or height of the extent of the input features.  Do not set if there is no 
		#  input dataset yet, or the user has set a specific distance (Altered is true).
		#
		if parameters[0].altered:
			if not parameters[1].valueAsText:
				filename, _ = os.path.splitext(parameters[0].valueAsText)
				parameters[1].value = filename +".MJL"
			if not parameters[2].valueAsText or not parameters[3].valueAsText:
				dataperiod,daterange = generate_lts.getDataPeriod(parameters,scriptFolder)
				if not parameters[2].valueAsText:
					parameters[2].value = round(float(dataperiod),1)
				if not parameters[3].valueAsText:
					parameters[3].value = daterange
			if not parameters[13].valueAsText:
				if ".km2" in str(parameters[0].valueAsText) and parameters[12].value == True:
					filename, _ = os.path.splitext(parameters[0].valueAsText)
					parameters[13].value = filename +".dfs0"
		if parameters[8].value == True:
			parameters[9].enabled = True
			parameters[11].enabled = True
			parameters[10].enabled = True
		else:
			parameters[9].enabled = False
			parameters[11].enabled = False
			parameters[10].enabled = False
		if parameters[12].value == True:
			parameters[13].enabled = True
		else:
			parameters[13].enabled = False
		if parameters[14].value == True:
			parameters[15].enabled = True
		else: 
			parameters[15].enabled = False
			return

    def updateMessages(self, parameters):
		if True:
			if parameters[4].value > 0:
				if parameters[5].value > 0:
					parameters[5].setErrorMessage("Can't include by both total rain depth and return period.")
					parameters[4].setErrorMessage("Can't include by both total rain depth and return period.")
			if parameters[8].value == True:
				if parameters[10].value > 0:
					if parameters[9].value > 0:
						parameters[9].setErrorMessage("Can't include by both return period and number of events.")
						parameters[10].setErrorMessage("Can't include by both return period and number of events.")
			if parameters[3].value:
				if not " - " in parameters[3].value:
					parameters[3].setErrorMessage("Date range must contain \" - \" without the quotation marks.")
					return
			if parameters[14].value == True:
				if not parameters[15].value > 0:
					parameters[15].setErrorMessage("Must select duration of dry period")

    def execute(self, parameters, messages):
		generate_lts.writeLTS(parameters,scriptFolder)
		return
class LTSCombiner(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Combine LTS-files"
        self.description = "Combine two LTS-files. \n\nCreated by: Emil Nielsen \nContact: enielsen93@hotmail.com"
        self.canRunInBackground = False

    def getParameterInfo(self):
		#Define parameter definitions

		# First parameter
		param0 = arcpy.Parameter(
			displayName="Input LTS files",
			name="LTS_input_files",
			datatype="File",
			parameterType="Required",
			direction="Input",
			multiValue=True)
		param0.filter.list=["mjl"]
		
		param1 = arcpy.Parameter(
			displayName="Output combined LTS file",
			name="LTS_output_file",
			datatype="File",
			parameterType="Required",
			direction="Output")
		param1.filter.list=["mjl"]
		
		params = [param0, param1]

		return params

    def isLicensed(self):
		return True

    def updateParameters(self, parameters):		
		# Set the default distance threshold to 1/100 of the larger of the width
		#  or height of the extent of the input features.  Do not set if there is no 
		#  input dataset yet, or the user has set a specific distance (Altered is true).
		#
		return

    def updateMessages(self, parameters):
		return

    def execute(self, parameters, messages):
		generate_lts.combineLTS(parameters,scriptFolder)
		return
		
#def main():
#	tbx = Toolbox()
#	tool = LTSGenerator()
#	parameters = tool.getParameterInfo()
#	tool.execute(tool.getParameterInfo(),None)

#if __name__=='__main__':
#	main()