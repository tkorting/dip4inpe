
def total_zero(x):
    # plt.figure(), plt.imshow(x), plt.colorbar(), plt.title('total_zero'), plt.show();
    x_valid = x.compressed()
    if x_valid.size == 0:
        return 0
    return int(np.sum(x_valid == 0))

from rasterstats import zonal_stats
import geopandas as gpd
from rasterio.transform import Affine
def nodata_free_crop(raster_path, aoi, verbose = False, max_nodata_cover = 0.2, sampling_factor = 1.0):
    with rio.open(raster_path) as raster:
        rows = int(raster.height * sampling_factor)
        columns = int(raster.width * sampling_factor)
        transform = raster.transform * Affine.scale(1/sampling_factor)
        raster_extent = [raster.bounds.left, raster.bounds.right, raster.bounds.bottom, raster.bounds.top]
        first_band = raster.read(1, out_shape=(rows, columns)).astype(np.float32)
    stats = zonal_stats(aoi, first_band, affine=transform, nodata=-1, stats=None, add_stats={'total_zero': total_zero})
    neta = 0.000001
    nodata_ratio = stats[0]['total_zero']/(stats[0]['count'] + neta)
    if verbose:
        x, y = aoi.exterior.xy
        plt.figure(figsize=(5,5)), plt.imshow(first_band, extent = raster_extent, origin = "upper"), plt.plot(x, y, color="red", linewidth=2), plt.title('nodata_free_crop(first band)'), plt.show();
        print(stats)
        print('amount of nodata detected:', nodata_ratio)
    if nodata_ratio > max_nodata_cover:
        return False
    return True

def total_clouds(x):
    # plt.figure(), plt.imshow(x), plt.colorbar(), plt.title('total_clouds'), plt.show();
    x_valid = x.compressed()
    if x_valid.size == 0:
        return 0
    return int(np.sum(x_valid == True))

import matplotlib.pyplot as plt
from rasterio.transform import Affine
def cloud_free_crop(raster_path, aoi, max_cloud_cover = 0.4, method = 'omni', sampling_factor = 1.0, verbose = False):
    if method == 'omni':
        cloud_mask = get_omni_cloud_mask(raster_path, sampling_factor = sampling_factor, verbose = verbose)    
    else:
        cloud_mask = get_cloud_mask(raster_path, sampling_factor = sampling_factor, verbose = verbose)
    with rio.open(raster_path) as raster:
        transform = raster.transform * Affine.scale(1/sampling_factor)
        stats = zonal_stats(aoi, cloud_mask, affine=transform, nodata=-1, stats=None, add_stats={'total_clouds': total_clouds})
        neta = 0.000001
        cloud_ratio = stats[0]['total_clouds']/(stats[0]['count'] + neta)
        if verbose:
            print(stats)
            print('amount of clouds detected:', cloud_ratio)
        # in some cases all metrics are returning None values
        if stats[0]['min'] == None and stats[0]['max'] == None:
            return False
        if cloud_ratio > max_cloud_cover:
            return False
    return True
    
import numpy as np
import rasterio as rio
from .calibration import get_acc
def get_all_assets(raster_path, sampling_factor = 1.0):
    xml_path = raster_path[:-4] + '.xml'
    acc = get_acc(xml_path)
    with rio.open(raster_path) as src:
        rows = int(src.height * sampling_factor)
        columns = int(src.width * sampling_factor)
        if 'PAN' in raster_path or 'pan' in raster_path or len(src.indexes) < 4:
            green = src.read(1, out_shape=(rows, columns)).astype(np.float32) * acc['green']
            red = src.read(2, out_shape=(rows, columns)).astype(np.float32) * acc['red']
            nir = src.read(3, out_shape=(rows, columns)).astype(np.float32) * acc['nir']
            blue = np.zeros_like(green)
        else:
            blue = src.read(1, out_shape=(rows, columns)).astype(np.float32) * acc['blue']
            green = src.read(2, out_shape=(rows, columns)).astype(np.float32) * acc['green']
            red = src.read(3, out_shape=(rows, columns)).astype(np.float32) * acc['red']
            nir = src.read(4, out_shape=(rows, columns)).astype(np.float32) * acc['nir']
    blue[blue < 0] = 0.0
    green[green < 0] = 0.0
    red[red < 0] = 0.0
    nir[nir < 0] = 0.0
    neta = 0.00001
    ndvi = (nir - red) / (nir + red + neta)
    ndwi = (green - nir) / (green + nir + neta)
    bright = blue + green + red + nir    
    return blue, green, red, nir, ndvi, ndwi, bright

