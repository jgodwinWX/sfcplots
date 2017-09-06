import matplotlib
matplotlib.use("Agg")

import csv
import math
import matplotlib.pyplot as plt
import numpy as np
import random

from collections import OrderedDict
from metar import Metar
from mpl_toolkits.basemap import Basemap

def temperatureParse(obs_string):
    try:
        start = obs_string.find("temperature: ") + 13
        end = obs_string.find(" C",start)
        temperature = obs_string[start:end]
        if len(temperature) > 5:
            return("M")
        return(temperature)
    except ValueError:
        return("M")

def dewpointParse(obs_string):
    try:
        start = obs_string.find("dew point: ") + 11
        end = obs_string.find(" C",start)
        dewpoint = obs_string[start:end]
        if len(dewpoint) > 5:
            return("M")
        return(dewpoint)
    except ValueError:
        return("M")

def winddirParse(obs_string):
    try:
        start = obs_string.find("wind: ") + 6
        end = obs_string.find(" at",start)
        winddir = obs_string[start:end]
        if len(winddir) > 4:
            return("M")
        return(winddir)
    except ValueError:
        return("M")

def windspdParse(obs_string):
    try:
        start = obs_string.find("at ") + 3
        end = obs_string.find(" knots",start)
        windspd = float(obs_string[start:end])
        if len(obs_string[start:end]) > 5:
            return("M")
        return(windspd)
    except ValueError:
        return("M")

def slpParse(obs_string):
    try:
        obs_string.replace("mb","hPa",1)
        start = obs_string.find("sea-level pressure: ") + 20
        end = obs_string.find(" mb",start)
        pressure = obs_string[start:end]
        if len(pressure) > 7:
            return("M")
        return(pressure)
    except ValueError:
        return("M")

# user settings
center_site = "KDFW"    # site to center the map around
filtering = 0.55    # level of filtering (0.50 = 50.%, 0.10 = 10%, etc.)

# import the METAR site locations
metar_site_data = open("metar_sites.csv",'r')
has_header = True
reader = csv.reader(metar_site_data,delimiter=',')

# constants
RIGHTTRIANGLE = 0.5 * np.sqrt(2)    # multiplier for a 45-45-90 triangle

metar_lats = {}
metar_lons = {}
metar_elevs = {}
print "Importing METAR locations"
for row in reader:
    if has_header:
        has_header = False
        continue
    metar_lats[row[0]] = float(row[1])
    metar_lons[row[0]] = float(row[2])
    metar_elevs[row[0]] = float(row[3])

# import the METAR data
print "Importing METAR data"
lines = [line.rstrip("\n") for line in open("metar_data.txt")]
temperature = {}
dewpoint = {}
winddir = {}
windspd = {}
slp = {}
icao_list = []
blacklist = []
novalidtime = True
for k in range(len(lines)):
    if not lines[k]:
        continue
    elif lines[k][0] == "2":
        if novalidtime:
            valid_time = lines[k]
            print "Valid time: %s UTC" % valid_time
            novalidtime = False
        continue
    else:
        try:
            obs = Metar.Metar(lines[k])
            obs_string = obs.string()
            stationid = obs_string[9:13]
            if stationid in icao_list:
                continue
            else:
                icao_list.append(stationid)
                temperature[stationid] = temperatureParse(obs_string)
                dewpoint[stationid] = dewpointParse(obs_string)
                winddir[stationid] = winddirParse(obs_string)
                windspd[stationid] = windspdParse(obs_string)
                slp[stationid] = slpParse(obs_string)
                # "blacklist" sites with missing values
                if temperature[stationid] == "M" or dewpoint[stationid] == "M" or winddir[stationid] == "M" or windspd[stationid] == "M" or slp[stationid] == "M":
                    blacklist.append(stationid)
        except Exception:
            continue

# reorder stations randomly
lat_items = metar_lats.items()
lon_items = metar_lons.items()
random.shuffle(lat_items)
random.shuffle(lon_items)
metar_lats = OrderedDict(lat_items)
metar_lons = OrderedDict(lon_items)

