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
import xml.etree.ElementTree as ET
import collections
from typing import (
    Dict,
    Any,
    TYPE_CHECKING
)
import numpy as np
from nomad.units import ureg
# from pynxtools.dataconverter.convert import transfer_data_into_template
from nomad_measurements.utils import (
    to_pint_quantity,
    detect_scan_type,
    modify_scan_data,
)
from nomad_measurements.xrd.IKZ import RASXfile, BRMLfile

if TYPE_CHECKING:
    from structlog.stdlib import (
        BoundLogger,
    )


def transfer_data_into_template(**kwargs):
    raise NotImplementedError

def read_panalytical_xrdml(file_path: str, logger: 'BoundLogger'=None) -> Dict[str, Any]:
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

    axes = collections.defaultdict(list)
    counting_time_value = []
    attenuation_values = []
    intensities_array = []
    counts_array = []

    for scan in scans:
        data_points = scan.find('xrdml:dataPoints', ns)
        intensities = data_points.find('xrdml:intensities', ns)
        counting_time = data_points.find('xrdml:commonCountingTime', ns)
        attenuation = data_points.find('xrdml:beamAttenuationFactors', ns)

        counting_time_value.append(
            np.fromstring(counting_time.text, sep=' ') * ureg(counting_time.get('unit'))
        )
        if attenuation is not None:
            attenuation_values.append(
                np.fromstring(attenuation.text, sep=' ') * ureg.dimensionless
            )
            scaling_factor = attenuation_values[-1]
        else:
            attenuation_values = None
            scaling_factor = 1
        if intensities is not None:
            intensities_array.append(
                np.fromstring(intensities.text, sep=' ') * ureg.dimensionless
            )
            counts_array = None
        else:
            counts = data_points.find('xrdml:counts', ns)
            counts_array.append(np.fromstring(counts.text, sep=' ') * ureg.dimensionless)
            intensities_array.append(
                counts_array[-1] * scaling_factor * ureg.dimensionless
            )
        n_points = len(intensities_array[-1])

        for axis in data_points.findall('xrdml:positions', ns):
            name = axis.get('axis')
            unit = axis.get('unit')
            listed = axis.find('xrdml:listPositions', ns)
            start = axis.find('xrdml:startPosition', ns)
            end = axis.find('xrdml:endPosition', ns)
            common = axis.find('xrdml:commonPosition', ns)
            if listed is not None:
                axes[name].append(np.fromstring(listed.text, sep=' ') * ureg(unit))
            elif start is not None and end is not None:
                axes[name].append(
                    np.linspace(
                        float(start.text), float(end.text), n_points
                    ) * ureg(unit)
                )
            elif common is not None:
                axes[name].append(np.array([float(common.text)]) * ureg(unit))
            else:
                if logger is not None:
                    logger.warning('Unknown data for {name} axis.')
                axes[name].append(None)

    scan_data = collections.defaultdict(list)
    scan_data.update(axes)
    scan_data['intensity'] = intensities_array
    scan_data['counts'] = counts_array
    scan_data['countTime'] = counting_time_value
    scan_data['beamAttenuationFactors'] = attenuation_values

    scan_type = detect_scan_type(scan_data)
    modified_scan_data = modify_scan_data(scan_data, scan_type)

    return {
        **modified_scan_data,
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
            'scan_type': scan_type,
        },
    }