import numpy as np
import omnicloudmask
def get_omni_cloud_mask(raster_path, sampling_factor = 1.0, verbose = False):
    '''
    Return binary cloud mask for each pixel
    
    parameters
    ----------
    raster_path: string with full path of input raster
    sampling_factor: float from 0.1 to 1.0, to use 10% to 100% of pixels
    verbose: boolean to print details when True
    
    return
    ------
    boolean matrix, where each pixel is:
    False -> no cloud
    True -> cloud
    '''
    _, green, red, nir, _, _, _ = get_all_assets(raster_path, sampling_factor)
    input_array = np.stack([red, green, nir], axis=0)
    cloud_mask = omnicloudmask.predict_from_array(input_array, inference_device='cpu')
    return (cloud_mask[0] > 0)

import numpy as np
from scipy.ndimage import binary_dilation
def get_cloud_mask(raster_path, threshold_ndwi = -0.12, percentile_bright = 75, sampling_factor = 1.0, verbose = False):
    '''
    Return binary cloud mask for each pixel
    
    parameters
    ----------
    raster_path: string with full path of input raster
    threshold_ndwi: float from -1.0 to 1.0, applied to ndwi as threshold for clouds
    percentile_bright: int from 0 to 100 indicating amount of brightness to consider as clouds
    sampling_factor: float from 0.1 to 1.0, to use 10% to 100% of pixels
    verbose: boolean to print details when True
    
    return
    ------
    boolean matrix, where each pixel is:
    False -> no cloud
    True -> cloud
    '''    
    L = 10
    mean_threshold = 2**L * 0.1
    if 'PAN' in raster_path or 'pan' in raster_path or 'MUX' in raster_path or 'mux' in raster_path:
        L = 8
        mean_threshold = 2**L * 0.45
    elif 'WFI' in raster_path or 'wfi' in raster_path:
        mean_threshold = 2**L * 0.15 # 0.09
    elif 'WPM' in raster_path or 'wpm' in raster_path:
        mean_threshold = 2**L * 0.18
    blue, green, red, _, _, ndwi, bright = get_all_assets(raster_path, sampling_factor)
    threshold_bright = 0
    if bright.size > 0:
        threshold_bright = np.percentile(bright, percentile_bright)
    cloud_mask = (green > mean_threshold) & (ndwi > threshold_ndwi) & (bright >= threshold_bright)
    structure = np.ones((3, 3), dtype=bool)
    cloud_mask_dilation = binary_dilation(cloud_mask, structure=structure, iterations=1)
    
    cloud_mask_dilation_float = cloud_mask_dilation.astype(np.float32)
    cloud_mask_dilation_float[green == 0] = 0
    cloud_mask_dilation_float[cloud_mask_dilation == False] = 0
    cloud_mask_dilation_float[cloud_mask == True] = 1
    if verbose:
        nodata = 0
        rows, columns = green.shape
        matrix_rgb = np.zeros((rows, columns, 3))
        matrix_rgb[:, :, 0] = red / (red.max() if red.max() != 0 else 1.0)
        matrix_rgb[:, :, 1] = green / (green.max() if green.max() != 0 else 1.0)
        matrix_rgb[:, :, 2] = blue / (blue.max() if blue.max() != 0 else 1.0)
    
        plt.figure(figsize=(12, 6))
        plt.subplot(3, 4, 1), plt.imshow(green), plt.title('green'), plt.colorbar()
        plt.subplot(3, 4, 2), plt.imshow(ndwi, vmin=-1, vmax=1), plt.title('ndwi'), plt.colorbar()
        plt.subplot(3, 4, 3), plt.imshow(bright), plt.title('bright'), plt.colorbar()
        plt.subplot(3, 4, 4), plt.imshow(matrix_rgb), plt.title('true color')
        plt.subplot(3, 4, 5), plt.hist(green[green != nodata].flatten(), bins=100)
        plt.subplot(3, 4, 6), plt.hist(ndwi[ndwi != nodata].flatten(), bins=100)
        plt.subplot(3, 4, 7), plt.hist(bright[bright != nodata].flatten(), bins=100)
        plt.subplot(3, 4, 9), plt.imshow((green > mean_threshold)), plt.title(f'green > {mean_threshold}'), plt.colorbar()
        plt.subplot(3, 4, 10), plt.imshow((ndwi > threshold_ndwi)), plt.title(f'ndwi > {threshold_ndwi}'), plt.colorbar()
        plt.subplot(3, 4, 11), plt.imshow((bright > threshold_bright)), plt.title(f'bright > {threshold_bright}'), plt.colorbar()
        plt.subplot(3, 4, 12), plt.imshow(cloud_mask_dilation_float), plt.title(f'cloud_mask_dilation_float'), plt.colorbar()
        plt.tight_layout()
        plt.show();
    return cloud_mask_dilation_float
    
