#
# Copyright The NOMAD Authors.
#
# This file is part of NOMAD. See https://nomad-lab.eu for further info.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import os
import xml.etree.ElementTree as ET
from typing import (
    Dict,
    Any,
)
import numpy as np
from structlog.stdlib import (
    BoundLogger,
)
from nomad.units import ureg
from nomad_measurements.xrd.IKZ import RASXfile


def read_panalytical_xrdml(file_path: str, logger: BoundLogger=None) -> Dict[str, Any]:
    '''
    Function for reading the X-ray diffraction data in a Panalytical `.xrdml` file.

    Args:
        file_path (str): The path to the `.xrdml` file.
        logger (BoundLogger): A structlog logger.

    Returns:
        Dict[str, Any]: The X-ray diffraction data in a Python dictionary.
    '''
    with open(file_path, 'r', encoding='utf-8') as file:
        element_tree = ET.parse(file)
    root = element_tree.getroot()
    ns_version = root.tag.split('}')[0].strip('{')
    ns = {'xrdml': ns_version}

    def find_float(path):
        result = root.find(path, ns)
        if result is not None:
            unit = result.get('unit', '')
            if unit == 'Angstrom':
                unit = 'angstrom'
            return float(result.text) * ureg(unit)
        return None

    def find_string(path):
        result = root.find(path, ns)
        if result is not None:
            return result.text
        return None

    xrd_measurement = root.find('xrdml:xrdMeasurement', ns)
    scans = xrd_measurement.findall('xrdml:scan', ns)
    if len(scans) > 1 and logger is not None:
        logger.warning(
            'Multi scan xrdml files are currently not supported. Only reading first scan.'
        )
    scan = scans[0]  # TODO: Implement multi-scan

    data_points = scan.find('xrdml:dataPoints', ns)
    intensities = data_points.find('xrdml:intensities', ns)
    counting_time = data_points.find('xrdml:commonCountingTime', ns)
    attenuation = data_points.find('xrdml:beamAttenuationFactors', ns)

    counting_time_value = (
        np.fromstring(counting_time.text, sep=' ') * ureg(counting_time.get('unit'))
    )
    if attenuation is not None:
        attenuation_values = np.fromstring(attenuation.text, sep=' ')
        scaling_factor = attenuation_values
    else:
        attenuation_values = None
        scaling_factor = 1
    if intensities is not None:
        intensities_array = (
            np.fromstring(intensities.text, sep=' ')
        )
        counts_array = None
    else:
        counts = data_points.find('xrdml:counts', ns)
        counts_array = np.fromstring(counts.text, sep=' ')
        intensities_array = (
            counts_array * scaling_factor
        )
    n_points = len(intensities_array)

    axes = {}
    for axis in data_points.findall('xrdml:positions', ns):
        name = axis.get('axis')
        unit = axis.get('unit')
        listed = axis.find('xrdml:listPositions', ns)
        start = axis.find('xrdml:startPosition', ns)
        end = axis.find('xrdml:endPosition', ns)
        common = axis.find('xrdml:commonPosition', ns)
        if listed is not None:
            axes[name] = np.fromstring(listed.text, sep=' ') * ureg(unit)
        elif start is not None and end is not None:
            axes[name] = np.linspace(
                float(start.text), float(end.text), n_points
            ) * ureg(unit)
        elif common is not None:
            axes[name] = np.array([float(common.text)]) * ureg(unit)
        else:
            if logger is not None:
                logger.warning('Unknown data for {name} axis.')
            axes[name] = None

    return {
        'countTime': counting_time_value,
        'detector': intensities_array,
        'counts': counts_array,
        'beamAttenuationFactors': attenuation_values,
        **axes,
        'scanmotname': scan.get('scanAxis', None),
        'metadata': {
            'sample_id': find_string('xrdml:sample/xrdml:id'),
            'measurement_type': xrd_measurement.get('measurementType', None),
            'sample_mode': xrd_measurement.get('sampleMode', None),
            'source': {
                'current': find_float(
                    'xrdml:xrdMeasurement/xrdml:incidentBeamPath/xrdml:xRayTube'
                    '/xrdml:current'
                ),
                'voltage': find_float(
                    'xrdml:xrdMeasurement/xrdml:incidentBeamPath/xrdml:xRayTube'
                    '/xrdml:tension'
                ),
                'kAlpha1': find_float(
                    'xrdml:xrdMeasurement/xrdml:usedWavelength/xrdml:kAlpha1'
                ),
                'kAlpha2': find_float(
                    'xrdml:xrdMeasurement/xrdml:usedWavelength/xrdml:kAlpha2'
                ),
                'kBeta': find_float(
                    'xrdml:xrdMeasurement/xrdml:usedWavelength/xrdml:kBeta'
                ),
                'ratioKAlpha2KAlpha1': find_float(
                    'xrdml:xrdMeasurement/xrdml:usedWavelength/xrdml:ratioKAlpha2KAlpha1'
                ),
                'anode_material': find_string(
                    'xrdml:xrdMeasurement/xrdml:incidentBeamPath/xrdml:xRayTube'
                    '/xrdml:anodeMaterial'
                ),
            },
            'scan_mode': scan.get('mode', None),
            'scan_axis': scan.get('scanAxis', None),
        },
    }


