"""
Author: Riley Hales, 2018
Copyright: Riley Hales, RCH Engineering, 2019
Description: Functions for generating timeseries and simple statistical
    charts for netCDF data for point, bounding box, or shapefile geometries
"""
import calendar
import datetime
import os
import shutil
import requests
import json

import rasterio
import rasterstats
import shapefile
import netCDF4
import numpy
import pandas
import statistics

from .options import gldas_variables
from .app import Gldas as App


def newchart(data):
    """
    Determines the environment for generating a timeseries chart. Call this function
    """
    # input parameters
    var = str(data['variable'])
    loc_type = data['loc_type']

    # list the netcdfs to be processed
    path = App.get_custom_setting('thredds_path')
    path = os.path.join(path, 'raw')
    allfiles = os.listdir(path)
    files = [nc for nc in allfiles if nc.endswith('.nc4')]
    if data['time'] != 'alltimes':
        yearfilter = 'A' + data['time'][0:3]
        files = [i for i in files if yearfilter in i]
    files.sort()

    # some metadata
    for item in gldas_variables():
        if item[1] == data['variable']:
            name = item[0]
            break

    # get the timeseries, units, and message based on location type
    if loc_type == 'Point':
        values, units = pointchart(var, data['coords'], path, files)
        type_message = 'Values at a Point'
    elif loc_type == 'Polygon':
        values, units = polychart(var, data['coords'], path, files)
        type_message = 'In a Bounding Box'
    elif loc_type == 'VectorGeometry':
        vectordata = data['vectordata']
        values, units = vectorchart(var, path, files, vectordata, data['instance_id'])
        if vectordata == 'customshape':
            type_message = 'Average in user\'s shapefile'
        else:
            if vectordata.startswith('esri-'):
                vectordata = vectordata.split('-')[-1]
            type_message = 'Average for ' + vectordata
    values.sort(key=lambda tup: tup[0])

    multiline, boxplot, categories = makestatplots(values, data['time'])
    return {
        'values': values,
        'multiline': multiline,
        'boxplot': boxplot,
        'categories': categories,
        'units': units,
        'variable': var,
        'type': type_message,
        'name': name
    }


def geojson_to_shape(vectordata, savepath):
    # get the geojson data from esri
    base = 'https://services.arcgis.com/P3ePLMYs2RVChkJx/ArcGIS/rest/services/'
    if vectordata.startswith('regions-'):
        vectordata = vectordata.replace('regions-', '')
        url = base + 'World_Regions/FeatureServer/0/query?f=pgeojson&outSR=4326&where=REGION+%3D+%27' + \
            vectordata + '%27'
    else:  # vectordata.startswith('countries-'):
        vectordata = vectordata.replace('countries-', '')
        url = base + 'World__Countries_Generalized_analysis_trim/FeatureServer/0/query?f=pgeojson&outSR=4326&' \
                     'where=NAME+%3D+%27' + vectordata + '%27'

    req = requests.get(url=url)
    geojson = json.loads(req.text)

    # create the shapefile
    fileobject = shapefile.Writer(target=savepath, shpType=shapefile.POLYGON, autoBalance=True)

    # label all the columns in the .dbf
    geomtype = geojson['features'][0]['geometry']['type']
    if geojson['features'][0]['properties']:
        for attribute in geojson['features'][0]['properties']:
            fileobject.field(str(attribute), 'C', '30')
    else:
        fileobject.field('Name', 'C', '50')

    # add the geometry and attribute data
    for feature in geojson['features']:
        if geomtype == 'Polygon':
            fileobject.poly(polys=feature['geometry']['coordinates'])
        elif geomtype == 'MultiPolygon':
            for i in feature['geometry']['coordinates']:
                fileobject.poly(polys=i)
        if feature['properties']:
            fileobject.record(**feature['properties'])
        else:
            fileobject.record(vectordata)

    # create a prj file
    with open(savepath + '.prj', 'w') as prj:
        prj.write('GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],'
                  'PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]]')

    fileobject.close()
    return