import os
import geopandas as gpd
from rasterio.mask import mask
from shapely.geometry import mapping, box
from rasterio.enums import Resampling
from rasterio.windows import from_bounds
def crop_band(band_path, output_band_path, aoi, aoi_crs, only_box = False, sampling_factor = 1.0, verbose = False):
    '''
    Return GeoTIFF cropped by Area of Interes
    
    parameters
    ----------
    band_path: string with full path of input raster single band
    output_band_path: string with full path of output raster single band (resultant crop)
    aoi: string with full path to KML with Area of Interest (AoI)
    aoi_crs: string with EPSG from AOI
    only_box: boolean indicating to produce raster only inside bounding box of aoi
    sampling_factor: float from 0.1 to 1.0, to use 10% to 100% of pixels
    verbose: boolean to print details when True
    
    return
    ------
    boolean indicating Success when True
    '''
    if os.path.exists(band_path) == False:
        print('# path does not exist for crop_band', band_path) 
        return False
    with rio.open(band_path) as src:
        aoi_gdf = gpd.GeoDataFrame({"geometry": [aoi]}, crs=aoi_crs).to_crs(src.crs)
        if only_box:
            raster_box = box(*src.bounds)
            aoi_box = box(*aoi_gdf.total_bounds)
            crop_box = aoi_box.intersection(raster_box)
            if crop_box.is_empty:
                print('# AOI outside image')
                return False            
            # bounds = aoi_gdf.total_bounds
            bounds = crop_box.bounds
            window = from_bounds(*bounds, transform=src.transform)
            window = window.round_offsets().round_lengths()
            out_image = src.read(window=window)
            out_transform = src.window_transform(window)
        else:
            out_image, out_transform = mask(src, [mapping(aoi_gdf.iloc[0].geometry)], crop=True)
        try:
          out_meta = src.meta.copy()
          out_meta.update({
            'height': out_image.shape[1],
            'width': out_image.shape[2],
            'nodata': 0,
            'transform': out_transform
          })
          with rio.open(output_band_path, 'w', **out_meta) as dest:
              dest.write(out_image)
        except Exception as e:
          print(f'# error in crop for crop_band {e}', band_path)
          return False
    return True

import os
def merge_or_pansharpen_bands(bands_list, output_raster_path, verbose = False):
    '''
    Apply gdal merge, or gdal pansharpening in ordered list of bands
    For pansharpening, the first band is considered panchromatic
    All bands are considered to be registered
    
    parameters
    ----------
    bands_list: list of strings containing full path of input bands
    output_raster_path: string with full path of output merged/pansharpened raster
    verbose: boolean to print details when True
    
    return
    ------
    boolean indicating Success when True
    '''
    for band_path in bands_list:
        if os.path.exists(band_path) == False:
            return False
    bands_list_string = ' '.join(bands_list)
    # this part is required to avoid minor alignment of rasters for pansharpening
    if 'wpm' in bands_list_string.lower() or 'pan' in bands_list_string.lower():
        if 'wpm' in bands_list_string.lower() and len(bands_list) != 5:
            print('# error in number of bands, the list is', bands_list_string)
            return False
        with rio.open(bands_list[0]) as src:
            xmin, ymin, xmax, ymax = src.bounds
            for j in range(1, 5):
                cmd = f'gdal_edit.py -a_ullr {xmin} {ymax} {xmax} {ymin} {bands_list[j]}'
                if verbose:
                    print('>', cmd)
                os.system(cmd)
    if 'wpm' in bands_list_string.lower():
        if len(bands_list) != 5:
            print('# error in number of bands')
            return False
        # testing new weights for WPM, giving extra influence for nir
        weights = '-w 0.15 -w 0.15 -w 0.25 -w 0.45'
        cmd = f'gdal_pansharpen.py {bands_list[0]} {weights} -b 1 -b 2 -b 3 -b 4 {bands_list[1]} {bands_list[2]} {bands_list[3]} {bands_list[4]} {output_raster_path}; gdal_edit.py -colorinterp_1 blue -colorinterp_2 green -colorinterp_3 red -colorinterp_4 undefined -a_nodata 0 {output_raster_path}'
    elif 'pan' in bands_list_string.lower():
        if len(bands_list) != 4:
            print('# error in number of bands')
            return False
        cmd = f'gdal_pansharpen.py {bands_list[0]} -b 1 -b 2 -b 3 {bands_list[1]} {bands_list[2]} {bands_list[3]} {output_raster_path}; gdal_edit.py -colorinterp_1 green -colorinterp_2 red -colorinterp_3 undefined -a_nodata 0 {output_raster_path}'
    elif 'mux' in bands_list_string.lower() or 'wfi' in bands_list_string.lower():
        if len(bands_list) != 4:
            print('# error in number of bands')
            return False
        cmd = f'gdal_merge.py -n 0 -a_nodata 0 -o {output_raster_path} -separate {bands_list[0]} {bands_list[1]} {bands_list[2]} {bands_list[3]}; gdal_edit.py -colorinterp_1 blue -colorinterp_2 green -colorinterp_3 red -colorinterp_4 undefined -a_nodata 0 {output_raster_path}'
    if verbose:
        print('>', cmd)
    os.system(cmd)
    return True