# set up the basemap
print "Drawing basemap"
plt.clf()
fig = matplotlib.pyplot.gcf()
fig.set_size_inches(15.0,10.0)
south = metar_lats[center_site] - 2.5
north = metar_lats[center_site] + 2.5
west = metar_lons[center_site] - 5.0
east = metar_lons[center_site] + 5.0
truelat = metar_lats[center_site]
m = Basemap(projection="merc",llcrnrlat=south,urcrnrlat=north,llcrnrlon=west,urcrnrlon=east,lat_ts=truelat,resolution='i')
m.drawcoastlines()
m.drawcountries()
m.drawstates()
m.drawcounties()

# plot station points
print "Filtering stations to fit map"
sites = []
for key in metar_lats:
    if metar_lats[key] > north or metar_lats[key] < south:
        continue
    elif metar_lons[key] < west or metar_lons[key] > east:
        continue
    else:
        sites.append(key)

# print plot the data
print "Plotting data"
increment = int(len(sites) / int(len(sites) * filtering))
for j in range(0,len(sites),increment):
    if sites[j] in blacklist:
        continue
    lon,lat = metar_lons[sites[j]],metar_lats[sites[j]]
    xpt,ypt = m(lon,lat)
    lonpt,latpt = m(xpt,ypt,inverse=True)
    # plot the wind speed and direction
    try:
        if windspd[sites[j]] == "M":
            continue
        if winddir[sites[j]] == "N":
            u = 0
            v = -windspd[sites[j]]
        elif winddir[sites[j]] == "NE" or winddir[sites[j]] == "NNE" or winddir[sites[j]] == "ENE":
            u = -RIGHTTRIANGLE * windspd[sites[j]]
            v = -RIGHTTRIANGLE * np.sqrt(2) * windspd[sites[j]]
        elif winddir[sites[j]] == "E":
            u = -windspd[sites[j]]
            v = 0.0
        elif winddir[sites[j]] == "SE" or winddir[sites[j]] == "SSE" or winddir[sites[j]] == "ESE":
            u = -RIGHTTRIANGLE * windspd[sites[j]]
            v = RIGHTTRIANGLE * windspd[sites[j]]
        elif winddir[sites[j]] == "S":
            u = 0.0
            v = windspd[sites[j]]
        elif winddir[sites[j]] == "SW" or winddir[sites[j]] == "SSW" or winddir[sites[j]] == "WSW":
            u = RIGHTTRIANGLE * windspd[sites[j]]
            v = RIGHTTRIANGLE * windspd[sites[j]]
        elif winddir[sites[j]] == "W":
            u = windspd[sites[j]]
            v = 0.0
        elif winddir[sites[j]] == "NW" or winddir[sites[j]] == "NNW" or winddir[sites[j]] == "WNW":
            u = RIGHTTRIANGLE * windspd[sites[j]]
            v = -RIGHTTRIANGLE * windspd[sites[j]]
        m.barbs(xpt,ypt,u,v)
    except KeyError:
        continue

    # plot the temperatures
    try:
        if temperature[sites[j]] == "M" or len(temperature[sites[j]]) > 5:
            continue
        temp_f = float(temperature[sites[j]]) * 1.8 + 32.0
        plt.text(xpt-20000,ypt+5000,("%.0f" % temp_f),color="red",size="x-small")
    except KeyError:
        continue

    # plot the dewpoint
    try:
        if dewpoint[sites[j]] == "M" or len(dewpoint[sites[j]]) > 5:
            continue
        dpt_f = float(dewpoint[sites[j]]) * 1.8 + 32.0
        plt.text(xpt-20000,ypt-15000,("%.0f" % dpt_f),color="green",size="x-small")
    except KeyError:
        continue

    # plot the sea-level pressure
    try:
        if slp[sites[j]] == "M" or len(slp[sites[j]]) > 7:
            continue
        if float(slp[sites[j]]) >= 1000.0:
            pres = slp[sites[j]][2:4] + slp[sites[j]][5]
            plt.text(xpt+20000,ypt+5000,pres,color="black",size="x-small")
        elif float(slp[sites[j]]) < 1000.0:
            pres = slp[sites[j]][1:3] + slp[sites[j]][4]
            plt.text(xpt+20000,ypt+5000,pres,color="black",size="x-small")
        else:
            raise Exception("Invalid pressure!")
    except KeyError:
        continue

print "Saving map to PDF"
plt.title("Surface Observations valid %s UTC" % valid_time)
plt.savefig("/home/jgodwin/python/sfcplots/sfcplot.png",bbox_inches="tight")

print "Done!"
