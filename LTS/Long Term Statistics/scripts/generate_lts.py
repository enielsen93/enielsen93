# Tool for reading DFS0 or KM2 files and creating LTS files from it
# Created by Emil Nielsen
# Contact: 
# E-mail: enielsen93@hotmail.com

# Import of modules
import os # path module
import sys
import struct
if struct.calcsize("P") * 8 == 64: # .NET compatibility
    sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "\clr64")
else:
    sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "\clr")
import clr
import numpy as np # matrix manipulation
import bisect # math bisection method
import re # regex for reading KM2
#from System import Array, Char # Convert to .NET array for writing DFS0
from collections import OrderedDict # Dictionairy with order for writing .CSV
from distutils.util import strtobool # Converting string to boolean

import datetime # time series management
from datetime import datetime as dtnow # get time of code
import matplotlib.dates as dates # time series management
import dateutil # parse string to date
import System

from jinja2 import Environment # Templating language
from jinja2.loaders import FileSystemLoader # Templating language

import ConfigParser # .ini read/write
import inspect # global variable
local_vars = {}

# Function that reads KM2
def readKM2(filename):
	global local_vars
	# Read KM2 file as string
	with open(filename,'r') as km2:
		km2Str = km2.readlines()
	
	# Pre-compile regex search patterns
	eventstartlineRE = re.compile(r"^1 \d{8}")
	eventinfoRE = re.compile(r"^1 ?(\d{8}) {0,}(\d{4}) {1,}\d+ {1,}\d+ {1,}(\d+) {1,}([\d\.]+) {1,}(\d+)")
	gaugeintRE = re.compile("([\d\.]+)")
	
	# Definining vectors for event information
	eventstarttime = [] # The start time of each event
	gaugetime = [] # The time vector of the rain gauge
	gaugeint = [] # The intensity vector of the rain gauge in [mu m/s]
	timedelay = 0
	eventrejected = False
	eventfirstline = 1
	
	# Read the KM2 line by line
	for i,line in enumerate(km2Str):
		# If the line contains information about the event:
		if eventstartlineRE.search(line):
			# Split the information into segments
			eventinfo = eventinfoRE.match(line)
			# If it's not rejected ( == 2 ), include it
			# THIS IS NOW DISABLED: It doesn't appear like this feature works like it's supposed to in the KM2 files
			if not eventinfo.group(5) == "4":
				# Get the start time of the event
				eventstarttime.append(dates.date2num(datetime.datetime.strptime(eventinfo.group(1) + " " + eventinfo.group(2),"%Y%m%d %H%M")))
				# Remember that the next line will be the first registrered intensity for the event, so the first measurement can be excluded
				eventfirstline = True
				# It's not rejected, so don't reject the following measurements
				eventrejected = False
				if timedelay>0:
					gaugeint.extend([0])
					gaugetime.extend([gaugetime[-1]+1./60/24])
					timedelay = 0
			# If the event is rejected, remember this
			else:
				eventrejected = True
		# If the line does not contain information about the event, it must contain intensities.
		# If it's not rejected, read the intensities
		elif not eventrejected:
			ints = map(float,gaugeintRE.findall(line))
			# Exclude the first measurement
			if eventfirstline == 1:
				ints = [0] + ints[1:]
			gaugeint.extend(ints)
			gaugetime.extend((np.arange(0,len(ints),dtype=float)+timedelay)/60/24+eventstarttime[-1])
			timedelay += len(ints)
			eventfirstline = False
	return np.asarray(gaugetime,dtype=float),np.asarray(gaugeint)

