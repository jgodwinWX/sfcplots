#!/bin/env python

import cartopy.crs as ccrs
import cartopy.feature as feat
import math
import matplotlib.pyplot as plt
import numpy as np
import pandas

from awips.dataaccess import DataAccessLayer
from datetime import datetime,timedelta
from dynamicserialize.dstypes.com.raytheon.uf.common.time import TimeRange
from matplotlib import rcParams
from metpy.calc import get_wind_components
from metpy.plots import StationPlot,StationPlotLayout,simple_layout
from metpy.plots.wx_symbols import sky_cover,current_weather
from metpy.units import units
from scipy.constants.constants import C2F

# function for converting cloud cover code to oktas
def get_cloud_cover(code):

    if isinstance(code,float):
        return 0.0

    if 'OVC' in code:
        return 1.0
    elif 'BKN' in code:
        return 6.0/8.0
    elif 'SCT' in code:
        return 4.0/8.0
    elif 'FEW' in code:
        return 2.0/8.0
    else:
        return 0.0

# set up the METAR sites we want and the parameters
sites = pandas.read_csv('metarsites.txt',sep=' ',header=None)[0].tolist()
single_value_params = ["timeObs", "stationName", "longitude", "latitude",
                       "temperature", "dewpoint", "windDir",
                       "windSpeed", "seaLevelPress"]
multi_value_params = ["presWeather", "skyCover", "skyLayerBase"]
all_params = single_value_params + multi_value_params
obs_dict = dict({all_params: [] for all_params in all_params})
pres_weather = []
sky_cov = []
sky_layer_base = []

# get the valid time: we get a two-hour buffer since the EDEX can be flakey
lastHourDateTime = datetime.utcnow() - timedelta(hours = 2)
endHourDateTime = datetime.utcnow() - timedelta(hours = 1)
start = lastHourDateTime.strftime('%Y-%m-%d %H')
end = endHourDateTime.strftime('%Y-%m-%d %H')
beginRange = datetime.strptime( start + ":00:00", "%Y-%m-%d %H:%M:%S")
endRange = datetime.strptime( end + ":59:59", "%Y-%m-%d %H:%M:%S")
timerange = TimeRange(beginRange, endRange)

# request observations from the UCAR EDEX server
DataAccessLayer.changeEDEXHost("edex-cloud.unidata.ucar.edu")
request = DataAccessLayer.newDataRequest()
request.setDatatype("obs")
request.setParameters(*(all_params))
request.setLocationNames(*(sites))
response = DataAccessLayer.getGeometryData(request,timerange)

for ob in response:
    # get the available parameter in each observation
    avail_params = ob.getParameters()
    if 'presWeather' in avail_params:
        pres_weather.append(ob.getString('presWeather'))
    elif 'skyCover' in avail_params:
        sky_cov.append(ob.getString('skyCover'))
        sky_layer_base.append(ob.getNumber('skyLayerBase'))
    else:
        for param in single_value_params:
            if param in avail_params:
                if param == 'timeObs':
                    obs_dict[param].append(datetime.fromtimestamp(ob.getNumber(param)/1000.0))
                else:
                    try:
                        obs_dict[param].append(ob.getNumber(param))
                    except TypeError:
                        obs_dict[param].append(ob.getString(param))
            else:
                obs_dict[param].append(None)

        obs_dict['presWeather'].append(pres_weather)
        obs_dict['skyCover'].append(sky_cov)
        obs_dict['skyLayerBase'].append(sky_layer_base)
        pres_weather = []
        sky_cov = []
        sky_layer_base = []

# get the most recent observation for each station
df = pandas.DataFrame(data=obs_dict,columns=all_params).sort_values(by='timeObs',ascending=False)
# group rows by station
groups = df.groupby('stationName')
# create a new dataframe for the most recent observation at each station
df_recent = pandas.DataFrame(columns=all_params)
for rid,station in groups:
    row = station.head(1)
    df_recent = pandas.concat([df_recent,row])

# filter missing windspeeds
for ix,val in enumerate(df_recent['windSpeed']):
    if val == -9999:
        df_recent.set_value(ix,'windSpeed',0.0)

# convert dataframe to something metpy-readable by attaching units and calculating derived values
data = dict()
data['stid'] = np.array(df_recent['stationName'])                           # station ID
data['latitude'] = np.array(df_recent['latitude'])                          # station latitude
data['longitude'] = np.array(df_recent['longitude'])                        # station longitude
data['air_temperature'] = C2F(np.array(df_recent['temperature'],\
    dtype=float) * units.degF)                                              # air temperature
data['dew_point'] = C2F(np.array(df_recent['dewpoint'],\
    dtype=float) * units.degF)                                              # dewpoint temperature
data['slp'] = np.array(df_recent['seaLevelPress'],\
    dtype=float) * units('mbar')                                            # sea-level pressure
u,v = get_wind_components(np.array(df_recent['windSpeed']) * \
    units('knots'),np.array(df_recent['windDir']) * units.degree)           # wind speed/direction

# filter out missing winds
for ix,val in enumerate(u.magnitude):
    if abs(val) > 100.0:
        u.magnitude[ix] = 0.0

for ix,val in enumerate(v.magnitude):
    if abs(val) > 100.0:
        v.magnitude[ix] = 0.0

data['eastward_wind'],data['northward_wind'] = u,v
data['cloud_frac'] = [int(get_cloud_cover(x)*8) for x in df_recent['skyCover']]

# set up the basemap
proj = ccrs.LambertConformal(central_longitude=-99.0,central_latitude=31.5,\
    standard_parallels=[35])

# get some map features
state_boundaries = feat.NaturalEarthFeature(category='cultural',\
    name='admin_1_states_provinces_lines',scale='50m',facecolor="None")
land_50m = feat.NaturalEarthFeature('physical','land','50m',facecolor='None')
ocean_50m = feat.NaturalEarthFeature('physical','ocean','50m',facecolor='None')
borders_50m = feat.NaturalEarthFeature(category='cultural',name='admin_0_countries',\
    scale='50m',facecolor='None')

# set up the figure
plt.clf()
fig = plt.figure(figsize=(20,15))

# add the map features to the figure
ax = fig.add_subplot(1,1,1,projection=proj)
ax.add_feature(feat.LAKES, zorder=1,facecolor='cyan')
ax.add_feature(land_50m,zorder=0,facecolor='gray')
ax.add_feature(ocean_50m,zorder=-1,facecolor='cyan')
ax.coastlines(resolution='50m', zorder=2, color='black')
ax.add_feature(state_boundaries, zorder=3,color='black')
ax.add_feature(borders_50m,zorder=4,color='black')
ax.set_extent((-110, -88, 25, 38))

# create the station plots
stationplot = StationPlot(ax,data['longitude'],data['latitude'],transform=ccrs.PlateCarree(),\
    fontsize=9)
simple_layout.plot(stationplot,data)

# station plot aesthetics
stationplot.plot_parameter('NW', np.array(data['air_temperature']), color='red')
stationplot.plot_parameter('SW', np.array(data['dew_point']), color='darkgreen')
stationplot.plot_parameter('NE', np.array(data['slp']),
                           formatter=lambda v: format(10 * v, '.0f')[-3:])
stationplot.plot_symbol('C', data['cloud_frac'], sky_cover)
stationplot.plot_text((2, 0), np.array(data['stid']))

# save the figure
plt.title("METAR Observations valid %s00 UTC" % end)
plt.savefig("plot.png",bbox_inches='tight')
