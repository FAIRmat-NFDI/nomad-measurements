# -*- coding: utf-8 -*-

'''
    Code adapted from io.py file available in Dr. Carsten Richter's codebase at
    https://github.com/carichte/IKZ/blob/master/IKZ/xray/io.py
    
'''

from __future__ import print_function
import zipfile
import sys
import xml.etree.ElementTree as ET
import collections
import numpy as np
import time
import xmltodict
from structlog.stdlib import (
    BoundLogger,
)

def try_scalar(val):
    try:
        return int(val)
    except (ValueError, TypeError):
        pass
    try:
        return float(val)
    except (ValueError, TypeError):
        pass
    return val


def parse_rasx_metadata(xml):
    mdata = dict()
    #xml.seek(0)
    tree = ET.parse(xml)
    measurement = tree.getroot()

    for group in ["GeneralInformation", "ScanInformation", "SampleInformation", "RSMInformation"]:
        groupobj = measurement.find(group)
        if groupobj is None:
            continue
        mdata[group] = dict((info.tag, try_scalar(info.text)) for info in groupobj)



    hwdict = mdata["HardwareConfig"] = dict()
    hwconf = measurement.find("HWConfigurations")

    optics = hwdict["optics"] = dict()
    for category in hwconf.find("Categories"):
        optics[category.attrib["Name"]] = category.attrib["SelectedUnit"]
    optics["Monochromator"] = [child.text for child in hwconf.find("Optics")]
    hwdict["Detector"] = optics["Detector"]


    distances = hwdict["distances"] = []
    
    ## python >= 3.7:
    #Distance = collections.namedtuple("Distance", ("To", "From", "Unit", "Value"), defaults=4*[None])
    ## python < 3.7:
    Distance = collections.namedtuple('Distance', ("To", "From", "Unit", "Value"))
    Distance.__new__.__defaults__ = (None,) * len(Distance._fields)

    for distance in hwconf.find("Distances"):
        attrib = distance.attrib.copy()
        attrib["Value"] = try_scalar(attrib["Value"])
        distances.append(Distance(**attrib))



    hwdict["xraygenerator"] = dict((info.tag, try_scalar(info.text)) for info in hwconf.find("XrayGenerator"))


    header = mdata["RASHeader"] = dict()
    axtitle = dict()
    for info in measurement.find("RASHeader"):
        pair = list(info)
        key = pair[0].text
        if "MEAS_COND_AXIS_NAME" in key:
            num = int(key.rsplit("-", 1)[1])
            axtitle[num] = pair[1].text
        else:
            header[key] = pair[1].text

    ## python >= 3.7:
    #Axis = collections.namedtuple("Axis",
    #                              ("Name", "Unit", "Offset", "Position", "Description"),
    #                              defaults=5*[None])
    ## python < 3.7:
    Axis = collections.namedtuple('Axis',
                                  ("Name",
                                   "Unit",
                                   "Offset",
                                   "Position",
                                   "EndPosition",
                                   "Description",
                                   "State",
                                   "Resolution",
                                   "Speed",
                                   "SpeedUnit",
                                   "SpeedResolution",
                                   "OscillationWidth",
                                   ))
    Axis.__new__.__defaults__ = (None,) * len(Axis._fields)

    axes = mdata["Axes"] = collections.OrderedDict()
    for i, axis in enumerate(measurement.find("Axes")):
        attrib = axis.attrib.copy()
        attrib["Description"] = axtitle[i]
        for key in ("Offset", "Position"):
            attrib[key] = try_scalar(attrib.get(key))
        attrib = dict([_i for _i in attrib.items() if _i[0] in Axis._fields])
        if len(attrib) < len(axis.attrib):
            missing = set(axis.attrib).difference(set(attrib))
            for key in missing:
                print("Warning: unknown axis attribute: %s"%k)
        axes[axis.attrib["Name"]] = Axis(**attrib)


    return mdata


