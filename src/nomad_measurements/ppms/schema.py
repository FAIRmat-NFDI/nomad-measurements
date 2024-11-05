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
from typing import (
    TYPE_CHECKING,
)

import re
from io import StringIO
import numpy as np
import pandas as pd
from datetime import datetime


from structlog.stdlib import (
    BoundLogger,
)

from nomad.metainfo import Package, Section, MEnum, SubSection

from nomad.datamodel.metainfo.basesections import Measurement

from nomad.datamodel.metainfo.annotations import (
    ELNAnnotation,
    SectionProperties,
)
from nomad.datamodel.data import (
    EntryData,
)
from nomad.datamodel.data import (
    ArchiveSection,
)

from nomad.metainfo import (
    Package,
    Quantity,
)

from nomad.datamodel.metainfo.eln import (
    CompositeSystem,
)

from nomad.datamodel.metainfo.plot import PlotSection, PlotlyFigure

from nomad_measurements.ppms.ppmssteps import (
    PPMSMeasurementStep,
    PPMSMeasurementRemarkStep,
    PPMSMeasurementWaitStep,
    PPMSMeasurementSetPositionStep,
    PPMSMeasurementSetTemperatureStep,
    PPMSMeasurementScanFieldStep,
    PPMSMeasurementScanFieldEndStep,
    PPMSMeasurementScanTempStep,
    PPMSMeasurementScanTempEndStep,
    PPMSMeasurementACTResistanceStep,
    PPMSMeasurementETOResistanceStep,
    PPMSMeasurementSetMagneticFieldStep,
)

from nomad_measurements.ppms.ppmsdatastruct import (
    PPMSData,
    ACTPPMSData,
    ACTChannelData,
    ACTData,
    ETOPPMSData,
    ETOChannelData,
    ETOData,
)

if TYPE_CHECKING:
    from structlog.stdlib import (
        BoundLogger,
    )

from nomad.config import config
from nomad.metainfo import SchemaPackage

configuration = config.get_plugin_entry_point(
    'nomad_measurements.ppms:schema_package_entry_point'
)

m_package = SchemaPackage()

def clean_channel_keys(input_key: str) -> str:
    output_key = (
        input_key
        .split('(')[0]
        .replace('Std. Dev.', 'std dev')
        .replace('Std.Dev.', 'std dev')
        .replace('Res.', 'resistivity')
        .replace('Crit.Cur.', 'crit cur')
        .replace('C.Cur.', 'crit cur')
        .replace('Quad.Error', 'quad error')
        .replace('Harm.', 'harmonic')
        .replace('-', ' ')
        .replace('Field (Oe)','Magnetic Field (Oe)')
        .lower()
        .replace('ch1','')
        .replace('ch2','')
        .strip()
        .replace(' ','_')
        .replace('3rd','third')
        .replace('2nd','second')
    )
    return output_key

class Sample(CompositeSystem):
    name = Quantity(
        type=str,
        description='FILL')
    type = Quantity(
        type=str,
        description='FILL')
    material = Quantity(
        type=str,
        description='FILL')
    comment = Quantity(
        type=str,
        description='FILL')
    lead_separation = Quantity(
        type=str,
        description='FILL')
    cross_section = Quantity(
        type=str,
        description='FILL')



