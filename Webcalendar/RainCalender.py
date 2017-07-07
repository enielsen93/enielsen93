import csv
import numpy as np
import datetime
#import matplotlib.pyplot as plt

gaugetime = []
gaugeint = []
with open('RainData.csv', 'rb') as f:
    reader = csv.reader(f)
    for row in reader:
        gaugetime.append(float(row[0]))
        gaugeint.append(float(row[1]))
        
gaugetime = np.asarray(gaugetime)
gaugeint = np.asarray(gaugeint)
gaugeday = np.floor(gaugetime)
days = np.unique(gaugeday)
gaugedayacc = np.empty((len(days),1))
for i, day in enumerate(days):
    idx = np.where(gaugeday==day)
    gaugedayacc[i] = np.sum(gaugeint[idx])/1000*60
    
dts = [10, 30, 60, 120]
maxRAgg = np.zeros((len(days),len(dts)))

for i, day in enumerate(days):
    idx = np.where(gaugeday==day)
    if len(idx[0])<2:
        continue
    gx = gaugetime[idx]
    gy = gaugeint[idx]
    gxminutes = np.round(gx*24*60)
    gxpad = np.concatenate((gxminutes, np.arange(int(gxminutes[1]),int(gxminutes[-1]),1)))
    gypad = np.concatenate((gy,np.arange(len(gxpad)-len(gy),dtype=float)*0))
    _,idx = np.unique(gxpad,1)
    gxsort = gxpad[idx]
    gysort = gypad[idx]
    for j, dt in enumerate(dts):
        for k in range(np.max(np.append(1,len(gxsort)-dt))):
            sumR = np.sum(gysort[k:k+dt-1]/1000*60)
            if sumR > maxRAgg[i,j]:
                maxRAgg[i,j] = sumR
#        if (j>1 and maxRAgg[i,j-1]>maxRAgg[i,j]):
#            maxRAgg[i,j] = maxRAgg[i,j-1]

#    print len(gx)
#    print len(gxpad)/2
    

with open(r'RainStats.csv', 'wb') as csvfile:
    writer = csv.writer(csvfile, delimiter=',',
    quotechar='|', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(['Date', 'agg0','agg10','agg30','agg60','agg120'])
    for i in range(0,len(days)):
        dt = datetime.datetime.fromordinal(int(days[i])) + datetime.timedelta(days=days[i]%1) - datetime.timedelta(days = 366)
        writer.writerow([dt.strftime('%Y-%m-%d'),round(gaugedayacc[i,0],1),round(maxRAgg[i,0],2),round(maxRAgg[i,1],2),round(maxRAgg[i,2],2),round(maxRAgg[i,3],2)])
#    
#plt.hist(gaugedayacc, normed=True, bins=30)
#
#with open(r'Rain.csv', 'wb') as csvfile:
#    writer = csv.writer(csvfile, delimiter=',',
#    quotechar='|', quoting=csv.QUOTE_MINIMAL)
#    writer.writerow(['Time', 'Rain'])
#    for i in range(0,len(gaugetime)):
#        dt = datetime.datetime.fromordinal(int(gaugetime[i])) + datetime.timedelta(days=gaugetime[i]%1) - datetime.timedelta(days = 366)
#        writer.writerow([dt.strftime('%Y-%m-%d %H:%M:%S'),round(gaugeint[i],3)])