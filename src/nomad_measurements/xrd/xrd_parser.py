import re # for regular expressions
import os  # for file path operations
import numpy as np
import xml.etree.ElementTree as ET # for XML parsing
# from xrayutilities.io.panalytical_xml import XRDMLFile # for reading XRDML files
from nomad.units import ureg
from .IKZ import RASXfile

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


class PanalyticalXRDMLParser:
    '''A class to parse Panalytical XRDML files.'''

    def __init__(self, file_path):
        '''
        Args:
            file_path (str): The path of the XRDML file to be parsed.
        '''
        self.file_path = file_path

    def parse_metadata(self):
        '''Parses the metadata of the XRDML file.'''

        with open(self.file_path, 'r', encoding='utf-8') as file:
            content = file.read()

        # Remove the XML encoding declaration if it exists
        content = re.sub(r'<\?xml.*\?>', '', content)

        root = ET.fromstring(content)

        ns_version = root.tag.split("}")[0].strip("{")
        ns = {'xrd': ns_version}

        xrd_measurement = root.find("xrd:xrdMeasurement", ns)
        xrd_sample = root.find("xrd:sample", ns)
        
        def find_float(path):
            result = xrd_measurement.find(path, ns)
            if result is not None:
                unit = result.get('unit', '')
                if unit == 'Angstrom':
                    unit = 'angstrom'
                return float(result.text) * ureg(unit)
            else:
                return None

        metadata = {
            "sample_id": xrd_sample.find(".//{*}id", ns).text if xrd_sample.find(".//{*}id", ns) is not None else None,
            "measurement_type": xrd_measurement.get("measurementType", None),
            "sample_mode": xrd_measurement.get("sampleMode", None),
            "source": {
                "voltage": find_float("xrd:incidentBeamPath/xrd:xRayTube/xrd:tension"),
                "kAlpha1": find_float("xrd:usedWavelength/xrd:kAlpha1"),
                "kAlpha2": find_float("xrd:usedWavelength/xrd:kAlpha2"),
                "kBeta": find_float("xrd:usedWavelength/xrd:kBeta"),
                "ratioKAlpha2KAlpha1": find_float("xrd:usedWavelength/xrd:ratioKAlpha2KAlpha1"),
                "anode_material": xrd_measurement.find("xrd:incidentBeamPath/xrd:xRayTube/xrd:anodeMaterial", ns).text if xrd_measurement.find("xrd:incidentBeamPath/xrd:xRayTube/xrd:anodeMaterial", ns) is not None else None,
            },

            "scan_mode": xrd_measurement.find("xrd:scan", ns).get("mode") if xrd_measurement.find("xrd:scan", ns) is not None else None,
            "scan_axis": xrd_measurement.find("xrd:scan", ns).get("scanAxis") if xrd_measurement.find("xrd:scan", ns) is not None else None,
        }
        return metadata


    def parse_xrdml(self):
        '''Parses the XRDML file using xrayutilities.

        Returns:
            dict: A dictionary containing the parsed XRDML data.
        '''
        # Read the XRDML file using xrayutilities
        # xrd_data = XRDMLFile(self.file_path)
        xrd_data = {}
        result = xrd_data.scan.ddict


        # Add the scanmotname, material, hkl to the dictionary
        result["scanmotname"] = xrd_data.scan.scanmotname
        result["material"] = xrd_data.scan.material
        result["hkl"] = xrd_data.scan.hkl
        # add the metadata to the dictionary
        result["metadata"] = self.parse_metadata()

        return result


class FormatParser:
    '''A class to identify and parse different file formats.'''

    def __init__(self, file_path, logger):
        '''
        Args:
            file_path (str): The path of the file to be identified and parsed.
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
        xrdml_parser = PanalyticalXRDMLParser(self.file_path)
        return xrdml_parser.parse_xrdml()

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
    ''' Reads .rasx files from Rigaku instruments
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
    data = reader.get_data()
    metainfo = reader.get_metainfo()
    pdata = reader.get_RSM()

    if not metainfo[0]['ScanInformation']['AxisName'] == "TwoTheta":
        raise NotImplementedError(f"{metainfo[0]['ScanInformation']['AxisName']} scan not supported. Only TwoTheta scan is supported.")

    ## in case of 2D scan, only select the first line scan, other angles than 2Theta are held constant
    if not data.shape[0] == 1:
        logger.warn("2D scan currently not supported. Taking the data from the first line scan.")
        for key in pdata:
            if type(pdata[key])==np.ndarray:
                if pdata[key].ndim == 2:
                    pdata[key] = pdata[key][0,:].squeeze()

        if not len(np.unique(pdata["Omega"])) == 1:
            raise ValueError("Unexpected array of Omega angles. Should contain same value of angles.")
        else:
            pdata["Omega"] = pdata["Omega"][0]
    metainfo = metainfo[0]

    output = {
        "detector"  : pdata["Intensity"],
        "2Theta"    : pdata["TwoTheta"],
        "Omega"     : pdata["Omega"],
        "Chi"       : pdata["Chi"],
        "countTime" : None,         # not found in .rasx 
        "metadata"  : {
            "sample_id" : None,     # not found in .rasx
            "scan_axis" : metainfo["ScanInformation"]["AxisName"],
            "source"    : {
                "anode_material"    : metainfo["HardwareConfig"]["xraygenerator"]["TargetName"],
                "kAlpha1"           : metainfo["HardwareConfig"]["xraygenerator"]["WavelengthKalpha1"],
                "kAlpha2"           : metainfo["HardwareConfig"]["xraygenerator"]["WavelengthKalpha2"],
                "kBeta"             : metainfo["HardwareConfig"]["xraygenerator"]["WavelengthKbeta"],
                "voltage"           : metainfo["HardwareConfig"]["xraygenerator"]["Voltage"] * ureg(metainfo["HardwareConfig"]["xraygenerator"]["VoltageUnit"]), 
                "current"           : metainfo["HardwareConfig"]["xraygenerator"]["Current"] * ureg(metainfo["HardwareConfig"]["xraygenerator"]["CurrentUnit"]),
                "ratioKAlpha2KAlpha1"   : None,     # not found in .rasx
            },
        },
    }

    return output