def read_rigaku_rasx(file_path: str, logger: BoundLogger=None) -> Dict[str, Any]:
    '''
    Reads .rasx files from Rigaku instruments
        - reader is based on IKZ submodule
        - currently supports one scan per file
        - in case of multiple scans per file, only the first scan is read

    Args:
        file_path (string): absolute path of the file.
        logger (BoundLogger): A structlog logger for propagating errors and warnings.

    Returns:
        Dict[str, Any]: The X-ray diffraction data in a Python dictionary.
    '''
    reader = RASXfile(file_path, verbose=False)
    data_shape = reader.data.shape
    metainfo = reader.meta[0]
    p_data = reader.get_1d_scan()
    source = reader.get_source_info()

    if not data_shape[0] == 1:
        if logger is not None:
            logger.warning(
                '2D scan currently not supported. '
                'Taking the data from the first line scan.'
            )
        for key, data in p_data.items():
            if isinstance(data[0], np.ndarray) and data[0].ndim == 2:
                p_data[key][0] = data[0][0,:].squeeze()
                if len(np.unique(p_data[key][0])) == 1:
                    # shrinking duplicate data populated by `RASXFile`
                    first_val = p_data[key][0][0]
                    p_data[key][0] = np.array([first_val])

    count_time = None
    if metainfo['ScanInformation']['Mode'].lower() == 'continuous':
        speed_unit = ureg(
            metainfo['ScanInformation']['SpeedUnit'].replace('min','minute')
        )
        count_time_unit = ureg(metainfo['ScanInformation']['PositionUnit']) / speed_unit
        count_time = (
            metainfo['ScanInformation']['Step']
            / metainfo['ScanInformation']['Speed']
        )
        count_time = np.array([count_time]) * count_time_unit

    scan_axis = metainfo['ScanInformation']['AxisName']

    output = {
        'detector': (
            p_data['intensity'][0]
            if p_data['intensity'] else None
        ),
        '2Theta': (
            p_data[scan_axis][0] * ureg(p_data[scan_axis][1])
            if p_data[scan_axis] else None
        ),
        'Omega': (
            p_data['Omega_position'][0] * ureg(p_data['Omega_position'][1])
            if p_data['Omega_position'] else None
        ),
        'Chi': (
            p_data['Chi_position'][0] * ureg(p_data['Chi_position'][1])
            if p_data['Chi_position'] else None
        ),
        'Phi': (
            p_data['Phi_position'][0] * ureg(p_data['Phi_position'][1])
            if p_data['Phi_position'] else None
        ),
        'countTime': count_time,
        'metadata': {
            'sample_id': None,
            'scan_axis': scan_axis,
            'source': {
                'anode_material': (
                    source['TargetName'][0]
                    if source['TargetName'] else None
                ),
                'kAlpha1': (
                    source['WavelengthKalpha1'][0]
                    * ureg(source['WavelengthKalpha1'][1])
                    if source['WavelengthKalpha1'] else None
                ),
                'kAlpha2': (
                    source['WavelengthKalpha2'][0]
                    * ureg(source['WavelengthKalpha2'][1])
                    if source['WavelengthKalpha2'] else None
                ),
                'kBeta': (
                    source['WavelengthKbeta'][0]
                    * ureg(source['WavelengthKbeta'][1])
                    if source['WavelengthKbeta'] else None
                ),
                'voltage': (
                    source['Voltage'][0] * ureg(source['Voltage'][1])
                    if source['Voltage'] else None
                ),
                'current': (
                    source['Current'][0] * ureg(source['Current'][1])
                    if source['Current'] else None
                ),
                'ratioKAlpha2KAlpha1': None,
            },
        },
    }

    return output


def read_xrd(file_path: str, logger: BoundLogger) -> Dict[str, Any]:
    '''
    Function for reading an XRD file.

    Args:
        file_path (str): The path of the file to be read.
        logger (BoundLogger): A structlog logger.

    Returns:
        dict: The parsed and converted data in a common dictionary format.
    '''
    file_path = os.path.abspath(file_path)

    if file_path.endswith('.xrdml'):
        return read_panalytical_xrdml(file_path, logger)
    if file_path.endswith('.rasx'):
        return read_rigaku_rasx(file_path, logger)
    raise ValueError(f'Unsupported file format: {file_path.split(".")[-1]}')
