# -*- coding: utf-8 -*-
"""

@author: Ye
"""

import pandas as pd
from mpl_toolkits.basemap import Basemap
import matplotlib.pyplot as plt
import numpy as np


df = pd.read_csv("E:\BaiduYunDownload\heatmapip5_clean_city.csv",header=False,\
                    names=["count","IP","latt","longt","city"])

print df.head()
#中国平面
m = Basemap(projection="mill",llcrnrlat=4,urcrnrlat=53,
            llcrnrlon=70,urcrnrlon=135,resolution="c")

#全世界平面，不要南北极
#m = Basemap(projection="mill",llcrnrlat=-60,urcrnrlat=90,
#            llcrnrlon=-180,urcrnrlon=180,resolution="c")

#地球体
#m = Basemap(projection='ortho', lat_0=0, lon_0=100,
#              resolution='l', area_thresh=1000.0)

#地球体平面
#m = Basemap(projection='robin', lat_0=0, lon_0=100,
#              resolution='l', area_thresh=1000.0)
#海岸线
#m.drawcoastlines(linewidth=0.1,color='b')  
#m.drawcoastlines()
#国家
#m.drawcountries(linewidth=0.1,color='k')  
#m.drawcountries()
#州
#m.drawstates(linewidth=0.1,color='r')
#河流
#m.drawrivers(linewidth=0.1,color='g')  
#边界
m.drawmapboundary(fill_color='#689CD2') 
#m.drawmapboundary() 
#大陆
#m.fillcontinents(color='#BF9E30',lake_color='#689CD2',zorder=0)
m.fillcontinents(color='#eeefff')


#经纬线
#m.drawmeridians(np.arange(0,360,30))  
#m.drawparallels(np.arange(-90,90,30))  

#卫星图
#m.bluemarble()    
m.readshapefile("C:\Users\Ye\Documents\Python Scripts\StatPlanet_China\map\map",
                "All regionsasdas")

latt = tuple(df["latt"])
print len(latt)
longt = tuple(df["longt"])

x,y = m(longt,latt)

m.plot(x,y,"b.",markersize=3,alpha=1)
#lon = 121
#lat = 31
#x,y = m(lon, lat)

#http://matplotlib.org/api/axes_api.html#matplotlib.axes.Axes.plot   plot标志
#m.plot(x, y, 'r.', markersize=10)
#plt.text(x+10000,y+5000,"shanghai")

plt.title("IP distribution")
plt.show()