class PPMSMeasurement(Measurement,PlotSection,EntryData):

    # m_def = Section(
    #     a_eln=dict(lane_width='600px'),
    #     a_plot={"plotly_graph_object": {
    #             "data": {
    #             "x": "#data/temperature",
    #             "y": "#data/field",
    #             },
    #         }
    # },
    # )
    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                   'name',
                   'datetime',
                   'data_file',
                   'sequence_file',
                   'description',
                   'software',
                   'startupaxis',
               ],
            ),
            lane_width='600px',
            ),
    )

    data_file = Quantity(
        type=str,
        a_eln=dict(component='FileEditQuantity'),
        a_browser=dict(adaptor='RawFileAdaptor'))
    file_open_time = Quantity(
        type=str,
        description='FILL')
    software = Quantity(
        type=str,
        description='FILL')
    startupaxis = Quantity(
        type=str,
        shape=['*'],
        description='FILL')

    steps = SubSection(
        section_def=PPMSMeasurementStep,
        repeats=True,
    )

    data = SubSection(section_def=PPMSData, repeats=True)
    #data = SubSection(section_def=PPMSData)

    sequence_file = Quantity(
        type=str,
        a_eln=dict(component='FileEditQuantity'),
        a_browser=dict(adaptor='RawFileAdaptor'))

    temperature_tolerance = Quantity(
        type=float,
        unit='kelvin',
        a_eln=ELNAnnotation(
            component='NumberEditQuantity',
            defaultDisplayUnit='kelvin'
        ),
    )

    field_tolerance = Quantity(
        type=float,
        unit='gauss',
        a_eln=ELNAnnotation(
            component='NumberEditQuantity',
            defaultDisplayUnit='gauss'
        ),
    )

    def normalize(self, archive, logger: BoundLogger) -> None:

        super(PPMSMeasurement, self).normalize(archive, logger)

        if archive.data.sequence_file:
            logger.info('Parsing PPMS sequence file.')
            with archive.m_context.raw_file(self.sequence_file, 'r') as file:
                sequence = file.readlines()

            all_steps=[]
            measurement_active=False
            for line in sequence:
                if line.startswith("!"):
                    continue
                elif line.startswith("REM "):
                    all_steps.append(PPMSMeasurementRemarkStep(
                        name="Remark: "+line[4:],
                        remark_text=line[4:],
                        )
                    )
                elif line.startswith("WAI "):
                    details=line.split()
                    onerror=["No Action","Abort","Shutdown"]
                    all_steps.append(PPMSMeasurementWaitStep(
                        name="Wait for "+details[2]+" s.",
                        delay=float(details[2]),
                        condition_temperature=bool(int(details[3])),
                        condition_field=bool(int(details[4])),
                        condition_position=bool(int(details[5])),
                        condition_chamber=bool(int(details[6])),
                        on_error_execute=onerror[int(details[7])],
                        )
                    )
                elif line.startswith("MVP"):
                    details=line.split()
                    mode=["Move to position","Move to index and define",
                          "Redefine present position"]
                    all_steps.append(PPMSMeasurementSetPositionStep(
                        name="Move sample to position "+details[2]+".",
                        position_set=float(details[2]),
                        position_rate=float(details[5].strip("\"")),
                        mode=mode[int(details[3])],
                        )
                    )
                elif line.startswith("TMP"):
                    details=line.split()
                    mode=['Fast Settle','No Overshoot']
                    all_steps.append(PPMSMeasurementSetTemperatureStep(
                        name="Set temperature to "+details[2]+" K with "+details[3]+" K/min.",
                        temperature_set=float(details[2]),
                        temperature_rate=float(details[3])/60.,
                        mode=mode[int(details[4])],
                        )
                    )
                elif line.startswith("FLD"):
                    details=line.split()
                    approach=['Linear','No Overshoot','Oscillate']
                    end_mode=['Persistent','Driven']
                    all_steps.append(PPMSMeasurementSetMagneticFieldStep(
                        name="Set field to "+details[2]+" Oe with "+details[3]+" Oe/min.",
                        field_set=float(details[2]),
                        field_rate=float(details[3]),
                        approach=approach[int(details[4])],
                        end_mode=end_mode[int(details[5])],
                        )
                    )
                elif line.startswith("LPB"):
                    details=line.split()
                    spacing_code=['Uniform','H*H','H^1/2','1/H','log(H)']
                    approach=['Linear','No Overshoot','Oscillate','Sweep']
                    end_mode=['Persistent','Driven']
                    all_steps.append(PPMSMeasurementScanFieldStep(
                        name="Scan field from "+details[2]+" Oe to "+details[3]+" Oe.",
                        initial_field=float(details[2]),
                        final_field=float(details[3]),
                        spacing_code=spacing_code[int(details[6])],
                        rate=float(details[4]),
                        number_of_steps=int(details[5]),
                        approach=approach[int(details[7])],
                        end_mode=end_mode[int(details[8])],
                        )
                    )
                elif line.startswith("ENB"):
                    all_steps.append(PPMSMeasurementScanFieldEndStep(
                        name="End Field Scan."
                        )
                    )
                elif line.startswith("LPT"):
                    details=line.split()
                    spacing_code=['Uniform','1/T','log(T)']
                    approach=['Fast','No Overshoot','Sweep']
                    all_steps.append(PPMSMeasurementScanTempStep(
                        name="Scan temperature from "+details[2]+" K to "+details[3]+" K.",
                        initial_temp=float(details[2]),
                        final_temp=float(details[3]),
                        spacing_code=spacing_code[int(details[6])],
                        rate=float(details[4])/60.,
                        number_of_steps=int(details[5]),
                        approach=approach[int(details[7])],
                        )
                    )
                elif line.startswith("ENT"):
                    all_steps.append(PPMSMeasurementScanTempEndStep(
                        name="End Temperature Scan."
                        )
                    )
                elif line.startswith("ACTR"):
                    details=line.split()
                    autorange=['Fixed Gain','Always Autorange','Sticky Autorange']
                    fixedgain=[5,1,0.5,0.2,0.1,0.05,0.04,0.02,0.01,0.005,0.004,0.002,0.001,0.0004,0.0002,0.00004]
                    all_steps.append(PPMSMeasurementACTResistanceStep(
                        name="AC Transport Resistance measurement.",
                        measurement_active=[bool(int(details[4])),bool(int(details[12]))],
                        excitation=[float(details[5])/1000,float(details[13])/1000],
                        frequency=[float(details[6]),float(details[14])],
                        duration=[float(details[7]),float(details[15])],
                        constant_current_mode=[bool(int(details[8])),bool(int(details[16]))],
                        low_resistance_mode=[bool(int(details[11])),bool(int(details[19]))],
                        autorange=[autorange[int(details[9])],autorange[int(details[17])]],
                        fixed_gain=[fixedgain[int(details[10])],fixedgain[int(details[18])]]
                        )
                    )
                elif line.startswith("ETOR"):
                    details=line.split()
                    mode=['Do Nothing','Start Excitation','Start Continuous Measure',
                          'Perform N Measurements','Stop Measurement','Stop Excitation']
                    sample_wiring=['4-wire','2-wire']
                    shift=0
                    name=""
                    mode_int=[]
                    number_of_measure=[]
                    amplitude=[]
                    frequency=[]
                    wiring=[]
                    autorange=[]
                    averaging_time=[]
                    for i in range(2):
                        mode_int.append(int(details[3+shift]))
                        if mode_int[i] in [0,4,5]:
                            number_of_measure.append(0)
                            amplitude.append(0)
                            frequency.append(0)
                            wiring.append(0)
                            autorange.append(False)
                            averaging_time.append(0)
                            shift+=1
                        elif mode_int[i] in [1,2,3]:
                            if mode_int[i]==3:
                                number_of_measure.append(int(details[4+shift]))
                                shift+=1
                            else:
                                number_of_measure.append(0)
                            amplitude.append(float(details[5+shift])/1000.)
                            frequency.append(float(details[6+shift]))
                            wiring.append(int(details[12+shift]))
                            autorange.append(bool(int(details[8+shift])))
                            averaging_time.append(float(details[7+shift]))
                            shift+=10
                        name+="Channel "+str(i+1)+": "+mode[mode_int[i]]
                        if i==0: name+="; "
                    # if 4 in mode_int:
                    #     measurement_active=False
                    # if 1 in mode_int or 2 in mode_int or 3 in mode_int:
                    #     measurement_active=True
                    all_steps.append(PPMSMeasurementETOResistanceStep(
                        name=name,
                        mode=[mode[mode_int[0]],mode[mode_int[1]]],
                        excitation_amplitude=amplitude,
                        excitation_frequency=frequency,
                        preamp_sample_wiring=[sample_wiring[wiring[0]],sample_wiring[wiring[1]]],
                        preamp_autorange=autorange,
                        config_averaging_time=averaging_time,
                        config_number_of_measurements=number_of_measure,
                        )
                    )
                elif line.startswith("SHT"):
                    continue
                elif line.startswith("CHN"):
                    continue
                else:
                    logger.error('Found unknown keyword '+line[:4])
            self.steps=all_steps

        if archive.data.data_file:
            logger.info('Parsing PPMS measurement file.')
            if not self.temperature_tolerance:
                self.temperature_tolerance=0.2
            if not self.field_tolerance:
                self.field_tolerance=5.

            with archive.m_context.raw_file(self.data_file, 'r') as file:
                data = file.read()

            header_match = re.search(r'\[Header\](.*?)\[Data\]', data, re.DOTALL)
            header_section = header_match.group(1).strip()
            header_lines = header_section.split('\n')

            sample1_headers = [line for line in header_lines if line.startswith("INFO") and 'SAMPLE1_' in line]
            sample_1 = Sample()
            for line in sample1_headers:
                parts = re.split(r',\s*', line)
                key = parts[-1].lower().replace('sample1_','')
                if hasattr(sample_1, key):
                    setattr(sample_1, key, ", ".join(parts[1:-1]))

            sample2_headers = [line for line in header_lines if line.startswith("INFO") and 'SAMPLE2_' in line]
            sample_2 = Sample()
            for line in sample2_headers:
                parts = re.split(r',\s*', line)
                key = parts[-1].lower().replace('sample2_','')
                if hasattr(sample_2, key):
                    setattr(sample_2, key, ", ".join(parts[1:-1]))

            while self.samples:
                self.m_remove_sub_section(PPMSMeasurement.samples, 0)
            self.m_add_sub_section(PPMSMeasurement.samples, sample_1)
            self.m_add_sub_section(PPMSMeasurement.samples, sample_2)

            startupaxis_headers = [line for line in header_lines if line.startswith("STARTUPAXIS")]
            if startupaxis_headers:
                startupaxis = []
                for line in startupaxis_headers:
                    parts = line.split(',', 1)
                    startupaxis.append(parts[1])
                if hasattr(self, 'startupaxis'):
                    setattr(self, 'startupaxis', startupaxis)

            for line in header_lines:
                if line.startswith("FILEOPENTIME"):
                    if hasattr(self, 'datetime'):
                        try:
                            iso_date = datetime.strptime(line.split(',')[3], "%m/%d/%Y %H:%M:%S")
                        except ValueError:
                            try:
                                iso_date = datetime.strptime(" ".join(line.split(',')[2:4]), "%m-%d-%Y %I:%M %p")
                            except ValueError:
                                iso_date = datetime.strptime(line.split(',')[3], "%Y-%m-%d %H:%M:%S")
                        setattr(self, 'datetime', iso_date)
                if line.startswith("BYAPP"):
                    if hasattr(self, 'software'):
                        setattr(self, 'software', line.replace('BYAPP,', '').strip())
                if line.startswith("TEMPERATURETOLERANCE"):
                    if hasattr(self, 'temperature_tolerance'):
                        setattr(self, 'temperature_tolerance', float(line.replace('TEMPERATURETOLERANCE,', '').strip()))
                if line.startswith("FIELDTOLERANCE"):
                    if hasattr(self, 'field_tolerance'):
                        setattr(self, 'field_tolerance', float(line.replace('FIELDTOLERANCE,', '').strip()))

            data_section = header_match.string[header_match.end():]
            data_section = data_section.replace(',Field',',Magnetic Field')
            data_buffer = StringIO(data_section)
            data_df = pd.read_csv(data_buffer, header=0, skipinitialspace=True, sep=',',engine='python')
            other_data = [key for key in data_df.keys() if 'ch1' not in key and 'ch2' not in key and 'map' not in key.lower()]
            all_data=[]

            # if archive.data.sequence_file:
            #     logger.info('Parsing PPMS measurement file using the sequence file.')
            #     indexlist=[]
            #     typelist=[]
            #     templist=[]
            #     fieldlist=[]
            #     #identify separate measurements by following the steps structure
            #     temp=float(data_df["Temperature (K)"].iloc[0])*self.temperature_tolerance.units
            #     field=float(data_df["Magnetic Field (Oe)"].iloc[0])*self.field_tolerance.units
            #     startval=0
            #     index=0
            #     measurement_type="undefined"
            #     measurement_active=False
            #     for step in self.steps:
            #         measurement_ends=False
            #         if isinstance(step,PPMSMeasurementSetTemperatureStep):
            #             if measurement_active:
            #                 if measurement_type!="undefined" and measurement_type!="temperature":
            #                     logger.error("Mixed measurement type found. Are sequence and data matching?")
            #                 measurement_type="temperature"
            #                 for i in range(index,len(data_df)):
            #                     if (abs(float(data_df["Temperature (K)"].iloc[i])*step.temperature_set.units-step.temperature_set)<self.temperature_tolerance and
            #                         abs(float(data_df["Magnetic Field (Oe)"].iloc[i])*self.field_tolerance.units-field)<self.field_tolerance):
            #                         index=i
            #                         break
            #                 else:
            #                     logger.error("Set temperature not found. Are sequence and data matching?")
            #                 for i in range(index,len(data_df)):
            #                     if (abs(float(data_df["Temperature (K)"].iloc[i])*step.temperature_set.units-step.temperature_set)>self.temperature_tolerance or
            #                         abs(float(data_df["Magnetic Field (Oe)"].iloc[i])*self.field_tolerance.units-field)>self.field_tolerance):
            #                         index=i
            #                         break
            #                 else:
            #                     index=i
            #             temp=step.temperature_set
            #         if isinstance(step,PPMSMeasurementSetMagneticFieldStep):
            #             if measurement_active:
            #                 if measurement_type!="undefined" and measurement_type!="field":
            #                     logger.error("Mixed measurement type found. Are sequence and data matching?")
            #                 measurement_type="field"
            #                 for i in range(index,len(data_df)):
            #                     if (abs(float(data_df["Magnetic Field (Oe)"].iloc[i])*step.field_set.units-step.field_set)<self.field_tolerance and
            #                         abs(float(data_df["Temperature (K)"].iloc[i])*self.temperature_tolerance.units-temp)<self.temperature_tolerance):
            #                         index=i
            #                         break
            #                 else:
            #                     logger.error("Set field not found. Are sequence and data matching?")
            #                 for i in range(index,len(data_df)):
            #                     if (abs(float(data_df["Magnetic Field (Oe)"].iloc[i])*step.field_set.units-step.field_set)>self.field_tolerance or
            #                         abs(float(data_df["Temperature (K)"].iloc[i])*self.temperature_tolerance.units-temp)>self.temperature_tolerance):
            #                         index=i
            #                         break
            #                 else:
            #                     index=i
            #             field=step.field_set
            #         if isinstance(step,PPMSMeasurementScanTempStep):
            #             if measurement_active:
            #                 logger.error("Measurement already active when approaching scan step. Is this sequence valid?")
            #             measurement_active=True
            #             measurement_type="temperature"
            #             if abs(float(data_df["Temperature (K)"].iloc[index])*step.initial_temp.units-step.initial_temp)>self.temperature_tolerance:
            #                 logger.error("Initial temperature not found in scan step. Are sequence and data matching?")
            #             for i in range(index,len(data_df)):
            #                 if (abs(float(data_df["Temperature (K)"].iloc[i])*step.initial_temp.units-step.final_temp)<self.temperature_tolerance and
            #                     abs(float(data_df["Magnetic Field (Oe)"].iloc[i])*self.field_tolerance.units-field)<self.field_tolerance):
            #                     index=i
            #                     break
            #             else:
            #                 logger.error("Set temperature not found. Are sequence and data matching?")
            #             for i in range(index,len(data_df)):
            #                 if (abs(float(data_df["Temperature (K)"].iloc[i])*step.initial_temp.units-step.final_temp)>self.temperature_tolerance or
            #                     abs(float(data_df["Magnetic Field (Oe)"].iloc[i])*self.field_tolerance.units-field)>self.field_tolerance):
            #                     index=i
            #                     break
            #             else:
            #                 index=i
            #             temp=step.final_temp
            #         if isinstance(step,PPMSMeasurementScanFieldStep):
            #             if measurement_active:
            #                 logger.error("Measurement already active when approaching scan step. Is this sequence valid?")
            #             measurement_active=True
            #             measurement_type="field"
            #             if abs(float(data_df["Magnetic Field (Oe)"].iloc[index])*step.initial_field.units-step.initial_field)>self.field_tolerance:
            #                 logger.error("Initial field not found in scan step. Are sequence and data matching?")
            #             for i in range(index,len(data_df)):
            #                 if (abs(float(data_df["Magnetic Field (Oe)"].iloc[i])*step.initial_field.units-step.final_field)<self.field_tolerance and
            #                     abs(float(data_df["Temperature (K)"].iloc[i])*self.temperature_tolerance.units-temp)<self.temperature_tolerance):
            #                     index=i
            #                     break
            #             else:
            #                 logger.error("Set field not found. Are sequence and data matching?")
            #             for i in range(index,len(data_df)):
            #                 if (abs(float(data_df["Magnetic Field (Oe)"].iloc[i])*step.initial_field.units-step.final_field)>self.field_tolerance or
            #                     abs(float(data_df["Temperature (K)"].iloc[i])*self.temperature_tolerance.units-temp)>self.temperature_tolerance):
            #                     index=i
            #                     break
            #             else:
            #                 index=i
            #             field=step.final_field
            #         if isinstance(step,PPMSMeasurementETOResistanceStep):
            #             if "Stop Measurement" in step.mode:
            #                 measurement_ends=False
            #             if "Start Continuous Measure" in step.mode or "Perform N Measurements" in step.mode:
            #                 measurement_active=True
            #         if isinstance(step,PPMSMeasurementScanTempEndStep):
            #             if not measurement_active:
            #                 logger.error("Measurement not running when approaching scan end step. Is this sequence valid?")
            #             if measurement_active:
            #                 if measurement_type!="undefined" and measurement_type!="temperature":
            #                     logger.error("Mixed measurement type found. Are sequence and data matching?")
            #             measurement_ends=True
            #         if isinstance(step,PPMSMeasurementScanFieldEndStep):
            #             if not measurement_active:
            #                 logger.error("Measurement not running when approaching scan end step. Is this sequence valid?")
            #             if measurement_active:
            #                 if measurement_type!="undefined" and measurement_type!="field":
            #                     logger.error("Mixed measurement type found. Are sequence and data matching?")
            #             measurement_ends=True
            #         if measurement_ends:
            #             measurement_active=False
            #             indexlist.append([startval,index])
            #             typelist.append(measurement_type)
            #             templist.append(temp)
            #             fieldlist.append(field)
            #             startval=index

            #Just for demo
            #else:
            #    logger.info('Parsing PPMS measurement file without using the sequence file.')
            if True:
                all_steps=[]
                indexlist=[]
                typelist=[]
                templist=[]
                fieldlist=[]
                startval=0
                measurement_type="undefined"
                block_found=False
                for i in range(len(data_df)):
                    if i==len(data_df)-1:
                        typelist.append(measurement_type)
                        block_found=True
                    elif measurement_type=="undefined":
                        for k in [2,5,10,20,40]:
                            if i+k-1>len(data_df):
                                continue
                            if abs(float(data_df["Temperature (K)"].iloc[i])-float(data_df["Temperature (K)"].iloc[i+k]))*self.temperature_tolerance.units<self.temperature_tolerance:
                                measurement_type="field"

                            if abs(float(data_df["Magnetic Field (Oe)"].iloc[i])-float(data_df["Magnetic Field (Oe)"].iloc[i+k]))*self.field_tolerance.units<self.field_tolerance:
                                if measurement_type=="undefined":
                                    measurement_type="temperature"
                                else:
                                    #logger.error("Can't identify measurement type in line "+str(i)+" with forward step "+str(k)+".")
                                    measurement_type="undefined"
                            if measurement_type!="undefined":
                                break
                        else:
                            logger.warning("Can't identify measurement type in line "+str(i)+".")
                    elif measurement_type=="field":
                        if abs(float(data_df["Temperature (K)"].iloc[i-1])-float(data_df["Temperature (K)"].iloc[i]))*self.temperature_tolerance.units>self.temperature_tolerance:
                            typelist.append("field")
                            block_found=True
                    elif measurement_type=="temperature":
                        if abs(float(data_df["Magnetic Field (Oe)"].iloc[i-1])-float(data_df["Magnetic Field (Oe)"].iloc[i]))*self.field_tolerance.units>self.field_tolerance:
                            typelist.append("temperature")
                            block_found=True
                    if block_found==True:
                        block_found=False
                        indexlist.append([startval,i])
                        startval=i
                        templist.append(np.round(float(data_df["Temperature (K)"].iloc[i-1]),1))
                        fieldlist.append(np.round(float(data_df["Magnetic Field (Oe)"].iloc[i-1]),-1))
                        if measurement_type=="temperature":
                            all_steps.append(PPMSMeasurementStep(name="Temperature sweep at "+str(fieldlist[-1])+" Oe."))
                        if measurement_type=="field":
                            all_steps.append(PPMSMeasurementStep(name="Field sweep at "+str(templist[-1])+" K."))
                        measurement_type="undefined"
                #self.steps=all_steps

            if self.software.startswith("ACTRANSPORT"):
                logger.info("Parsing AC Transport measurement.")
                logger.info(typelist)
                for i in range(len(indexlist)):
                    block=data_df.iloc[indexlist[i][0]:indexlist[i][1]]
                    data = ACTPPMSData()
                    data.measurement_type=typelist[i]
                    if  data.measurement_type=="field":
                        data.name="Field sweep at "+str(templist[i])+" K."
                        filename=self.data_file.strip(".dat")+"_field_sweep_"+str(templist[i])+"_K.dat"
                    if  data.measurement_type=="temperature":
                        data.name="Temperature sweep at "+str(fieldlist[i])+" Oe."
                        filename=self.data_file.strip(".dat")+"_temperature_sweep_"+str(fieldlist[i])+"_Oe.dat"
                    data.title=data.name
                    for key in other_data:
                        clean_key = key.split('(')[0].strip().replace(' ','_').lower()#.replace('time stamp','timestamp')
                        if hasattr(data, clean_key):
                            setattr(data,
                                    clean_key,
                                    block[key] # * ureg(data_template[f'{key}/@units'])
                                    )
                    channel_1_data = [key for key in block.keys() if 'ch1' in key.lower()]
                    if channel_1_data:
                        channel_1 = ACTChannelData()
                        setattr(channel_1, 'name', 'Channel 1')
                        for key in channel_1_data:
                            clean_key = clean_channel_keys(key)
                            if hasattr(channel_1, clean_key):
                                setattr(channel_1,
                                        clean_key,
                                        block[key] # * ureg(data_template[f'{key}/@units'])
                                        )
                        data.m_add_sub_section(ACTPPMSData.channels, channel_1)
                    channel_2_data = [key for key in block.keys() if 'ch2' in key.lower()]
                    if channel_2_data:
                        channel_2 = ACTChannelData()
                        setattr(channel_2, 'name', 'Channel 2')
                        for key in channel_2_data:
                            clean_key = clean_channel_keys(key)
                            if hasattr(channel_2, clean_key):
                                setattr(channel_2,
                                        clean_key,
                                        block[key] # * ureg(data_template[f'{key}/@units'])
                                        )
                        data.m_add_sub_section(ACTPPMSData.channels, channel_2)

                    map_data = [key for key in block.keys() if 'Map' in key]
                    if map_data:
                        for key in map_data:
                            map = ACTData()
                            if hasattr(map, 'name'):
                                setattr(map, 'name', key)
                            if hasattr(map, 'map'):
                                setattr(map, 'map', block[key])
                            data.m_add_sub_section(ACTPPMSData.maps, map)

                    #create raw output files
                    with archive.m_context.raw_file(filename, 'w') as outfile:
                        outfile.write(header_section+"\n")
                        block.to_csv(outfile,index=False,mode="a")

                    all_data.append(data)

            if self.software.startswith("Electrical Transport Option"):
                logger.info("Parsing ETO measurement.")
                logger.info(typelist)
                for i in range(len(indexlist)):
                    block=data_df.iloc[indexlist[i][0]:indexlist[i][1]]
                    data = ETOPPMSData()
                    data.measurement_type=typelist[i]
                    if  data.measurement_type=="field":
                        data.name="Field sweep at "+str(templist[i])+" K."
                        filename=self.data_file.strip(".dat")+"_field_sweep_"+str(templist[i])+"_K.dat"
                    if  data.measurement_type=="temperature":
                        data.name="Temperature sweep at "+str(fieldlist[i])+" Oe."
                        filename=self.data_file.strip(".dat")+"_temperature_sweep_"+str(fieldlist[i])+"_Oe.dat"
                    data.title=data.name
                    for key in other_data:
                        clean_key = key.split('(')[0].strip().replace(' ','_').lower()#.replace('time stamp','timestamp')
                        if hasattr(data, clean_key):
                            setattr(data,
                                    clean_key,
                                    block[key] # * ureg(data_template[f'{key}/@units'])
                                    )
                    channel_1_data = [key for key in block.keys() if 'ch1' in key.lower()]
                    if channel_1_data:
                        channel_1 = ETOChannelData()
                        setattr(channel_1, 'name', 'Channel 1')
                        for key in channel_1_data:
                            clean_key = clean_channel_keys(key)
                            if hasattr(channel_1, clean_key):
                                setattr(channel_1,
                                        clean_key,
                                        block[key] # * ureg(data_template[f'{key}/@units'])
                                        )
                        data.m_add_sub_section(ACTPPMSData.channels, channel_1)
                    channel_2_data = [key for key in block.keys() if 'ch2' in key.lower()]
                    if channel_2_data:
                        channel_2 = ETOChannelData()
                        setattr(channel_2, 'name', 'Channel 2')
                        for key in channel_2_data:
                            clean_key = clean_channel_keys(key)
                            if hasattr(channel_2, clean_key):
                                setattr(channel_2,
                                        clean_key,
                                        block[key] # * ureg(data_template[f'{key}/@units'])
                                        )
                        data.m_add_sub_section(ETOPPMSData.channels, channel_2)

                    eto_channel_data = [key for key in data_df.keys() if 'ETO Channel' in key]
                    if eto_channel_data:
                        for key in eto_channel_data:
                            eto_channel = ETOData()
                            if hasattr(eto_channel, 'name'):
                                setattr(eto_channel, 'name', key)
                            if hasattr(eto_channel, 'ETO_channel'):
                                setattr(eto_channel, 'ETO_channel', data_df[key])
                            data.m_add_sub_section(ETOPPMSData.eto_channels, eto_channel)

                    #create raw output files
                    with archive.m_context.raw_file(filename, 'w') as outfile:
                        outfile.write(header_section+"\n")
                        block.to_csv(outfile,index=False,mode="a")

                    all_data.append(data)

            self.data=all_data



            #Now create the according plots
            import plotly.express as px
            from plotly.subplots import make_subplots
            for data in self.data:
                if self.software.startswith("ACTRANSPORT"):
                    if data.measurement_type=="field":
                        resistivity_ch1=px.scatter(x=data.magnetic_field,y=data.channels[0].resistivity)
                        resistivity_ch2=px.scatter(x=data.magnetic_field,y=data.channels[1].resistivity)
                    if data.measurement_type=="temperature":
                        resistivity_ch1=px.scatter(x=data.temperature,y=data.channels[0].resistivity)
                        resistivity_ch2=px.scatter(x=data.temperature,y=data.channels[1].resistivity)
                if self.software.startswith("Electrical Transport Option"):
                    if data.measurement_type=="field":
                        resistivity_ch1=px.scatter(x=data.magnetic_field,y=data.channels[0].resistance)
                        resistivity_ch2=px.scatter(x=data.magnetic_field,y=data.channels[1].resistance)
                    if data.measurement_type=="temperature":
                        resistivity_ch1=px.scatter(x=data.temperature,y=data.channels[0].resistance)
                        resistivity_ch2=px.scatter(x=data.temperature,y=data.channels[1].resistance)
                figure1 = make_subplots(rows=2, cols=1, shared_xaxes=True)
                figure1.add_trace(resistivity_ch1.data[0], row=1, col=1)
                figure1.add_trace(resistivity_ch2.data[0], row=2, col=1)
                figure1.update_layout(height=400, width=716, title_text=data.name)
                self.figures.append(PlotlyFigure(label=data.name, figure=figure1.to_plotly_json()))

m_package.__init_metainfo__()