# Function that reads DFS0 file
def readDFS0(filename,scriptFolder):
	# Use MIKE SDK .NET
	clr.AddReference(scriptFolder + r"\DHI MIKE SDK\DHI.Generic.MikeZero.DFS.dll")
	clr.AddReference(scriptFolder + r"\DHI MIKE SDK\DHI.Generic.MikeZero.EUM.dll")
	import DHI.Generic.MikeZero.DFS
	import DHI.Generic.MikeZero.DFS.dfs0
	# Open DFS0-file
	dfs0File  = DHI.Generic.MikeZero.DFS.DfsFileFactory.DfsGenericOpen(filename)
	dd = DHI.Generic.MikeZero.DFS.dfs0.Dfs0Util.ReadDfs0DataDouble(dfs0File)
	dfs0File.Close();
	ddlist = np.array(list(dd))
	gaugetime = ddlist[range(0,len(ddlist),2)]
	startdate = datetime.datetime(dfs0File.FileInfo.TimeAxis.StartDateTime.Year,dfs0File.FileInfo.TimeAxis.StartDateTime.Month,dfs0File.FileInfo.TimeAxis.StartDateTime.Day,dfs0File.FileInfo.TimeAxis.StartDateTime.Hour,dfs0File.FileInfo.TimeAxis.StartDateTime.Second)
#	toSecFactor = DHI.Generic.MikeZero.eumUtil.ConvertToBase(dfs0File.FileInfo.TimeAxis.TimeUnit,1.0)
	gaugetime = dates.date2num(startdate) + gaugetime/60/60/24
	toMicroMeterPerSecondFactor = DHI.Generic.MikeZero.eumUtil.ConvertToBase(dfs0File.ItemInfo.__getitem__(0).Quantity.Unit,1.0)*1e6
	gaugeint = ddlist[range(1,len(ddlist),2)]*toMicroMeterPerSecondFactor
	return gaugetime,gaugeint

# Function that writes DFS0 file
def writeDFS0(gaugetime,gaugeint,outfile,scriptFolder):
	global local_vars
	gaugetime = gaugetime.tolist()
	gaugeint = gaugeint.tolist()

	# Use MIKE SDK .NET
	clr.AddReference(scriptFolder + r"\DHI MIKE SDK\MatlabDfsUtil.2016.dll")
	clr.AddReference(scriptFolder + r"\DHI MIKE SDK\DHI.Generic.MikeZero.DFS.dll")
	clr.AddReference(scriptFolder + r"\DHI MIKE SDK\DHI.Generic.MikeZero.EUM.dll")
	
	import MatlabDfsUtil 
	import DHI.Generic.MikeZero
	import DHI.Generic.MikeZero.DFS
	import DHI.Generic.MikeZero.DFS.dfs0
	import DHI.Generic.MikeZero.DFS.dfs123
	
	factory = DHI.Generic.MikeZero.DFS.DfsFactory()
	builder = DHI.Generic.MikeZero.DFS.DfsBuilder.Create('Python dfs0 file','Python DFS',0);
	
	starttimeDT = System.DateTime(*dates.num2date(gaugetime[0]).timetuple()[:6], kind=System.DateTimeKind.Utc)

	timeMinutes = ((np.asarray(gaugetime)-gaugetime[0])*24*60).tolist()
	builder.SetDataType(0)
	builder.SetGeographicalProjection(factory.CreateProjectionGeoOrigin('UTM-33',12,54,2.6))
	builder.SetTemporalAxis(factory.CreateTemporalNonEqCalendarAxis(DHI.Generic.MikeZero.eumUnit.eumUminute,starttimeDT))
	
	item1 = builder.CreateDynamicItemBuilder()
	dfsdataType = DHI.Generic.MikeZero.DFS.DfsSimpleType.Float;
	item1.Set('Regnintensitet', DHI.Generic.MikeZero.eumQuantity(DHI.Generic.MikeZero.eumItem.eumIRainfallIntensity,DHI.Generic.MikeZero.eumUnit.eumUMicroMeterPerSecond), dfsdataType)
	item1.SetValueType(DHI.Generic.MikeZero.DFS.DataValueType.Instantaneous)
	item1.SetAxis(factory.CreateAxisEqD0())
	builder.AddDynamicItem(item1.GetDynamicItemInfo())
	
	builder.CreateFile(outfile)
	dfs = builder.GetFile()
	
	gaugeintArr = System.Array.CreateInstance(float,len(gaugeint),1)
	for i,val in enumerate(gaugeint):
		gaugeintArr[i,0] = val
	
	MatlabDfsUtil.DfsUtil.WriteDfs0DataDouble(dfs, Array[float](timeMinutes), gaugeintArr)
	local_vars = inspect.currentframe().f_locals	
	dfs.Close()
	return