def pointchart(var, coords, path, files):
    # return items
    values = []

    # get a list of the lat/lon and units using a reference file
    nc_obj = netCDF4.Dataset(os.path.join(path, files[0]), 'r')
    nc_lons = nc_obj['lon'][:]
    nc_lats = nc_obj['lat'][:]
    units = nc_obj[var].__dict__['units']
    # get the index number of the lat/lon for the point
    lon_indx = (numpy.abs(nc_lons - round(float(coords[0]), 2))).argmin()
    lat_indx = (numpy.abs(nc_lats - round(float(coords[1]), 2))).argmin()
    nc_obj.close()

    # extract values at each timestep
    for nc in files:
        # get the time value for each file
        nc_obj = netCDF4.Dataset(os.path.join(path, nc), 'r')
        time = nc_obj['time'].__dict__['begin_date']
        time = datetime.datetime.strptime(time, "%Y%m%d")
        # slice the array at the area you want
        val = float(nc_obj[var][0, lat_indx, lon_indx].data)
        values.append((calendar.timegm(time.utctimetuple()) * 1000, val, time.month, time.year))
        nc_obj.close()

    return values, units


def polychart(var, coords, path, files):
    # return items
    values = []

    # get a list of the latitudes and longitudes and the units
    nc_obj = netCDF4.Dataset(os.path.join(path, str(files[0])), 'r')
    nc_lons = nc_obj['lon'][:]
    nc_lats = nc_obj['lat'][:]
    units = nc_obj[var].__dict__['units']
    # get a bounding box of the rectangle in terms of the index number of their lat/lons
    minlon = (numpy.abs(nc_lons - round(float(coords[0][1][0]), 2))).argmin()
    maxlon = (numpy.abs(nc_lons - round(float(coords[0][3][0]), 2))).argmin()
    maxlat = (numpy.abs(nc_lats - round(float(coords[0][1][1]), 2))).argmin()
    minlat = (numpy.abs(nc_lats - round(float(coords[0][3][1]), 2))).argmin()
    nc_obj.close()

    # extract values at each timestep
    for nc in files:
        # set the time value for each file
        nc_obj = netCDF4.Dataset(os.path.join(path, nc), 'r')
        time = nc_obj['time'].__dict__['begin_date']
        time = datetime.datetime.strptime(time, "%Y%m%d")
        # slice the array, drop nan values, get the mean, append to list of values
        array = nc_obj[var][0, minlat:maxlat, minlon:maxlon].data
        array[array < -5000] = numpy.nan  # If you have fill values, change the comparator to git rid of it
        array = array.flatten()
        array = array[~numpy.isnan(array)]
        values.append((calendar.timegm(time.utctimetuple()) * 1000, float(array.mean()), time.month, time.year))

        nc_obj.close()

    return values, units


