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
import os  # for file path operations
import xml.etree.ElementTree as ET # for XML parsing
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


class FileReader:
    '''A class to read files from a given file path.'''
    def __init__(self, file_path):
        '''
        Args:
            file_path (str): The path of the file to be read.
        '''
        self.file_path = file_path

    def read_file(self):
        '''Reads the content of a file from the given file path.

        Returns:
            str: The content of the file.
        '''
        with open(self.file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        return content


def read_xrdml(mainfile: str, logger: BoundLogger=None) -> Dict[str, Any]:
    '''
    Function for reading the X-ray diffraction data in a Panalytical `.xrdml` file. 

    Args:
        mainfile (str): The path to the `.xrdml` file.
        logger (BoundLogger): A structlog logger.

    Returns:
        Dict[str, Any]: The X-ray diffraction data in a Python dictionary.
    '''
    with open(mainfile, 'r', encoding='utf-8') as file:
        element_tree = ET.parse(file)
    root = element_tree.getroot()
    ns_version = root.tag.split("}")[0].strip("{")
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

    xrd_measurement = root.find("xrdml:xrdMeasurement", ns)
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
        _values = attenuation_values
    else:
        attenuation_values = None
        _values = 1
    if intensities is not None:
        intensities_array = (
            np.fromstring(intensities.text, sep=' ')
            # / counting_time_value.to('s').magnitude * ureg('cps')
        )
        counts_array = None
    else:
        counts = data_points.find('xrdml:counts', ns)
        counts_array = np.fromstring(counts.text, sep=' ')
        intensities_array = (
            counts_array * _values
            # / counting_time_value.to('s').magnitude * ureg('cps')
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
        "countTime": counting_time_value,
        "detector": intensities_array,
        "counts": counts_array,
        "beamAttenuationFactors": attenuation_values,
        **axes,
        "scanmotname": scan.get("scanAxis", None),
        "metadata": {
            "sample_id": find_string('xrdml:sample/xrdml:id'),
            "measurement_type": xrd_measurement.get("measurementType", None),
            "sample_mode": xrd_measurement.get("sampleMode", None),
            "source": {
                "current": find_float(
                    'xrdml:xrdMeasurement/xrdml:incidentBeamPath/xrdml:xRayTube'
                    '/xrdml:current'
                ),
                "voltage": find_float(
                    'xrdml:xrdMeasurement/xrdml:incidentBeamPath/xrdml:xRayTube'
                    '/xrdml:tension'
                ),
                "kAlpha1": find_float(
                    "xrdml:xrdMeasurement/xrdml:usedWavelength/xrdml:kAlpha1"
                ),
                "kAlpha2": find_float(
                    "xrdml:xrdMeasurement/xrdml:usedWavelength/xrdml:kAlpha2"
                ),
                "kBeta": find_float(
                    "xrdml:xrdMeasurement/xrdml:usedWavelength/xrdml:kBeta"
                ),
                "ratioKAlpha2KAlpha1": find_float(
                    "xrdml:xrdMeasurement/xrdml:usedWavelength/xrdml:ratioKAlpha2KAlpha1"
                ),
                "anode_material": find_string(
                    "xrdml:xrdMeasurement/xrdml:incidentBeamPath/xrdml:xRayTube"
                    "/xrdml:anodeMaterial"
                ),
            },
            "scan_mode": scan.get("mode", None),
            "scan_axis": scan.get("scanAxis", None),
        },
    }


class FormatParser:
    '''A class to identify and parse different file formats.'''

    def __init__(self, file_path, logger):
        '''
        Args:
            file_path (str): The path of the file to be identified and parsed.
            logger (BoundLogger): A structlog logger.
        '''
        self.file_path = file_path
        self.logger = logger

    def identify_format(self):
        '''Identifies the format of a given file.

        Returns:
            str: The file extension of the file.
        '''
        file_extension = os.path.splitext(self.file_path)[1].lower()
        return file_extension

    def parse_panalytical_xrdml(self):
        '''Parses a Panalytical XRDML file.

        Returns:
            dict: A dictionary containing the parsed XRDML
        data.
        '''
        return read_xrdml(self.file_path, self.logger)

    def parse_panalytical_udf(self):
        '''Parse the Panalytical .udf file.

        Returns:
            None: Placeholder for parsing .udf files.
        '''
        pass

    def parse_bruker_raw(self):
        '''Parse the Bruker .raw file.

        Returns:
            None: Placeholder for parsing .raw files.
        '''
        pass

    def parse_bruker_xye(self):
        '''Parse the Bruker .xye file.

        Returns:
            None: Placeholder for parsing .xye files.
        '''
        pass

    def parse_rigaku_rasx(self):
        ''' Parse the rigaku .rasx files.

        Returns:
            dict: A dictionary containing the parsed .rasx
        '''
        return read_rigaku_RASX(self.file_path, self.logger)

    def parse(self):
        '''Parses the file based on its format.

        Returns:
            dict: A dictionary containing the parsed data.

        Raises:
            ValueError: If the file format is unsupported.
        '''
        file_format = self.identify_format()

        if file_format == ".xrdml":
            return self.parse_panalytical_xrdml()
        elif file_format == ".rasx":
            return self.parse_rigaku_rasx()
        elif file_format == ".udf":
            return self.parse_panalytical_udf()
        elif file_format == ".raw":
            return self.parse_bruker_raw()
        elif file_format == ".xye":
            return self.parse_bruker_xye()
        else:
            raise ValueError(f"Unsupported file format: {file_format}")


class DataConverter:
    '''A class to convert parsed data into a common dictionary format.'''

    def __init__(self, parsed_data):
        '''
        Args:
            parsed_data (dict): The parsed data to be converted.
        '''
        self.parsed_data = parsed_data

    def convert(self):
        '''Converts the parsed data into a common dictionary format.

        Returns:
            dict: The converted data in a common dictionary format.
        '''
        # In this case, the parsed_data is already in the common dictionary format
        # If you need additional conversion or data processing, implement it here
        return self.parsed_data

def parse_and_convert_file(file_path, logger):
    '''The main function to parse and convert a file.
    Args:
        file_path (str): The path of the file to be parsed and converted.
        logger (BoundLogger): A structlog logger.

    Returns:
        dict: The parsed and converted data in a common dictionary format.
    '''
    file_path = os.path.abspath(file_path)

    format_parser = FormatParser(file_path, logger)
    parsed_data = format_parser.parse()

    data_converter = DataConverter(parsed_data)
    common_data = data_converter.convert()

    return common_data

def read_rigaku_RASX(file_path, logger):
    '''
    Reads .rasx files from Rigaku instruments
        - reader is based on IKZ submodule
        - currently supports one scan per file
        - in case of multiple scans per file, only the first scan is read

    Args:
        file_path (string): absolute path of the file
        logger (object): logger object for propagating errors and warnings

    Returns:
        dict: populated with data from Rigaku .RASX files
    '''
    reader = RASXfile(file_path)
    data = reader.data
    metainfo = reader.meta
    pdata = reader.get_RSM()

    ## in case of 2D scan, only select the first line scan, other angles than 2Theta are held constant
    if not data.shape[0] == 1:
        logger.warning("2D scan currently not supported. Taking the data from the first line scan.")
        for key in pdata:
            if type(pdata[key])==np.ndarray:
                if pdata[key].ndim == 2:
                    pdata[key] = pdata[key][0,:].squeeze()

        if not len(np.unique(pdata["Omega"])) == 1:
            raise ValueError("Unexpected array of Omega angles. Should contain same value of angles.")
        else:
            pdata["Omega"] = pdata["Omega"][0]
    metainfo = metainfo[0]

    _count_time = None
    if metainfo["ScanInformation"]["Mode"].lower() == "continuous":
        _speed_unit = ureg(metainfo["ScanInformation"]["SpeedUnit"].replace("min","minute"))
        _count_time_unit = ureg(metainfo["ScanInformation"]["PositionUnit"]) / _speed_unit
        _count_time = metainfo["ScanInformation"]["Step"] / metainfo["ScanInformation"]["Speed"]
        _count_time = np.array([_count_time]) * _count_time_unit

    axis = {}
    for ax in ["Omega", "Chi", "Phi"]:
        if not isinstance(pdata[ax], np.ndarray):
            axis[ax] = np.array([pdata[ax]]) 
        else:
            axis[ax] = pdata[ax]  

    output = {
        "detector"  : pdata["Intensity"],
        "2Theta"    : pdata[metainfo["ScanInformation"]["AxisName"]] *   ureg(reader.units[metainfo["ScanInformation"]["AxisName"]]),
        "Omega"     : axis["Omega"] * ureg(reader.units["Omega"]),
        "Chi"       : axis["Chi"] * ureg(reader.units["Chi"]),
        "Phi"       : axis["Phi"] * ureg(reader.units["Phi"]),
        "countTime" : _count_time,
        "metadata"  : {
            "sample_id" : None,     # not found in .rasx
            "scan_axis" : metainfo["ScanInformation"]["AxisName"],
            "source"    : {
                "anode_material"    : metainfo["HardwareConfig"]["xraygenerator"]["TargetName"],
                "kAlpha1"           : metainfo["HardwareConfig"]["xraygenerator"]["WavelengthKalpha1"]  * ureg("angstrom"),
                "kAlpha2"           : metainfo["HardwareConfig"]["xraygenerator"]["WavelengthKalpha2"]  * ureg("angstrom"),
                "kBeta"             : metainfo["HardwareConfig"]["xraygenerator"]["WavelengthKbeta"]    * ureg("angstrom"),
                "voltage"           : metainfo["HardwareConfig"]["xraygenerator"]["Voltage"] * ureg(metainfo["HardwareConfig"]["xraygenerator"]["VoltageUnit"]),
                "current"           : metainfo["HardwareConfig"]["xraygenerator"]["Current"] * ureg(metainfo["HardwareConfig"]["xraygenerator"]["CurrentUnit"]),
                "ratioKAlpha2KAlpha1"   : None,     # not found in .rasx
            },
        },
    }

    return output