# Function that returns the data period for a rain series
def getDataPeriod(parameters,scriptFolder): 
	if ".dfs0" in parameters[0].valueAsText:
		gaugetime,_ = readDFS0(parameters[0].valueAsText,scriptFolder)
	else:
		gaugetime,_ = readKM2(parameters[0].valueAsText)
	dataperiod = (gaugetime[-1]-gaugetime[0])/365
	daterange = dates.num2date(gaugetime[0]).strftime("%d/%m/%Y") + " - " + dates.num2date(gaugetime[-1]).strftime("%d/%m/%Y")
	return dataperiod,daterange

# Function that returns the bootstrapped samples of a set of parameters
def bootstrap_resample(X, samples, n=None):
	if n == None:
		n = np.size(X,axis=0)
	X_resample = np.empty((np.size(X,axis=0),0),dtype=np.float16)
	for i in range(0,samples):
		resample_i = np.floor(np.random.rand(n)*np.size(X,axis=0)).astype(int)
		X_resample = np.append(X_resample,np.transpose([X[resample_i]]),axis=1)
	return X_resample

# Main function that writes LTS files from rain series file
def writeLTS(parameters,scriptFolder):
	try:
		global local_vars
		# Open log file
		logFile = open(os.path.join(scriptFolder.encode('ascii','ignore'),'log.txt'),'w')
		# Read old config file and write new config file
		if not __name__ == '__main__':
			parametersDict = {}
			configWrite = ConfigParser.ConfigParser(allow_no_value=True)
	#			configWrite.add_section("Tool Settings")
			configWrite.add_section("ArcGIS input parameters")
	#			configRead = ConfigParser.ConfigParser(allow_no_value=True)
	#			configRead.read(scriptFolder + r"\config.ini")
	#			for item,value in configRead.items("Tool Settings"):
	#				parametersDict[item] = value
	#				configWrite.set("Tool Settings",i,par.value)
			for i,par in enumerate(parameters):
				if par.value==None:
					par.value = 0
				parametersDict[par.name] = str(par.valueAsText)
				if i == 0:
					configWrite.set("ArcGIS input parameters","# " + par.displayName)
				else:
					configWrite.set("ArcGIS input parameters","\r\n# " + par.displayName)
				configWrite.set("ArcGIS input parameters",par.name,par.value)
			with open(scriptFolder + r"\config.ini", "wb") as config_file:
				configWrite.write(config_file)
		else:
			parametersDict = parameters
		
		# Write parameters to log file
		logFile.write(str(dtnow.now())+": Starting tool Create LTS-file using the following parameters:\n")
		for key, value in parametersDict.iteritems():
			logFile.write(key+": " +value + "\n")
		logFile.write("\n")
		
		# Reading input file
		logFile.write(str(dtnow.now())+": Reading input file\n")
		if ".dfs0" in parametersDict["input_file"]:
			gaugetime,gaugeint = readDFS0(parametersDict["input_file"],scriptFolder)
		else:
			gaugetime,gaugeint = readKM2(parametersDict["input_file"])
		
		if strtobool(parametersDict["dfs0_output_enable"])==True:
			logFile.write(str(dtnow.now())+": Writing DFS0 file\n")
			writeDFS0(gaugetime,gaugeint,parametersDict["dfs_output"],scriptFolder)
	
		# Convert time to total minutes
		tminutes = np.int32(gaugetime*24*60)
	
		logFile.write(str(dtnow.now())+": Initializing time aggregate periods\n")
		# Time aggregates
		if strtobool(parametersDict["time_aggregate_enable"]) == False:
			dts = [5]
		elif parametersDict["rain_event_merge"]:
			dts = float(parametersDict["rain_event_merge_duration"])
		else:
			dts = map(int,parametersDict["time_aggregate_periods"].split(';'))#[1, 5, 10, 30, 60, 180, 360]		
	
		logFile.write(str(dtnow.now())+": Calculating rain depth over total event and time aggregate periods\n")
		j = 0 # Time in time aggregate loop
		eventidx = 0 # Event index
		tdiff = np.int64(np.diff(tminutes, n=1, axis=0)) # Calculate time diff between each intensitety data point
		RDAgg = np.empty((0,len(dts)+1),dtype=np.float) # Initialize rain aggregate matrix
		startj = endj = np.empty((0,0),dtype=np.int) # Initialize starttime and stop time for each event
		# Loop over all intensity data points
		while j<np.size(tminutes)-1:
			# End of each event is when there's a dry period of xxx minutes
