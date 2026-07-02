import os
def get_raster_info_from_name(raster_path, separator='_'):
    file_parts = os.path.basename(raster_path).split(separator)
    raster_info = {
        'satellite_name': file_parts[0],
        'satellite_number': file_parts[1],
        'sensor_name': file_parts[2],
        'acquisition_date': file_parts[3],
        'path': file_parts[4],
        'row': file_parts[5],
        'processing_level': file_parts[6],
        'extra': file_parts[7],
        'band_number': file_parts[-1].split('.')[0]
    }
    return raster_info

from datetime import datetime
def get_raster_description(raster_path, language='pt', separator='_'):
    raster_info = get_raster_info_from_name(raster_path, separator)
    date = datetime.strptime(raster_info['acquisition_date'], '%Y%m%d')
    if language == 'en':
        return f"Image acquired in {date.strftime('%Y/%m/%d')} from satellite {raster_info['satellite_name']}-{raster_info['satellite_number']}, using sensor {raster_info['sensor_name']}."
    elif language == 'pt':
        meses = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
        data = f"{date.day:02d}/{meses[date.month - 1]}/{date.year}"
        return f"{data}, satélite {raster_info['satellite_name']}-{raster_info['satellite_number']}, sensor {raster_info['sensor_name']}"

import rasterio as rio
def get_number_of_pixels(raster_path):
    with rio.open(raster_path) as raster:
        return raster.height * raster.width

import math
def get_spatial_resolution_in_meters(raster_name):
    with rio.open(raster_name) as raster:
        if raster.crs.is_geographic:
            lat_center = (raster.bounds.top + raster.bounds.bottom) / 2
            # 1 degree latitude ~= 111.32 km
            return abs(raster.transform[0]) * 111320.0
        else:
            return raster.transform[0]