class RASXfile(object):
    def __init__(self, path, verbose=True):
        with zipfile.ZipFile(path) as fh:
            # get the path for Profile<num>.txt
            profiles = [f.filename for f in fh.filelist if "Profile" in f.filename]
            numscans = len(profiles)
            data = []
            meta = []
            for i in range(numscans):
                if verbose:
                    if not i:
                        print("Loading profiles...")
                    sys.stdout.write("\r%5i/%i"%(i+1, numscans))
                profile = profiles[i]
                metafile = profile.replace("Profile", "MesurementConditions")
                metafile = metafile[:-4] + ".xml"
                #print(fname)
                with fh.open(profile) as f:
                    ## python >= 3.7:
                    f.seek(3) # skip the 3 non-ascii symbols at the start
                    data.append(np.loadtxt(f))
                    ## the ugly way to stay python < 3.7 compatible:
                    # _content = BytesIO(f.read()[3:])
                    # data.append(np.loadtxt(_content))
                with fh.open(metafile) as xml:
                    meta.append(parse_rasx_metadata(xml))

            ## loading images if available
            images = [f.filename for f in fh.filelist if "Image" in f.filename]
            numimg = len(images)


            imgdata = []
            for i in range(numimg):
                if verbose:
                    if not i:
                        print("Loading frames...")
                    sys.stdout.write("\r%5i/%i"%(i+1, numimg))
                imgpath = images[i]
                metafile = imgpath.replace("Image", "MesurementConditions")
                metafile = metafile[:-4] + ".xml"
                #print(fname)

                with fh.open(metafile) as xml:
                    meta.append(parse_rasx_metadata(xml))
                optics = meta[-1]["HardwareConfig"]["optics"]
                if optics["Detector"] == 'HyPix3000(H)':
                    det_shape = 385, 775
                elif optics["Detector"] == 'HyPix3000(V)':
                    det_shape = 775, 385
                else:
                    det_shape = -1,
                with fh.open(imgpath) as f:
                    imgarr = np.fromstring(f.read(), dtype=np.uint32)
                    imgarr.resize(det_shape)
                    imgdata.append(imgarr)

            if verbose:
                print()

        self._ndscan = len(np.unique(list(map(len, data))))==1
        if self._ndscan:
            data = np.array(data)    
        else:  # not originally part of Carsten's code 
            raise NotImplementedError("Unequal lengths of multiple scans in a file not supported.")
        imgdata = np.array(imgdata)

        self.data = data
        self.images = imgdata
        self.meta = meta
        self.positions = collections.defaultdict(list)
        self.units = collections.defaultdict(str)
        ## retrieving information about axis
        for mdata in meta:
            for axis in mdata["Axes"].values():
                self.positions[axis.Name].append(axis.Position)
                self.units[axis.Name] = axis.Unit
        for axis in self.positions:
            if len(set(self.positions[axis])) == 1:
                self.positions[axis] = self.positions[axis][0]
            else:
                self.positions[axis] = np.array(self.positions[axis])

    def get_RSM(self):
        pos, I, _ = self.data.transpose(2,0,1).squeeze()
        output = dict(Intensity=I)
        mot = self.meta[0]["ScanInformation"]["AxisName"]
        output[mot] = pos
        for axis in ["Omega", "Chi", "Phi", "TwoTheta", "TwoThetaChi"]:
            if axis in output:
                continue
            axdata = self.positions[axis]
            if np.ndim(axdata):
                # duplicate values to match dimensions of intensity
                # useful when num_scans > 1
                axdata = axdata[:,None] * np.ones_like(I)
            output[axis] = axdata

        return output

    def get_1d_scan(self, logger: BoundLogger=None):
        '''
        Collect the values and units of intensity, two_theta, and axis positions. Adapts 
        the output if collected data has multiple/2d scans.

        Returns:
            Dict[str, Any]: Each dict item contains a list with numerical value
                (numpy.ndarray) at index 0 and unit (str) at index 1. If quantity 
                is not available, the dict item will default to []. If units are not 
                available for two_theta or axis positions, they will default to 'deg'.
        '''
        two_theta, intensity, _ = self.data.transpose(2, 0, 1).squeeze()
        output = collections.defaultdict(list)
        output['intensity'] = [intensity, '']
        scan_axis = None
        scan_info = self.meta[0].get('ScanInformation', None)
        if scan_info:
            scan_axis = scan_info.get('AxisName', None)
        output['two_theta'] = [
            two_theta,
            self.units.get(scan_axis, 'deg'),
        ]

        for axis in ['Omega', 'Chi', 'Phi']:
            if axis not in self.positions.keys():
                continue
            ax_data = self.positions[axis]
            if not isinstance(ax_data, np.ndarray):
                ax_data = np.array([ax_data])
            if np.ndim(ax_data):
                ax_data = ax_data[:, None] * np.ones_like(intensity)
            output[axis + '_position'] = [
                ax_data,
                self.units.get(axis, 'deg'),
            ]

        if not self.data.shape[0] == 1:
            if logger is not None:
                logger.warning(
                    'Multiple/2D/RSM scan currently not supported. '
                    'Taking the data from the first line scan.'
                )
            for key, data in output.items():
                if isinstance(data[0], np.ndarray) and data[0].ndim == 2:
                    output[key][0] = data[0][0,:].squeeze()
                    if len(np.unique(output[key][0])) == 1:
                        # shrinking duplicate data populated by self.__init__()
                        first_val = output[key][0][0]
                        output[key][0] = np.array([first_val])

        return output

    def get_scan_info(self):
        '''
        Collects the scan information from self.meta if available.

        Returns:
            Dict[str, Any]: contains information about the scan
        '''
        return self.meta[0].get('ScanInformation',None)

    def get_source_info(self):
        '''
        Collects meta information of the X-ray source along with associated units.

        Returns:
            Dict[str, Any]: Each dict item contains a list with numerical value
                (float or int) at index 0 and unit (str) at index 1. One exception
                is the item with key 'TargetName' which has str at both indices.
                If quantity is not available, the dict item will default to [].
        '''
        output = collections.defaultdict(list)
        source = collections.defaultdict(list,
            self.meta[0]['HardwareConfig']['xraygenerator'])

        if source['TargetName']:
            output['TargetName'] = [
                source['TargetName'],
                '',
            ]
        if source['Voltage']:
            output['Voltage'] = [
                source['Voltage'],
                source.get('VoltageUnit','kV'),
            ]
        if source['Current']:
            output['Current'] = [
                source['Current'],
                source.get('CurrentUnit','mA'),
            ]
        for wavelength in ['WavelengthKalpha1', 'WavelengthKalpha2', 'WavelengthKbeta']:
            if source[wavelength]:
                output[wavelength] = [
                    source[wavelength],
                    source.get(wavelength + 'Unit', 'angstrom'),
                ]

        return output

    def get_starttime(self, idx=0, to_seconds=True):
        starttime = self.meta[idx]["ScanInformation"]["StartTime"]
        parsed_time = time.strptime(starttime, "%Y-%m-%dT%H:%M:%SZ")
        if to_seconds:
            return time.mktime(parsed_time)
        else:
            return parsed_time