#			if not parametersDict["rain_event_merge"]:
			jend = np.argmax(tdiff[j:]>max(max(dts),10))+j

			# Initialize time aggregate set for this event
			RDAgg = np.append(RDAgg,np.zeros((1,len(dts)+1),dtype=np.float),axis=0)
			# Start time of this event
			startj = np.append(startj,np.int(j))
			# Calculate total rain depth for event
			RDAgg[eventidx,-1] = np.sum(gaugeint[j:jend])/1000*60
			# Loop over all intensities in event
			for j in xrange(j,jend):
				# Loop over all time aggregate periods
				for i, dt in enumerate(dts):
					# Calculate total rain depth over aggregate period
					mm = np.sum(gaugeint[j:j+bisect.bisect_left((tminutes[j:j+dt]-tminutes[j]),dt)])/1000*60
					if (mm>RDAgg[eventidx,i]):
						RDAgg[eventidx,i] = mm
			# End time of this event
			endj = np.append(endj,np.int(jend))
			j+=2
			eventidx+=1 # Change event index
			
		logFile.write(str(dtnow.now())+": Initializing time series duration\n")
		if (float(parametersDict["time_series_duration"]) == 0):
			dataperiod = np.float((tminutes[-1]-tminutes[0])/60/24) # Calculate total data period for time series
		else:
			dataperiod = float(parametersDict["time_series_duration"])*365
		
		# Sort the time aggregates according to rain depth
		sortidx = np.argsort(-RDAgg,axis=0)
		RDAggSort = np.flipud(np.sort(RDAgg,axis=0))
		
		logFile.write(str(dtnow.now())+": Calculating total number of events for time aggregate and total rain depth\n")
		# Calculate number events of time aggregate from return period or just number of events
		if strtobool(parametersDict["time_aggregate_enable"]) == False:
			eventsAgg = 0
			eventsAggByRP = False
		elif not (int(parametersDict["time_aggregate_number_events"]) == 0):
			eventsAgg = float(parametersDict["time_aggregate_number_events"]) #np.int(np.ceil(dataperiod/(RP*365)))
			eventsAggByRP = False
		elif not (float(parametersDict["time_aggregate_return_period"].split("+")[0]) == 0):
			eventsAgg = np.int(np.floor(dataperiod/(float(parametersDict["time_aggregate_return_period"].split("+")[0])*365)))
			if "+" in parametersDict["time_aggregate_return_period"]:
				eventsAgg = eventsAgg + float(parametersDict["time_aggregate_return_period"].split("+")[1])
			eventsAggByRP = True
		else:
			eventsAgg = 0
			eventsAggByRP = False
	
