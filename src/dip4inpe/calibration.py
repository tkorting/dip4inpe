from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import warnings
import os
def get_acc(xml_path):
    warnings.filterwarnings('ignore', category = XMLParsedAsHTMLWarning)
    acc = {'pan':0.184471, 'blue':0.29107, 'green':0.297832, 'red':0.232504, 'nir':0.178993} # based on WPM   
    if os.path.exists(xml_path) == False:
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
    # force application of extra acc
    if 'MUX' in satellite or 'WPM' in satellite:
        for band in acc:
            acc[band] *= 1.45
    return acc
