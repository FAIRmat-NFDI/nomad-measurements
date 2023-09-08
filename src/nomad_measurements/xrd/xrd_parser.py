import re # for regular expressions
import os  # for file path operations
import xml.etree.ElementTree as ET # for XML parsing
from xrayutilities.io.panalytical_xml import XRDMLFile # for reading XRDML files
from nomad.units import ureg


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
        xrd_data = XRDMLFile(self.file_path)
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

    def __init__(self, file_path):
        '''
        Args:
            file_path (str): The path of the file to be identified and parsed.
        '''
        self.file_path = file_path

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

def parse_and_convert_file(file_path):
    '''The main function to parse and convert a file.
    Args:
        file_path (str): The path of the file to be parsed and converted.

    Returns:
        dict: The parsed and converted data in a common dictionary format.
    '''
    file_path = os.path.abspath(file_path)

    format_parser = FormatParser(file_path)
    parsed_data = format_parser.parse()

    data_converter = DataConverter(parsed_data)
    common_data = data_converter.convert()

    return common_data