#		logFile.write(parametersDict["include_events_return_period"])
#		logFile.write(parametersDict["include_events_return_period"].split("+"))
		# Calculate number events of total rain depth from return period or total rain depth
		if not (float(parametersDict["include_events_total_rain_depth"]) == 0):
			eventsSum = sum(RDAgg[:,-1]>float(parametersDict["include_events_total_rain_depth"]))#parameters[3].value #np.int(np.ceil(dataperiod/(RP*365)))
		elif not (float(parametersDict["include_events_return_period"].split("+")[0]) == 0):
			eventsSum = np.int(np.floor(dataperiod/(float(parametersDict["include_events_return_period"].split("+")[0])*365)))
			if "+" in parametersDict["include_events_return_period"]:
				eventsSum = eventsSum + float(parametersDict["include_events_return_period"].split("+")[1])
		else:
			eventsSum = 0
		
		# Parse date criteria as number
		if parametersDict["date_criteria"] and not parametersDict["date_criteria"]=="0":
			date_criteria = parametersDict["date_criteria"].split(' - ')
			date_criteriaNum = []
			for i,d in enumerate(date_criteria):
				date_criteriaNum.append(dates.date2num(dateutil.parser.parse(d,dayfirst=True,default=datetime.datetime(datetime.datetime.now().year,1,1))))
		else: # If it's empty, just set it to this
			date_criteriaNum = [0, 1e10]
		
		# Calculate 95% confidence interval for return period of rain event
		logFile.write(str(dtnow.now())+": Bootstrapping and calculating 95% confidence interval for return period of rain event\n")
		rd = RDAggSort[0:eventsSum*3,-1]
		rdbs = bootstrap_resample(rd,1000)
		rps = (dataperiod/365)/np.flipud(np.arange(0,np.size(rdbs,axis=0))+1)
		rdbs = np.sort(rdbs,axis=0)
		alpha = 0.05
		rpconfint = []
		rpmedian = []
		for i,r in enumerate(rd[0:eventsSum]): #-eventsSum-1:
			k = np.where(rdbs==r)
			rp = rps[k[0]]
			rpconfint.append(rp[np.floor(np.size(rdbs,axis=0)*alpha).astype(int)])
			rpmedian.append(rps[-1-i])
	
		# Initialize event information vectors
		eventstarttime = eventstoptime = eventstarttimeStr = []
		eventstoptimeStr = []
		durHour = []
		accrain = []
		durTotal = 0
		eventdts = []
		rpevent = []
		rpeventmedian = []	
				
		logFile.write(str(dtnow.now())+": Assembling selected events to LTS data set by total rain depth\n")
		# Start selecting and including events by total rain depth
		for eventidx in range(0,np.int(eventsSum)):
			# Event start time and stop time for the included event
			eventstarttime = dates.num2date(gaugetime[startj[sortidx[eventidx,-1]]]-float(parametersDict["soft_start_time"])/60/24)
			eventstoptime = dates.num2date(gaugetime[endj[sortidx[eventidx,-1]]]+float(parametersDict["soft_stop_time"])/60/24)
			# If the event starts within the selected dates, include it.
			if (date_criteriaNum[0] < gaugetime[startj[sortidx[eventidx,-1]]] < date_criteriaNum[1]):
				# If this event is not already included in the set, include it
				if not (eventstarttime.strftime('%Y-%m-%d %H:%M:00') in eventstarttimeStr):
					# Write the times to strings
					eventstarttimeStr.append(eventstarttime.strftime('%Y-%m-%d %H:%M:00'))
					eventstoptimeStr.append(eventstoptime.strftime('%Y-%m-%d %H:%M:00'))
					eventdts.append(['total event'])
					# Calculate the duration of the event
					dur = (eventstoptime-eventstarttime).seconds
					durTotal += float(dur)/3600
					durHour.append("%d" % (dur/3600))
					print durHour
					rpevent.append(rpconfint[eventidx])
					rpeventmedian.append(rpmedian[eventidx])
					
					# Calculate the rain depth of the event
					accrain.append("%1.1f" % (RDAgg[sortidx[eventidx,-1],-1]))
				else:
					eventdts[eventstarttimeStr.index(eventstarttime.strftime('%Y-%m-%d %H:%M:00'))].append('total event')
		
		logFile.write(str(dtnow.now())+": Assembling selected events to LTS data set by time aggregate\n")
	
		# Start selecting and including events by time aggregate
		eventidx = 0 # Index of event
		# If select by return period is enabled, continue until all events with return period above criteria have been tested
		# If select by number of events is enabled, continue until the number of included events has reached this number
		eventsAggByTA = np.zeros((len(dts)))+eventsAgg # Amount of events that should be included for each aggregate period
		eventsAggByTAIncl = np.zeros((len(dts))) # Amount of events concluded for each aggregate period
		while ((not eventsAggByRP)*sum(eventsAggByTAIncl)) < np.sum(eventsAggByTA) and eventsAggByRP*eventidx < eventsAgg:
			for i in range(0,np.size(dts)):
				# Event start time and stop time for the included event
				eventstarttime = dates.num2date(gaugetime[startj[sortidx[eventidx,i]]]-float(parametersDict["soft_start_time"])/60/24)
				eventstoptime = dates.num2date(gaugetime[endj[sortidx[eventidx,i]]]+float(parametersDict["soft_stop_time"])/60/24)
				# If the event starts within the selected dates, include it. If there's already enough events for that aggregate period, exclude it.
				if (date_criteriaNum[0] <= gaugetime[startj[sortidx[eventidx,i]]] <= date_criteriaNum[1]) and eventsAggByTAIncl[i]<eventsAggByTA[i]:
					# If this event is not already included in the set, include it
					if not (eventstarttime.strftime('%Y-%m-%d %H:%M:00') in eventstarttimeStr):
						# Write the times to strings
						eventstarttimeStr.append(eventstarttime.strftime('%Y-%m-%d %H:%M:00'))
						eventstoptimeStr.append(eventstoptime.strftime('%Y-%m-%d %H:%M:00'))
						eventdts.append(["%d min" % (dts[i])])
						# Calculate the duration of the event
						dur = (eventstoptime-eventstarttime).seconds
						durTotal += float(dur)/3600
						durHour.append("%d" % (dur/3600))
						rpevent.append([])
						rpeventmedian.append([])
						
						# Calculate the rain depth of the event
						accrain.append("%1.1f" % (RDAgg[sortidx[eventidx,i],-1]))
					else:
						eventdts[eventstarttimeStr.index(eventstarttime.strftime('%Y-%m-%d %H:%M:00'))].append("%d min" % (dts[i]))
					eventsAggByTAIncl[i] += 1
			eventidx +=1
					
		# Write strings of duration and data period for insertion into LTS.MJL file
		durTotalDay,remainder = divmod(durTotal,24)
		durTotalDay = int(durTotalDay)
		_,durTotalHour = divmod(remainder,60)
		durTotalHour = int(durTotalHour)
		durTotalStr = "%d days, %dh" % (durTotalDay,durTotalHour)
		dataperiodYears,remainder = divmod(dataperiod,365)
		dataperiodMonths = int(remainder/365*12)
		dataperiodStr = "%d years, %d months" % (dataperiodYears,dataperiodMonths)
		
		# Sort rain events by start time
		zipped = zip(eventstarttimeStr, eventstoptimeStr, durHour, accrain, eventdts, rpevent, rpeventmedian)
		zipped.sort()
		eventstarttimeStr, eventstoptimeStr, durHour, accrain, eventdts, rpevent, rpeventmedian = zip(*zipped)
		
		#####
		# Write LTS file through jinga2 module
		# Jinga2 reads a text file and uses it as a template for creating LTS files
		#####
		logFile.write(str(dtnow.now())+": Writing LTS file using Jinga2\n")
	
		Environment(loader=FileSystemLoader(''))
		eventlist = xrange(0,np.size(eventstarttime))
		# Load LTS template file
		templateFile = open(os.path.join(scriptFolder.encode('ascii','ignore'),'LTSTemplate.MJL'),'r')
		templateFileStr = templateFile.read()
	
		# Write LTS file with event information vectors
		fout = open(parametersDict["output_mjl"],'w+')
		fout.write(Environment().from_string(templateFileStr).render(inputfile=parametersDict["input_file"],eventlist=eventlist,simulation_start=eventstarttimeStr,simulation_stop=eventstoptimeStr,
						  job_number=range(1,len(eventstarttimeStr)+1),dur_time=durHour,jobs=len(eventstarttimeStr),total_dur_time=durTotalStr,
						  dataperiod=dataperiodStr,accumulated_rain=accrain,eventdts = eventdts,rpevent=rpevent,rpeventmedian=rpeventmedian,alpha=100-alpha*100,date_criteria=parametersDict["date_criteria"]))
		fout.close()
		
		# Create csv-file with LTS events		
		logFile.write(str(dtnow.now())+": Creating csv-file with LTS-events\n")
		csvDict = OrderedDict()
		csvDict["Simulation start"] = eventstarttimeStr
		csvDict["Simulation stop"] = eventstoptimeStr
		csvDict["Accumulated rain [mm]"] = accrain
		with open('LTSJobList.csv', 'w') as csvfile:
			csvfile.write("Job")
			[csvfile.write(',{0}'.format(key)) for key, _ in csvDict.items()]
			for i in range(0,len(csvDict["Simulation start"])):
				csvfile.write("\n{0}".format(i+1))
				[csvfile.write(',{0}'.format(value[i])) for _, value in csvDict.items()]
		logFile.write(str(dtnow.now())+": Succesful run\n")
		logFile.close()
		local_vars = inspect.currentframe().f_locals
		# If error occurs, write log-file
	except Exception as exc:
		local_vars = inspect.currentframe().f_locals
		logFile.write(str(exc))
		logFile.close()
		raise(exc)
	return

