import numpy as np
from .utils import get_all_assets, get_cloud_mask
def get_true_color(raster_path, sampling_factor = 1.0, normalize = False):
    blue, green, red, nir, _, _, _ = get_all_assets(raster_path, sampling_factor)       
    rows, columns = green.shape
    print('rows, columns, sampling_factor', rows, columns, sampling_factor)
    matrix_rgb = np.zeros((rows, columns, 3))
    if 'PAN' in raster_path or 'pan' in raster_path:
        blue = green
        green = nir
    if red.size > 0 and green.size > 0 and blue.size > 0:
        matrix_rgb[:, :, 0] = red / (red.max() if red.max() != 0 else 1.0)
        matrix_rgb[:, :, 1] = green / (green.max() if green.max() != 0 else 1.0)
        matrix_rgb[:, :, 2] = blue / (blue.max() if blue.max() != 0 else 1.0)
        if normalize:
            nodata = 0
            cloud_mask = get_cloud_mask(raster_path, sampling_factor=sampling_factor)
            matrix_rgb[:, :, 0] = get_normalized_Np(red, nodata, cloud_mask)
            matrix_rgb[:, :, 1] = get_normalized_Np(green, nodata, cloud_mask)
            matrix_rgb[:, :, 2] = get_normalized_Np(blue, nodata, cloud_mask)
    return matrix_rgb

import numpy as np
def get_normalized_Np(matrix, nodata = 0, cloud_mask = None, N = 1):
    # compute percentiles 1% and 99% (or N% and [100-N]%)
    if cloud_mask is not None:
        useful_matrix = matrix[(cloud_mask == False) & (matrix != nodata)]
    else:
        useful_matrix = matrix[matrix != nodata]
    if useful_matrix.shape == (0,):
        p1 = matrix.flatten().min()
        p99 = matrix.flatten().max()
    else:
        p1 = np.percentile(useful_matrix, N)
        p99 = np.percentile(useful_matrix, 100 - N)
    new_matrix = matrix - p1
    if p1 != p99:
        new_matrix = new_matrix / (p99 - p1)
    new_matrix[new_matrix > 1.0] = 1.0
    new_matrix[new_matrix < 0.01] = 0.01
    new_matrix[matrix == nodata] = nodata
    return new_matrix
