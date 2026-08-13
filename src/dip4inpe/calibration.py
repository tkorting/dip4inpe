from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from .metadata import get_raster_info_from_name
import warnings
import os
def get_acc(xml_path, force_xml = True, verbose = False):
    '''
    Obtain Absolute Calibration Coefficient (ACC) values from XML file
    
    parameters
    ----------
    xml_path: string with full path of XML file (in general same file name of GeoTIFF)
    force_xml: boolean to force using the ACC values from XML when True, or hard-coded values when False
    verbose: boolean to print details when True
    
    return
    ------
    dictionary where keys = (pan, blue, green, red, nir) and values = floats with corresponding ACC values
    '''
    warnings.filterwarnings('ignore', category = XMLParsedAsHTMLWarning)
    # CBERS-4A/WPM (default)
    acc = {'pan':0.184471, 'blue':0.29107, 'green':0.297832, 'red':0.232504, 'nir':0.178993}
    
    if os.path.exists(xml_path) == False:
        return acc
    if force_xml == False:
        metadata = get_raster_info_from_name(xml_path)
        instrument = metadata['satellite_name'] + '_' + 
                     metadata['satellite_number'] + '_' + 
                     metadata['sensor_name']
        if instrument == 'CBERS_4_AWFI':
            # CBERS-4/WFI (2026)
            acc = {'pan':0.0, 'blue':1.4351, 'green':1.4351, 'red':1.3903, 'nir':1.3903}
        elif instrument == 'CBERS_4A_WFI':
            # CBERS-4A/WFI (2026)
            acc = {'pan':0.0, 'blue':0.947982, 'green':0.965583, 'red':0.946315, 'nir':0.739644}
        elif instrument == 'AMAZONIA_1_WFI':
            # AMAZONIA-1/WFI (2026)
            acc = {'pan':0.0, 'blue':0.24, 'green':0.31, 'red':0.214, 'nir':0.185}
        elif instrument == 'CBERS_4_MUX':
            # CBERS-4/MUX (https://doi.org/10.3390/rs8050405)
            # First in-Flight Radiometric Calibration of MUX and WFI on-Board CBERS-4
            acc = {'pan':0.0, 'blue':1.68, 'green':1.62, 'red':1.59, 'nir':1.42}
        return acc
        
    xml_content = ''
    with open(xml_path, 'r', encoding='utf-8') as xml_file:
        xml_content = xml_file.read()
    soup = BeautifulSoup(xml_content, 'html.parser')
    node = soup.find('satellite')
    satellite = node.find('name').text + '_' + node.number.text + '_' + node.instrument.text
    calib_node = soup.find('absolutecalibrationcoefficient')
    band_names = {'CBERS_4A_WPM': {0: 'pan', 1: 'blue', 2: 'green', 3: 'red', 4: 'nir'},
                  'CBERS_4A_MUX': {5: 'blue', 6: 'green', 7: 'red', 8: 'nir'},
                  'CBERS_4A_WFI': {13: 'blue', 14: 'green', 15: 'red', 16: 'nir'},
                  'CBERS_4_PAN': {1: 'pan', 2: 'green', 3: 'red', 3: 'nir'},
                  'CBERS_4_PAN5M': {0: 'green', 1: 'red', 2: 'nir'}, # Charter
                  'CBERS_4_MUX': {5: 'blue', 6: 'green', 7: 'red', 8: 'nir'},
                  'CBERS_4_AWFI': {13: 'blue', 14: 'green', 15: 'red', 16: 'nir'},
                  'AMAZONIA_1_WFI': {1: 'blue', 2: 'green', 3: 'red', 4: 'nir'}
                 }
    if calib_node:
        for band in calib_node.find_all('band'):
            band_name = band_names[satellite]
            acc[band_name[int(band['name'])]] = float(band.text)

    return acc