def read_rigaku_rasx(file_path: str, logger: 'BoundLogger'=None) -> Dict[str, Any]:
    '''
    Reads .rasx files from Rigaku instruments
        - reader is based on IKZ module

    Args:
        file_path (string): absolute path of the file.
        logger (BoundLogger): A structlog logger for propagating errors and warnings.

    Returns:
        Dict[str, Any]: The X-ray diffraction data in a Python dictionary.
    '''
    reader = RASXfile(file_path, verbose=False)
    scan_info = reader.get_scan_info()
    scan_data = reader.get_scan_data(logger)
    source = reader.get_source_info()

    scan_type = detect_scan_type(scan_data)
    modified_scan_data = modify_scan_data(scan_data, scan_type)

    count_time = None
    scan_axis = None

    if scan_info:
        required_keys = ['Mode','SpeedUnit','PositionUnit','Step', 'Speed']
        if all(key in scan_info and scan_info[key] for key in required_keys):
            if scan_info['Mode'].lower() == 'continuous':
                speed_unit = ureg(scan_info['SpeedUnit'].replace('min','minute'))
                count_time_unit = ureg(scan_info['PositionUnit']) / speed_unit
                count_time = (
                    np.array([scan_info['Step'] / scan_info['Speed']])
                    * count_time_unit
                )
        scan_axis = scan_info.get('AxisName', None)

    output = {
        'intensity': modified_scan_data['intensity'],
        '2Theta': modified_scan_data['2Theta'],
        'Omega': modified_scan_data['Omega'],
        'Chi': modified_scan_data['Chi'],
        'Phi': modified_scan_data['Phi'],
        'countTime': count_time,
        'metadata': {
            'sample_id': None,
            'scan_axis': scan_axis,
            'scan_type': scan_type,
            'source': {
                'anode_material': source['TargetName'],
                'kAlpha1': source['WavelengthKalpha1'],
                'kAlpha2': source['WavelengthKalpha2'],
                'kBeta': source['WavelengthKbeta'],
                'voltage': source['Voltage'],
                'current': source['Current'],
                'ratioKAlpha2KAlpha1': None,
            },
        },
    }

    return output

def read_bruker_brml(file_path: str, logger: 'BoundLogger'=None) -> Dict[str, Any]:
    '''
    Reads .brml files from Bruker instruments
        - reader is based on IKZ module

    Args:
        file_path (string): absolute path of the file.
        logger (BoundLogger): A structlog logger for propagating errors and warnings.

    Returns:
        Dict[str, Any]: The X-ray diffraction data in a Python dictionary.
    '''
    reader = BRMLfile(file_path, verbose=False)
    scan_info = reader.get_scan_info()
    source = reader.get_source_info()
    scan_data = reader.get_scan_data(logger)
    scan_type = detect_scan_type(scan_data)
    modified_scan_data = modify_scan_data(scan_data, scan_type)

    output = {
        'intensity': modified_scan_data['intensity'],
        '2Theta': modified_scan_data['2Theta'],
        'Omega': modified_scan_data['Theta'], # theta and omega are synonymous in .brml
        'Chi': modified_scan_data['Chi'],
        'Phi': modified_scan_data['Phi'],
        'countTime': None,
        'metadata': {
            'sample_id': None,
            'scan_axis': scan_info.get('ScanName', None),
            'scan_type': scan_type,
            'source': {
                'anode_material': source['TubeMaterial'],
                'kAlpha1': source['WaveLengthAlpha1'],
                'kAlpha2': source['WaveLengthAlpha2'],
                'kBeta': source['WaveLengthBeta'],
                'ratioKAlpha2KAlpha1': source['WaveLengthRatio'],
                'voltage': source['Voltage'],
                'current': source['Current'],
            },
        },
    }

    return output

def read_nexus_xrd(file_path: str, logger: 'BoundLogger'=None) -> Dict[str, Any]:
    '''
    Function for reading the X-ray diffraction data in a Nexus file.

    Args:
        file_path (str): The path to the X-ray diffraction data file.
        logger (BoundLogger, optional): A structlog logger. Defaults to None.

    Returns:
        Dict[str, Any]: The X-ray diffraction data in a Python dictionary.
    '''
    nxdl_name = 'NXxrd_pan'
    xrd_template = transfer_data_into_template(
        nxdl_name=nxdl_name,
        input_file=file_path,
        reader='xrd',
    )
    return xrd_template