class BRMLfile(object):
    def __init__(self, path, exp_nbr=0, encoding="utf-8", verbose=True):
        self.path = path
        with zipfile.ZipFile(path, 'r') as fh:
            experiment = "Experiment%i"%exp_nbr
            datacontainer = "%s/DataContainer.xml"%experiment

            with fh.open(datacontainer, "r") as xml:
                data = xmltodict.parse(xml.read(), encoding=encoding)
            rawlist = data["DataContainer"]["RawDataReferenceList"]["string"]
            # rawlist contains the reference to all the raw files (multiple in case of RSM)
            if not isinstance(rawlist, list):
                rawlist = [rawlist]

            self.data = collections.defaultdict(list)
            self.motors = self.data # collections.defaultdict(list)
            for i, rawpath in enumerate(rawlist):
                if verbose:
                    if not i:
                        print("Loading frame %i"%i, end="")
                    else:
                        print(", %i"%i, end="")
                with fh.open(rawpath, "r") as xml:
                    # entering RawData<int>.xml
                    data = xmltodict.parse(xml.read(), encoding=encoding)
                dataroute = data["RawData"]["DataRoutes"]["DataRoute"]
                scaninfo = dataroute["ScanInformation"]
                nsteps = int(scaninfo["MeasurementPoints"])
                if nsteps==1:
                    rawdata = np.array(dataroute["Datum"].split(","))
                elif nsteps>1:
                    rawdata = np.array([d.split(",") for d in dataroute["Datum"]])

                rawdata = rawdata.astype(float).T
                rdv = dataroute["DataViews"]["RawDataView"]
                if not isinstance(rdv,list):
                    rdv = [rdv]
                for view in rdv:
                    viewtype = view["@xsi:type"]
                    vstart = int(view["@Start"])
                    vlen = int(view["@Length"])
                    if viewtype=="FixedRawDataView":
                        vname = view["@LogicName"]
                        self.data[vname].append(rawdata[vstart:(vstart+vlen)])
                    elif viewtype=="RecordedRawDataView":
                        vname = view["Recording"]["@LogicName"]
                        self.data[vname].append(rawdata[vstart:(vstart+vlen)])

                self.data["ScanName"].append(scaninfo["@ScanName"])
                self.data["TimePerStep"].append(scaninfo["TimePerStep"])
                self.data["TimePerStepEffective"].append(scaninfo["TimePerStepEffective"])
                self.data["ScanMode"].append(scaninfo["ScanMode"])

                scanaxes = scaninfo["ScanAxes"]["ScanAxisInfo"]
                if not isinstance(scanaxes, list):
                    scanaxes = [scanaxes]
                for axis in scanaxes:
                    aname = axis["@AxisName"]
                    aunit = axis["Unit"]["@Base"]
                    aref = float(axis["Reference"])
                    astart = float(axis["Start"]) + aref
                    astop = float(axis["Stop"]) + aref
                    astep = float(axis["Increment"])
                    nint = int(round(abs(astop-astart)/astep))
                    adata = {} # not originally part of Carsten's code
                    adata["Value"] = np.linspace(astart, astop, nint+1)
                    adata["Unit"] = aunit.lower()
                    self.data[aname].append(adata)

                drives = data["RawData"]["FixedInformation"]["Drives"]["InfoData"]
                if not isinstance(drives,list):
                    drives = [drives]
                for axis in drives:
                    aname = axis["@LogicName"]
                    apos = float(axis["Position"]["@Value"])
                    aunit = axis["Position"]["@Unit"]
                    adata = {} # not originally part of Carsten's code
                    adata["Value"] = apos
                    adata["Unit"] = aunit.lower()
                    self.motors[aname].append(adata)

            # (block starts) not originally part of Carsten's code
            try:
                self.mounted_optics_info = (
                    data["RawData"]["FixedInformation"]["Instrument"]
                    ["PrimaryTracks"]["TrackInfoData"]["MountedOptics"]["InfoData"]
                )
            except (KeyError, TypeError):
                self.mounted_optics_info = []
            # (block end) not originally part of Carsten's code

            for key in self.data:
                self.data[key] = np.array(self.data[key]).squeeze()
                if not self.data[key].shape:
                    self.data[key] = self.data[key].item()
            for key in self.motors:
                self.motors[key] = np.array(self.motors[key]).squeeze()
                if not self.motors[key].shape:
                    self.motors[key] = self.motors[key].item()

    def get_1d_scan(self, logger: BoundLogger=None):
        '''
        Collect the values and units of intensity, two_theta, and axis positions. Adapts
        the output if collected data has multiple/2d scans.

        Returns:
            Dict[str, Any]: Each dict item contains a list with numerical value
                (numpy.ndarray) at index 0 and unit (str) at index 1. If quantity
                is not available, the dict item will default to []. If units are not
                available for two_theta or axis positions, they will default to 'deg'.
        '''
        output = collections.defaultdict(list)

        counter_key = []
        for key in self.data.keys():
            if 'counter' in key.lower():
                counter_key.append(key)
        if len(counter_key) > 1:
            raise ValueError("More than one intensity counters found.")

        if not self.data.get(counter_key[0]).ndim == 1:
            if logger is not None:
                logger.warning(
                    'Multiple/2D/RSM scan currently not supported. '
                    'Taking the data from the first line scan.'
                )
            for key in [counter_key[0], 'TwoTheta', 'Theta', 'Chi', 'Phi']:
                val = self.data.get(key, None)
                if val is not None:
                    self.data[key] = val[0]

        if counter_key:
            output['intensity'] = [self.data.get(counter_key[0]), '']

        for key in ['TwoTheta', 'Theta', 'Chi', 'Phi']:
            data = self.data.get(key)
            if data is not None:
                val = data.get('Value')
                if val is not None:
                    if not isinstance(val, np.ndarray):
                        val = np.array([val])
                    output[key] = [
                        val,
                        data.get('Unit', 'deg'),
                    ]

        return output

    def get_scan_info(self):
        '''
        Collects the scan information from self.data if available.

        Returns:
            Dict[str, Any]: contains information about the scan
        '''
        output = collections.defaultdict(list)
        for key in ['ScanName']:
            if self.data.get(key) is not None:
                output[key] = [
                    self.data.get(key)[0],
                    '',
                ]

        return output

    def get_source_info(self):
        '''
        Collects meta information of the X-ray source along with associated units.

        Returns:
            Dict[str, Any]: Each dict item contains a list with numerical value
                (float or int) at index 0 and unit (str) at index 1. One exception
                is the item with key 'TubeMaterial' which has str at both indices.
                If quantity is not available, the dict item will default to [].
        '''
        output = collections.defaultdict(list)

        source = {}
        for component in self.mounted_optics_info:
            if component["@xsi:type"] == "TubeMountInfoData":
                source = component.get("Tube", {})
        if not source:
            return output

        if source.get('TubeMaterial'):
            output['TubeMaterial'] = [
                source['TubeMaterial'],
                '',
            ]
        if source.get('Generator', {}).get('Voltage'):
            val = source['Generator']['Voltage'].get('@Value')
            if val is not None:
                val = float(val)
                output['Voltage'] = [
                    val,
                    source['Generator']['Voltage'].get('@Unit', 'kV'),
                ]
        if source.get('Generator', {}).get('Current'):
            val = source['Generator']['Current'].get('@Value')
            if val is not None:
                val = float(val)
                output['Current'] = [
                    val,
                    source['Generator']['Current'].get('@Unit', 'mA'),
                ]
        for wavelength in [
            'WaveLengthAlpha1', 'WaveLengthAlpha2',
            'WaveLengthBeta', 'WaveLengthRatio',
        ]:
            if source.get(wavelength):
                val = source[wavelength].get('@Value')
                if val is not None:
                    val = float(val)
                    output[wavelength] = [
                        val,
                        source[wavelength].get('@Unit', 'angstrom'),
                    ]

        return output