def vectorchart(var, path, files, vectordata, instance_id=None):
    """
    Description: This script accepts a netcdf file in a geographic coordinate system, specifically the NASA GLDAS
        netcdfs, and extracts the data from one variable and the lat/lon steps to create a geotiff of that information.
    Dependencies: netCDF4, numpy, rasterio, rasterstats, os, shutil, calendar, datetime
    Params: View README.md
    Returns: Creates a geotiff named 'geotiff.tif' in the directory specified
    Author: Riley Hales, RCH Engineering, March 2019
    """
    # return items
    values = []

    # open the netcdf and get metadata
    nc_obj = netCDF4.Dataset(os.path.join(path, files[0]), 'r')
    lat = nc_obj.variables['lat'][:]
    lon = nc_obj.variables['lon'][:]
    units = nc_obj[var].__dict__['units']
    affine = rasterio.transform.from_origin(lon.min(), lat.max(), lat[1] - lat[0], lon[1] - lon[0])
    nc_obj.close()

    # file paths and settings
    if vectordata == 'customshape':
        dirpath = os.path.join(os.path.dirname(__file__), 'workspaces', 'user_workspaces', instance_id)
        shp = [i for i in os.listdir(dirpath) if i.endswith('.shp')]
        vectorpath = os.path.join(dirpath, shp[0])
    else:  # vectordata.startswith('esri-'):
        vectordata = vectordata.replace('esri-', '')
        dirpath = os.path.join(os.path.dirname(__file__), 'workspaces', 'user_workspaces', instance_id)
        if os.path.exists(dirpath):
            shutil.rmtree(dirpath)
        os.mkdir(dirpath)
        vectorpath = os.path.join(dirpath, instance_id)
        geojson_to_shape(vectordata, vectorpath)
        vectorpath += '.shp'

    # extract the timeseries by iterating over each netcdf
    for nc in files:
        # open the netcdf and get the data array
        nc_obj = netCDF4.Dataset(os.path.join(path, nc), 'r')
        time = nc_obj['time'].__dict__['begin_date']
        time = datetime.datetime.strptime(time, "%Y%m%d")

        var_data = nc_obj.variables[var][:]  # this is the array of values for the nc_obj
        array = numpy.asarray(var_data)[0, :, :]  # converting the data type
        array[array < -9000] = numpy.nan  # use the comparator to drop nodata fills
        array = array[::-1]  # vertically flip array so tiff orientation is right (you just have to, try it)

        stats = rasterstats.zonal_stats(vectorpath, array, affine=affine, nodata=numpy.nan, stats="mean")
        tmp = [i['mean'] for i in stats if i['mean'] is not None]
        values.append((calendar.timegm(time.utctimetuple()) * 1000, sum(tmp) / len(tmp), time.month, time.year))
    return values, units


def makestatplots(values, time):
    """
    Calculates statistics for the array of timeseries values and returns arrays for a highcharts boxplot
    """
    df = pandas.DataFrame(values, columns=['timestamp', 'values', 'month', 'year'])
    multiline = {'yearmulti': {'min': [], 'max': [], 'mean': []},
                 'monthmulti': {'min': [], 'max': [], 'mean': []}}
    boxplot = {'yearbox': [], 'monthbox': []}
    months = dict((n, m) for n, m in enumerate(calendar.month_name))

    if time == 'alltimes':
        ref_yr = 1948
        numyears = int(datetime.datetime.now().strftime("%Y")) - ref_yr + 1  # +1 because we want the first year also
    else:
        ref_yr = int(time.replace('s', ''))
        numyears = 10
    categories = {'month': [months[i + 1] for i in range(12)], 'year': [i + ref_yr for i in range(numyears)]}

    for i in range(1, 13):  # static 13 to go over months
        tmp = df[df['month'] == i]['values']
        std = statistics.stdev(tmp)
        median = statistics.median(tmp)
        ymin = min(tmp)
        ymax = max(tmp)
        mean = sum(tmp) / len(tmp)
        boxplot['monthbox'].append([months[i], ymin, mean - std, median, mean + std, ymax])
        multiline['monthmulti']['min'].append((months[i], ymin))
        multiline['monthmulti']['mean'].append((months[i], mean))
        multiline['monthmulti']['max'].append((months[i], ymax))
    for i, year in enumerate(categories['year']):
        tmp = df[df['year'] == year]['values']
        std = statistics.stdev(tmp)
        median = statistics.median(tmp)
        ymin = min(tmp)
        ymax = max(tmp)
        mean = sum(tmp) / len(tmp)
        boxplot['yearbox'].append([i, ymin, mean - std, median, mean + std, ymax])
        multiline['yearmulti']['min'].append((year, ymin))
        multiline['yearmulti']['mean'].append((year, mean))
        multiline['yearmulti']['max'].append((year, ymax))

    return multiline, boxplot, categories
