import ast
import math
import os

import netCDF4
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from .model import app_configuration, gldas_variables
from .tools import nc_to_gtiff, rastermask_average_gdalwarp, pointchart, polychart


@login_required()
def get_bounds(request):
    """
    Dynamically defines exact boundaries for the legend and wms so that they are synchronized
    This was substituted for statically defined values to improve performance on the most common values.
    Will be reimplemented when the app supports custom time values
    Dependencies
        netcdf4, os, ast, math
        from .model import app_configuration
    """
    configs = app_configuration()
    thredds_data_dir = configs['thredds_data_dir']

    data = ast.literal_eval(request.body)
    variable = data['variable']
    time = data['time']
    response_object = {}

    if time == 'alltimes':
        path = os.path.join(thredds_data_dir, 'raw')
        files = os.listdir(path)
        files.sort()
    else:
        path = os.path.join(thredds_data_dir, 'raw')
        allfiles = os.listdir(path)
        files = [nc for nc in allfiles if nc.startswith("GLDAS_NOAH025_M.A" + str(time))]
        files.sort()

    minimum = 1000000
    maximum = -1000000
    for nc in files:
        dataset = netCDF4.Dataset(path + '/' + nc, 'r')
        data_dict = dataset[variable].__dict__
        if data_dict['vmax'] > maximum:
            maximum = data_dict['vmax']
        if data_dict['vmin'] < minimum:
            minimum = data_dict['vmin']

    response_object['minimum'] = math.floor(minimum)
    response_object['maximum'] = math.ceil(maximum)

    return JsonResponse(response_object)


@login_required()
def get_pointseries(request):
    """
    The controller for the ajax call to create a timeseries for the area chosen by the user's drawing
    Dependencies: gldas_variables (model), pointchart (tools), ast
    """
    data = ast.literal_eval(request.body.decode('utf-8'))
    response = {}
    response['units'], response['values'] = pointchart(data)
    response['type'] = '(Values at a Point)'

    variables = gldas_variables()
    for key in variables:
        if variables[key] == data['variable']:
            name = key
            response['name'] = name
            break
    return JsonResponse(response)


@login_required()
def get_polygonaverage(request):
    """
    Used to do averaging of a variable over a polygon of area, user drawn or a shapefile
    Dependencies: polychart (tools), gldas_variables (model), ast
    """
    response = {}
    data = ast.literal_eval(request.body.decode('utf-8'))
    response['units'], response['values'] = polychart(data)
    response['type'] = '(Averaged over a Polygon)'

    variables = gldas_variables()
    for key in variables:
        if variables[key] == data['variable']:
            name = key
            response['name'] = name
            break
    return JsonResponse(response)


@login_required()
def get_shapeaverage(request):
    """
    Used to do averaging of a variable over a polygon of area, user drawn or a shapefile
    Dependencies: nc_to_gtiff (tools), rastermask_average_gdalwarp (tools), gldas_variables (model), ast
    """
    response = {}
    data = ast.literal_eval(request.body.decode('utf-8'))
    data['times'], response['units'] = nc_to_gtiff(data)
    response['values'] = rastermask_average_gdalwarp(data)
    response['type'] = '(Average for ' + data['region'] + ')'

    variables = gldas_variables()
    for key in variables:
        if variables[key] == data['variable']:
            name = key
            response['name'] = name
            break
    return JsonResponse(response)


@login_required()
def customsettings(request):
    """
    returns the paths to the data/thredds services taken from the custom settings and gives it to the javascript
    Dependencies: app_configuration (model)
    """
    return JsonResponse(app_configuration())