# Second function that combines LTS files to one total LTS file
def combineLTS(parameters,scriptFolder):
	scriptFolder = r"D:\Complete\tool\scripts"
	lts_files = str(parameters[0].valueAsText).split(";")
	starttime = []
	stoptime = []
	starttimeRE = re.compile(r"Simulation_start {0,}= {0,}'([^']+)'")
	stoptimeRE = re.compile(r"Simulation_end {0,}= {0,}'([^']+)'")
	input_files = []
	for lts_file in lts_files:
		with open(lts_file.replace('\'',''), 'r') as lts_file_open:
			text = lts_file_open.read()
			starttime.extend(starttimeRE.findall(text))
			stoptime.extend(stoptimeRE.findall(text))
			input_files.extend([lts_file]*len(starttimeRE.findall(text)))
	
	dur = []
	durTotal = 0
	for i in range(0,len(starttime)):
		dur.append('%d' % ((dates.date2num(datetime.datetime.strptime(stoptime[i],"%Y-%m-%d %H:%M:00")) - dates.date2num(datetime.datetime.strptime(starttime[i],"%Y-%m-%d %H:%M:00")))*24))
		durTotal += (dates.date2num(datetime.datetime.strptime(stoptime[i],"%Y-%m-%d %H:%M:00")) - dates.date2num(datetime.datetime.strptime(starttime[i],"%Y-%m-%d %H:%M:00")))*24
				
	durTotalDay,remainder = divmod(durTotal,24)
	durTotalDay = int(durTotalDay)
	_,durTotalHour = divmod(remainder,60)
	durTotalHour = int(durTotalHour)
	durTotalStr = "%d days, %dh" % (durTotalDay,durTotalHour)			
	
	job_number = range(1,len(starttime)+1)
		
	Environment(loader=FileSystemLoader(''))
	# Load LTS template file
	templateFile = open(os.path.join(scriptFolder.encode('ascii','ignore'),'LTSTemplateCombined.MJL'),'r')
	templateFileStr = templateFile.read()
	
	# Write LTS file with event information vectors
	fout = open(parameters[1].valueAsText,'w+')
	fout.write(Environment().from_string(templateFileStr).render(inputfile=lts_files,simulation_start=starttime,simulation_stop=stoptime,job_number=job_number,
			   dur_time=dur,total_dur_time=durTotalStr,jobs=job_number[-1],input_fileI=input_files))
	fout.close()
	return

# If this .py-file is run as a stand-alone, write an LTS-file with parameters from .ini-file (generated from previous run from ArcGIS)
if __name__ == '__main__':
	# Read config file
	config = ConfigParser.ConfigParser()
	config.read("config.ini")
	parametersDict = {}
	for option in config.options("ArcGIS input parameters"):
		parametersDict[option] = config.get("ArcGIS input parameters",option)
#
#	scriptFolder = os.path.dirname(os.path.realpath(__file__))
	scriptFolder = r"C:\Users\Eniel\Documents\Spyder\Long Term Statistics\scripts\\"
#	# Write LTS using parameters from config file
	writeLTS(parametersDict,scriptFolder)
