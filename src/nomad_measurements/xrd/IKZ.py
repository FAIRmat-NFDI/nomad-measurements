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
        self.units = dict()
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
                axdata = axdata[:,None] * np.ones_like(I)
            output[axis] = axdata

        return output
    
    def get_starttime(self, idx=0, to_seconds=True):
        starttime = self.meta[idx]["ScanInformation"]["StartTime"]
        parsed_time = time.strptime(starttime, "%Y-%m-%dT%H:%M:%SZ")
        if to_seconds:
            return time.mktime(parsed_time)
        else:
            return parsed_time
