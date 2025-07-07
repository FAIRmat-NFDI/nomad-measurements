#
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

import numpy as np
from nomad.datamodel.data import (
    ArchiveSection,
)
from nomad.datamodel.metainfo.annotations import (
    ELNAnnotation,
)
from nomad.datamodel.metainfo.basesections import (
    CompositeSystemReference,
    MeasurementResult,
)
from nomad.metainfo import (
    MEnum,
    Quantity,
    Section,
    SubSection,
)


class QDSample(ArchiveSection):
    name = Quantity(type=str, description='Name/ID of the sample')
    type = Quantity(
        type=str, description='Type of the sample, e.g. single crystal, device,...'
    )
    material = Quantity(type=str, description='Sample material/ chemical formula')
    comment = Quantity(type=str, description='Any additional comments')
    lead_separation = Quantity(type=str, description='Distance of the contact leads')
    cross_section = Quantity(
        type=str, description='Cross section through which the current flows'
    )
    sample = SubSection(
        section_def=CompositeSystemReference,
        description='Reference to the sample measured',
    )


class QDResult(MeasurementResult):
    """
    Section for the results of a generic QD measurement
    """

    temperature = Quantity(
        type=np.dtype(np.float64),
        unit='kelvin',
        shape=['*'],
        description='Temperature of the sample',
    )
    magnetic_field = Quantity(
        type=np.dtype(np.float64),
        unit='gauss',
        shape=['*'],
        description='Applied magnetic field',
    )
    measurement_type = Quantity(
        type=str,
        description='Type of the measurement',
    )


class ETOResult(QDResult):
    """
    Section for the results of an ETO QD measurement
    """

    resistance0 = Quantity(
        type=np.dtype(np.float64),
        unit='ohm',
        shape=['*'],
        description='Measured resistance of the sample',
    )
    resistance1 = Quantity(
        type=np.dtype(np.float64),
        unit='ohm',
        shape=['*'],
        description='Measured resistance of the sample',
    )


class ACTResult(QDResult):
    """
    Section for the results of an ACT QD measurement
    """

    resistivity0 = Quantity(
        type=np.dtype(np.float64),
        unit='ohm/centimeter',
        shape=['*'],
        description='Channel 1 sample resistivity.',
    )
    resistivity1 = Quantity(
        type=np.dtype(np.float64),
        unit='ohm/centimeter',
        shape=['*'],
        description='Channel 1 sample resistivity.',
    )


class ACMSResult(QDResult):
    """
    Section for the results of an ACMS QD measurement
    """

    excitation = Quantity(
        type=np.dtype(np.float64),
        unit='mA',
        shape=['*'],
        description='Peak amplitude of the requested excitation current.',
    )
    frequency = Quantity(
        type=np.dtype(np.float64),
        unit='Hz',
        shape=['*'],
        description='Applied frequency of the excitation',
    )
    moment = Quantity(
        type=np.dtype(np.float64),
        unit='lux',
        shape=['*'],
        description='(AC only) total magnitude of the a.c. moment',
    )
    moment_derivative = Quantity(
        type=np.dtype(np.float64),
        unit='lux',
        shape=['*'],
        description='(AC only) real, “in-phase” component of the magnetic\
              susceptibility χ’ multiplied by the a.c. excitation.',
    )
    moment_second_derivative = Quantity(
        type=np.dtype(np.float64),
        unit='lux',
        shape=['*'],
        description='(AC only) imaginary, “out-of-phase” component of the magnetic\
            susceptibility χ’’ multiplied by the a.c. excitation.',
    )


class MPMSResult(QDResult):
    """
    Section for the results of an ACT QD measurement
    """

    moment = Quantity(
        type=np.dtype(np.float64),
        unit='lux',
        shape=['*'],
        description='average magnetic moment of the sample during measurement.',
    )


class ResistivityResult(QDResult):
    """
    Section for the results of an ACT QD measurement
    """

    bridge_1_resistivity = Quantity(
        type=np.dtype(np.float64),
        unit='ohm',
        shape=['*'],
        description='Resistivity of user bridge channel 1.',
    )
    bridge_2_resistivity = Quantity(
        type=np.dtype(np.float64),
        unit='ohm',
        shape=['*'],
        description='Resistivity of user bridge channel 1.',
    )


class QDData(ArchiveSection):
    """General data section from QD"""

    name = Quantity(
        type=str,
        description='Name of the section',
        a_eln={'component': 'StringEditQuantity'},
    )
    time_stamp = Quantity(
        type=np.dtype(np.float64),
        unit='second',
        shape=['*'],
        description='Time stamp of the measurement point',
    )
    temperature = Quantity(
        type=np.dtype(np.float64),
        unit='kelvin',
        shape=['*'],
        description='Temperature of the sample',
    )
    magnetic_field = Quantity(
        type=np.dtype(np.float64),
        unit='gauss',
        shape=['*'],
        description='Applied magnetic field',
    )


class ETOData(ArchiveSection):
    """Data section from Channels in QD"""

    m_def = Section(
        label_quantity='name',
    )
    name = Quantity(
        type=str,
        description='Name of the section',
        a_eln={'component': 'StringEditQuantity'},
    )
    eto_channel = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        description='Content of a single ETO Channel from the measurement',
    )


class ETOChannelData(ArchiveSection):
    """Data section from Channels in QD"""

    m_def = Section(
        label_quantity='name',
    )
    name = Quantity(
        type=str,
        description='Name of the section',
        a_eln={'component': 'StringEditQuantity'},
    )
    resistance = Quantity(
        type=np.dtype(np.float64),
        unit='ohm',
        shape=['*'],
        description='Measured resistance of the sample',
    )
    resistance_std_dev = Quantity(
        type=np.dtype(np.float64),
        unit='ohm',
        shape=['*'],
        description='Standard deviation of the measured resistance',
    )
    phase_angle = Quantity(
        type=np.dtype(np.float64),
        unit='deg',
        shape=['*'],
        description='Measured phase angle',
    )
    i_v_current = Quantity(
        type=np.dtype(np.float64),
        unit='mA',
        shape=['*'],
        description='Wave form of the current.',
    )
    i_v_voltage = Quantity(
        type=np.dtype(np.float64),
        unit='V',
        shape=['*'],
        description='Wave form of the voltage.',
    )
    frequency = Quantity(
        type=np.dtype(np.float64),
        unit='Hz',
        shape=['*'],
        description='Frequency of the excitation',
    )
    averaging_time = Quantity(
        type=np.dtype(np.float64),
        unit='second',
        shape=['*'],
        description='Averaging time per measurement point',
    )
    ac_current = Quantity(
        type=np.dtype(np.float64),
        unit='mA',
        shape=['*'],
        description='The peak voltage of the AC drive.',
    )
    dc_current = Quantity(
        type=np.dtype(np.float64),
        unit='mA',
        shape=['*'],
        description='The maximum DC voltage in the channel.',
    )
    current_ampl = Quantity(
        type=np.dtype(np.float64),
        unit='mA',
        shape=['*'],
        description='Magnitude of the current.',
    )
    in_phase_current = Quantity(
        type=np.dtype(np.float64),
        unit='mA',
        shape=['*'],
        description='The in-phase current amplitude.',
    )
    quadrature_current = Quantity(
        type=np.dtype(np.float64),
        unit='mA',
        shape=['*'],
        description='The out-of-phase current amplitude.',
    )
    gain = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        description='Total gain = Module gain X head gain.',
    )
    second_harmonic = Quantity(
        type=np.dtype(np.float64),
        unit='dB',
        shape=['*'],
        description='The in-phase voltage amplitude of the 2nd harmonic.',
    )
    third_harmonic = Quantity(
        type=np.dtype(np.float64),
        unit='dB',
        shape=['*'],
        description='The in-phase voltage amplitude of the 3rd harmonic.',
    )


class ETOQDData(QDData):
    """Data section from QD"""

    m_def = Section(
        a_eln=dict(lane_width='600px'),
    )
    sample_position = Quantity(
        type=np.dtype(np.float64),
        unit='deg',
        shape=['*'],
        description='Angle of the sample stage relative to the magnetic field.',
    )
    chamber_pressure = Quantity(
        type=np.dtype(np.float64),
        unit='torr',
        shape=['*'],
        description='Pressure inside the sample chamber.',
    )
    eto_measurement_mode = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        description='Integer indicating the measurement type for the row of data.',
    )
    temperature_status = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        description='An encoded integer containing information on the current status\
              of the temperature.',
    )
    field_status = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        description='An encoded integer containing information on the current status\
              of the field.',
    )
    chamber_status = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        description='An encoded integer containing information on the current status\
              of the chamber.',
    )
    eto_status_code = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        description='An encoded integer containing information on the current status\
              of the ETO hardware.',
    )
    channels = SubSection(section_def=ETOChannelData, repeats=True)
    maps = SubSection(section_def=ETOData, repeats=True)


class ACTData(ArchiveSection):
    """Data section from Channels in QD"""

    m_def = Section(
        label_quantity='name',
    )
    name = Quantity(
        type=str,
        description='Name of the section',
        a_eln={'component': 'StringEditQuantity'},
    )
    map = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        description='Content of a single ACT map from the measurement',
    )


class ACTChannelData(ArchiveSection):
    """Data section from Channels in QD"""

    m_def = Section(
        label_quantity='name',
    )
    name = Quantity(
        type=str,
        description='Name of the section',
        a_eln={'component': 'StringEditQuantity'},
    )
    volts = Quantity(
        type=np.dtype(np.float64),
        unit='V',
        shape=['*'],
        description='Measured voltage in A.C. Measurements, this is equal to\
              |V resistive|, the absolute value of the in-phase voltage.',
    )
    v_std_dev = Quantity(
        type=np.dtype(np.float64),
        unit='V',
        shape=['*'],
        description='Standard deviation of the measured voltage',
    )
    resistivity = Quantity(
        type=np.dtype(np.float64),
        unit='ohm/centimeter',
        shape=['*'],
        description='Channel 1 sample resistivity.',
    )
    resistivity_std_dev = Quantity(
        type=np.dtype(np.float64),
        unit='ohm/centimeter',
        shape=['*'],
        description='Standard deviation of the measured resistivity',
    )
    hall = Quantity(
        type=np.dtype(np.float64),
        unit='centimeter**3/coulomb',
        shape=['*'],
        description='This is merely the resistivity divided by the magnetic field –\
              one data point is NOT a trustworthy measure of the Hall coefficient due\
                  to voltage offsets that are inevitable in Hall measurements.',
    )
    hall_std_dev = Quantity(
        type=np.dtype(np.float64),
        unit='centimeter**3/coulomb',
        shape=['*'],
        description='Standard deviation of the measured Hall coefficient',
    )
    crit_cur = Quantity(
        type=np.dtype(np.float64),
        unit='mA',
        shape=['*'],
        description='Critical current as determined by the current at which the\
              voltage crosses the user-input voltage criterion.',
    )
    crit_cur_std_dev = Quantity(
        type=np.dtype(np.float64),
        unit='mA',
        shape=['*'],
        description='Error bar on the measurement of “Crit.Cur. ch1”, determined as\
              the standard error obtained by making repeated measurements.',
    )
    second_harmonic = Quantity(
        type=np.dtype(np.float64),
        unit='dB',
        shape=['*'],
        description='Magnitude of the 2nd harmonic content (voltage signal at\
              2*Frequency) in the reported voltage in A.C. Measurements.',
    )
    third_harmonic = Quantity(
        type=np.dtype(np.float64),
        unit='dB',
        shape=['*'],
        description='Magnitude of the 3rd harmonic content (voltage signal at\
              3*Frequency) in the reported voltage in A.C. Measurements.',
    )
    quad_error = Quantity(
        type=np.dtype(np.float64),
        unit='ohm/cm/rad',
        shape=['*'],
        description='This is the estimate of the error in the reported resistivity due\
              to the quadrature component of the resistivity.',
    )
    drive_signal = Quantity(
        type=np.dtype(np.float64),
        unit='V',
        shape=['*'],
        description='Total magnitude of the sample response on channel 1.',
    )


class ACTQDData(QDData):
    """Data section from QD"""

    m_def = Section(
        a_eln=dict(lane_width='600px'),
    )
    measurement_type = Quantity(
        type=MEnum(
            'temperature',
            'field',
        ),
        a_eln=ELNAnnotation(
            component='EnumEditQuantity',
        ),
    )
    status = Quantity(
        type=np.dtype(np.float64), shape=['*'], description='Status of the measurement'
    )
    sample_position = Quantity(
        type=np.dtype(np.float64),
        unit='deg',
        shape=['*'],
        description='Angle of the sample stage relative to the magnetic field.',
    )
    excitation = Quantity(
        type=np.dtype(np.float64),
        unit='mA',
        shape=['*'],
        description='Peak amplitude of the requested excitation current.',
    )
    frequency = Quantity(
        type=np.dtype(np.float64),
        unit='Hz',
        shape=['*'],
        description='Applied frequency of the excitation',
    )
    act_status = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        description='Indicates errors in ACT measurement;\
              zero indicates no errors were encountered.',
    )
    act_gain = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        description='Total gain which is product of gain in ACT preamp (1,10,100,1000)\
              and ACMS board gain (1,5,25,125).',
    )
    bridge_1_resistance = Quantity(
        type=np.dtype(np.float64),
        unit='ohm',
        shape=['*'],
        description='Resistance of user bridge channel 1.',
    )
    bridge_2_resistance = Quantity(
        type=np.dtype(np.float64),
        unit='ohm',
        shape=['*'],
        description='Resistance of user bridge channel 2.',
    )
    bridge_3_resistance = Quantity(
        type=np.dtype(np.float64),
        unit='ohm',
        shape=['*'],
        description='Resistance of user bridge channel 3.',
    )
    bridge_4_resistance = Quantity(
        type=np.dtype(np.float64),
        unit='ohm',
        shape=['*'],
        description='Resistance of user bridge channel 4.',
    )
    bridge_1_excitation = Quantity(
        type=np.dtype(np.float64),
        unit='microampere',
        shape=['*'],
        description='Excitation current of user bridge channel 1.',
    )
    bridge_2_excitation = Quantity(
        type=np.dtype(np.float64),
        unit='microampere',
        shape=['*'],
        description='Excitation current of user bridge channel 2.',
    )
    bridge_3_excitation = Quantity(
        type=np.dtype(np.float64),
        unit='microampere',
        shape=['*'],
        description='Excitation current of user bridge channel 3.',
    )
    bridge_4_excitation = Quantity(
        type=np.dtype(np.float64),
        unit='microampere',
        shape=['*'],
        description='Excitation current of user bridge channel 4.',
    )
    signal_1_vin = Quantity(
        type=np.dtype(np.float64),
        unit='V',
        shape=['*'],
        description='Input voltage for signal channel 1.',
    )
    signal_2_vin = Quantity(
        type=np.dtype(np.float64),
        unit='V',
        shape=['*'],
        description='Input voltage for signal channel 2.',
    )
    digital_inputs = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        description='Eight-bit status of selected inputs.',
    )
    drive_1_iout = Quantity(
        type=np.dtype(np.float64),
        unit='mA',
        shape=['*'],
        description='Current delivered by driver output channel 1.',
    )
    drive_2_iout = Quantity(
        type=np.dtype(np.float64),
        unit='mA',
        shape=['*'],
        description='Current delivered by driver output channel 2.',
    )
    drive_1_ipower = Quantity(
        type=np.dtype(np.float64),
        unit='watts',
        shape=['*'],
        description='Power delivered by driver output channel 1.',
    )
    drive_2_ipower = Quantity(
        type=np.dtype(np.float64),
        unit='watts',
        shape=['*'],
        description='Power delivered by driver output channel 2.',
    )
    pressure = Quantity(
        type=np.dtype(np.float64),
        unit='torr',
        shape=['*'],
        description='Pressure in sample chamber, measured in torr.',
    )
    channels = SubSection(section_def=ACTChannelData, repeats=True)
    maps = SubSection(section_def=ACTData, repeats=True)


class ACMSData(ArchiveSection):
    """Maps data section in ACMS"""

    m_def = Section(
        label_quantity='name',
    )
    name = Quantity(
        type=str,
        description='Name of the section',
        a_eln={'component': 'StringEditQuantity'},
    )
    map = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        description='User-designated data items.',
    )


class ACMSQDData(QDData):
    """Data section in ACMS"""

    m_def = Section(
        a_eln=dict(lane_width='600px'),
    )
    frequency = Quantity(
        type=np.dtype(np.float64),
        unit='Hz',
        shape=['*'],
        description='(AC only) frequency of applied excitation field.',
    )
    amplitude = Quantity(
        type=np.dtype(np.float64),
        unit='gauss',
        shape=['*'],
        description='(AC only) peak amplitude of applied excitation field.',
    )
    moment_dc = Quantity(
        type=np.dtype(np.float64),
        unit='lux',
        shape=['*'],
        description='(DC only) dc moment inferred from extraction of sample.',
    )
    moment_std_err = Quantity(
        type=np.dtype(np.float64),
        unit='lux',
        shape=['*'],
        description='error bar on the measurement of the moment, defined as the\
              standard error of the regression of the composite data waveform to the\
                ideal waveform, expressed in units of moment.',
    )
    moment_derivative = Quantity(
        type=np.dtype(np.float64),
        unit='lux',
        shape=['*'],
        description='(AC only) real, “in-phase” component of the magnetic\
              susceptibility χ’ multiplied by the a.c. excitation.',
    )
    moment_second_derivative = Quantity(
        type=np.dtype(np.float64),
        unit='lux',
        shape=['*'],
        description='(AC only) imaginary, “out-of-phase” component of the magnetic\
            susceptibility χ’’ multiplied by the a.c. excitation.',
    )
    moment = Quantity(
        type=np.dtype(np.float64),
        unit='lux',
        shape=['*'],
        description='(AC only) total magnitude of the a.c. moment',
    )
    phase = Quantity(
        type=np.dtype(np.float64),
        unit='deg',
        shape=['*'],
        description='(AC only) phase of the sample response relative to the\
              paramagnetic calibration coil signal.',
    )
    calcoil_derivative = Quantity(
        type=np.dtype(np.float64),
        unit='lux',
        shape=['*'],
        description='(AC only) in-phase component of the calibration coil signal.',
    )
    calcoil_second_derivative = Quantity(
        type=np.dtype(np.float64),
        unit='lux',
        shape=['*'],
        description='(AC only) out-of-phase component of calibration coil signal.',
    )
    calcoil = Quantity(
        type=np.dtype(np.float64),
        unit='lux',
        shape=['*'],
        description='(AC only) total magnitude of calibration coil signal.',
    )
    cc_phase = Quantity(
        type=np.dtype(np.float64),
        unit='deg',
        shape=['*'],
        description='(AC only) phase of calibration coil response relative to\
              a paramagnetic response.',
    )
    count = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        description='number of waveforms that were averaged to produce this data\
              point.',
    )
    gain = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        description='total gain applied to sample response.',
    )
    measure_type = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        description='(AC only) measurement mode, where 5-point\
              (bottom-top-bottom-center-center) is the default.',
    )
    elapsed = Quantity(
        type=np.dtype(np.float64),
        unit='second',
        shape=['*'],
        description='total time required to collect this data point.',
    )
    sample_center = Quantity(
        type=np.dtype(np.float64),
        unit='cm',
        shape=['*'],
        description='sample location as determined by the last centering operation.\
              The scale correlates with motor position, with the origin being the\
                  ideal location for a sample.',
    )
    max_signal = Quantity(
        type=np.dtype(np.float64),
        unit='V',
        shape=['*'],
        description='maximum peak-to-peak signal seen at the detection coils.',
    )
    ppms_status = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        description='defined in Appendix A of PPMS Firmware Manual. This can also be\
              decoded in MultiVu under “Utilities > Status Calculator...”',
    )
    dsp_status = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        description='value of zero indicates the measurement completed without\
              any errors or warnings.',
    )
    min_temperature = Quantity(
        type=np.dtype(np.float64),
        unit='K',
        shape=['*'],
        description='minimum temperature during the measurement.',
    )
    max_temperature = Quantity(
        type=np.dtype(np.float64),
        unit='K',
        shape=['*'],
        description='maximum temperature during the measurement.',
    )
    min_field = Quantity(
        type=np.dtype(np.float64),
        unit='gauss',
        shape=['*'],
        description='minimum field during the measurement.',
    )
    max_field = Quantity(
        type=np.dtype(np.float64),
        unit='gauss',
        shape=['*'],
        description='maximum field during the measurement.',
    )
    dc_position = Quantity(
        type=np.dtype(np.float64),
        unit='cm',
        shape=['*'],
        description='(DC only) sample location inferred from curve fit to the\
             extraction waveform where the position of the sample is a fit parameter.',
    )
    ppms_temperature = Quantity(
        type=np.dtype(np.float64),
        unit='K',
        shape=['*'],
        description='temperature of the PPMS thermometer located at the bottom\
              of the sample chamber.',
    )
    ppms_position = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        description='Position of the PPMS sample holder in the chamber.',
    )
    bridge_1_resistance = Quantity(
        type=np.dtype(np.float64),
        unit='ohm',
        shape=['*'],
        description='Resistance of user bridge channel 1.',
    )
    bridge_1_excitation = Quantity(
        type=np.dtype(np.float64),
        unit='uA',
        shape=['*'],
        description='Excitation current of user bridge channel 1.',
    )
    bridge_2_resistance = Quantity(
        type=np.dtype(np.float64),
        unit='ohm',
        shape=['*'],
        description='Resistance of user bridge channel 2.',
    )
    bridge_2_excitation = Quantity(
        type=np.dtype(np.float64),
        unit='uA',
        shape=['*'],
        description='Excitation current of user bridge channel 2.',
    )
    bridge_3_resistance = Quantity(
        type=np.dtype(np.float64),
        unit='ohm',
        shape=['*'],
        description='Resistance of user bridge channel 3.',
    )
    bridge_3_excitation = Quantity(
        type=np.dtype(np.float64),
        unit='uA',
        shape=['*'],
        description='Excitation current of user bridge channel 3.',
    )
    bridge_4_resistance = Quantity(
        type=np.dtype(np.float64),
        unit='ohm',
        shape=['*'],
        description='Resistance of user bridge channel 4.',
    )
    bridge_4_excitation = Quantity(
        type=np.dtype(np.float64),
        unit='uA',
        shape=['*'],
        description='Excitation current of user bridge channel 4.',
    )
    signal_1_vin = Quantity(
        type=np.dtype(np.float64),
        unit='V',
        shape=['*'],
        description='Input voltage for signal channel 1.',
    )
    signal_2_vin = Quantity(
        type=np.dtype(np.float64),
        unit='V',
        shape=['*'],
        description='Input voltage for signal channel 2.',
    )
    digital_inputs = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        description='Eight-bit status of selected inputs.',
    )
    drive_1_iout = Quantity(
        type=np.dtype(np.float64),
        unit='mA',
        shape=['*'],
        description='Current delivered by driver output channel 1.',
    )
    drive_1_ipower = Quantity(
        type=np.dtype(np.float64),
        unit='W',
        shape=['*'],
        description='Power delivered by driver output channel 1.',
    )
    drive_2_iout = Quantity(
        type=np.dtype(np.float64),
        unit='mA',
        shape=['*'],
        description='Current delivered by driver output channel 2.',
    )
    drive_2_ipower = Quantity(
        type=np.dtype(np.float64),
        unit='W',
        shape=['*'],
        description='Power delivered by driver output channel 2.',
    )
    pressure = Quantity(
        type=np.dtype(np.float64),
        unit='torr',
        shape=['*'],
        description='Pressure in sample chamber, measured in torr.',
    )
    #!TODO: change unit to emu or similar, for now lux=emu
    maps = SubSection(section_def=ACMSData, repeats=True)


class MPMSData(ArchiveSection):
    """Maps data section in MPMS"""

    m_def = Section(
        label_quantity='name',
    )
    name = Quantity(
        type=str,
        description='Name of the section',
        a_eln={'component': 'StringEditQuantity'},
    )
    map = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        description='Mappable data columns (varying content).',
    )


class MPMSDCData(ArchiveSection):
    """MPMS data about the DC parameters"""

    m_def = Section(
        label_quantity='name',
    )
    dc_moment_fixed_ctr = Quantity(
        type=np.dtype(np.float64),
        unit='lux',
        shape=['*'],
        description='Amplitude of the moment for DC scan measurements (fixed center).',
    )
    dc_moment_err_fixed_ctr = Quantity(
        type=np.dtype(np.float64),
        unit='lux',
        shape=['*'],
        description='Amplitude of the associated standard error of the moment for\
              DC scan measurements (fixed center).',
    )
    dc_moment_free_ctr = Quantity(
        type=np.dtype(np.float64),
        unit='lux',
        shape=['*'],
        description='Amplitude of the moment for DC scan measurements (free center).',
    )
    dc_moment_err_free_ctr = Quantity(
        type=np.dtype(np.float64),
        unit='lux',
        shape=['*'],
        description='Amplitude of the associated standard error of the moment for\
              DC scan measurements (free center).',
    )
    dc_fixed_fit = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        description='Quality of fit of the raw data to the dipole response function\
              for the “Fixed Center” fits, respectively',
    )
    dc_free_fit = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        description='Quality of fit of the raw data to the dipole response function\
              for the “Free Center” fits, respectively',
    )
    dc_calculated_center = Quantity(
        type=np.dtype(np.float64),
        unit='mm',
        shape=['*'],
        description='Calculated sample position for the “Free Center” fit to the\
              DC scan raw data.',
    )
    dc_calculated_center_err = Quantity(
        type=np.dtype(np.float64),
        unit='mm',
        shape=['*'],
        description='Calculated associated error of the sample position for the\
              “Free Center” fit to the DC scan raw data.',
    )
    dc_scan_length = Quantity(
        type=np.dtype(np.float64),
        unit='mm',
        shape=['*'],
        description='Scan length of the current data point (as selected by the user\
              in the “Measure” menu).',
    )
    dc_scan_time = Quantity(
        type=np.dtype(np.float64),
        unit='second',
        shape=['*'],
        description='Scan time of the current data point (as selected by user in\
              the “Measure” menu).',
    )
    dc_number_of_points = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        description='Number of points in the raw DC scan waveform.',
    )
    dc_squid_drift = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        description='SQUID drift calculated from the subtraction of the up and down\
              measurement scans.',
    )
    dc_min_v = Quantity(
        type=np.dtype(np.float64),
        unit='V',
        shape=['*'],
        description='Minimum voltage reported by the SQUID module during the DC scan.',
    )
    dc_max_v = Quantity(
        type=np.dtype(np.float64),
        unit='V',
        shape=['*'],
        description='Maximum voltage reported by the SQUID module during the DC scan.',
    )
    dc_scans_per_measure = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        description='Number of DC scans per measurement point',
    )


class MPMSQDData(QDData):
    """Data section in MPMS"""

    m_def = Section(
        a_eln=dict(lane_width='600px'),
    )
    #!TODO: change unit to emu or similar, for now lux=emu
    moment = Quantity(
        type=np.dtype(np.float64),
        unit='lux',
        shape=['*'],
        description='average magnetic moment of the sample during measurement.',
    )
    moment_std_err = Quantity(
        type=np.dtype(np.float64),
        unit='lux',
        shape=['*'],
        description='standard error (i.e., the error of the mean) for the measurement.',
    )
    transport_action = Quantity(
        type=np.dtype(np.float64),
        unit='lux',
        shape=['*'],
        description='1 = measurement; 2 = auto-touchdown; 3 = manual touchdown',
    )
    averaging_time = Quantity(
        type=np.dtype(np.float64),
        unit='second',
        shape=['*'],
        description='(number of cycles per measurement)/frequency (as calculated)',
    )
    frequency = Quantity(
        type=np.dtype(np.float64),
        unit='Hz',
        shape=['*'],
        description='frequency of sample oscillation',
    )
    peak_amplitude = Quantity(
        type=np.dtype(np.float64),
        unit='mm',
        shape=['*'],
        description='peak amplitude of oscillation, such that position z(t) = Asinωt',
    )
    center_position = Quantity(
        type=np.dtype(np.float64),
        unit='mm',
        shape=['*'],
        description='average position of the transport over the measurement',
    )
    lockin_signal_derivative = Quantity(
        type=np.dtype(np.float64),
        unit='V',
        shape=['*'],
        description='Derivative of the signal of the lock-in amplifier.',
    )
    lockin_signal = Quantity(
        type=np.dtype(np.float64),
        unit='V',
        shape=['*'],
        description='Signal of the lock-in amplifier.',
    )
    range = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        description='Range of the lock-in amplifier.',
    )
    moment_quad_signal = Quantity(
        type=np.dtype(np.float64),
        unit='lux',
        shape=['*'],
        description='Quadratic component of the moment.',
    )
    min_temperature = Quantity(
        type=np.dtype(np.float64),
        unit='K',
        shape=['*'],
        description='Minimum sample temperature readings over the time required to\
              measure the current data point.',
    )
    max_temperature = Quantity(
        type=np.dtype(np.float64),
        unit='K',
        shape=['*'],
        description='Maximum sample temperature readings over the time required to\
              measure the current data point.',
    )
    min_field = Quantity(
        type=np.dtype(np.float64),
        unit='gauss',
        shape=['*'],
        description='Minimum sample field readings over the time required to measure\
              the current data point.',
    )
    max_field = Quantity(
        type=np.dtype(np.float64),
        unit='gauss',
        shape=['*'],
        description='Maximum sample field readings over the time required to measure\
              the current data point.',
    )
    mass = Quantity(
        type=np.dtype(np.float64),
        unit='g',
        shape=['*'],
        description='Total mass of moving parts obtained from the DC component of the\
              motor force.',
    )
    motor_lag = Quantity(
        type=np.dtype(np.float64),
        unit='deg',
        shape=['*'],
        description='Phase lag between motor drive current and actual motor position.',
    )
    pressure = Quantity(
        type=np.dtype(np.float64),
        unit='torr',
        shape=['*'],
        description='Pressure inside the sample chamber for the current data point.',
    )
    measure_count = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        description='Total number of waveforms used to calculate the current data\
              point.',
    )
    measurement_number = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        description='Measurement repetition number for MvsH and MvsT measurements.',
    )
    squid_status = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        description='Internal status codes as reported by the SQUID module.',
    )
    motor_status = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        description='Internal status codes as reported by the motor module.',
    )
    measure_status = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        description='0 OK; 1 SQUID voltage railed',
    )
    motor_current = Quantity(
        type=np.dtype(np.float64),
        unit='A',
        shape=['*'],
        description='AC component of the motor current.',
    )
    motor_temperature = Quantity(
        type=np.dtype(np.float64),
        unit='celsius',
        shape=['*'],
        description='Temperature of the heat sink inside the motor module.',
    )
    temperature_status = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        description='Temperature status code as reported by the temperature control\
              subsystem.',
    )
    field_status = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        description='Field status code as reported by the magnet power supply.',
    )
    chamber_status = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        description='Chamber status code as reported by the Gas handling controller.',
    )
    chamber_temp = Quantity(
        type=np.dtype(np.float64),
        unit='K',
        shape=['*'],
        description='Chamber temperature for the current data point.',
    )
    redirection_state = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        description='0 No redirection; 1 Oven option active and controlling\
              temperature',
    )
    average_temp = Quantity(
        type=np.dtype(np.float64),
        unit='K',
        shape=['*'],
        description='Average temperature during the measurement point.',
    )
    rotation_angle = Quantity(
        type=np.dtype(np.float64),
        unit='deg',
        shape=['*'],
        description='Angle of the sample rotator.',
    )
    rotator_state = Quantity(
        type=np.dtype(np.float64), shape=['*'], description='Status of the rotator.'
    )
    sample_position = Quantity(
        type=np.dtype(np.float64),
        unit='deg',
        shape=['*'],
        description='Angle of the sample stage relative to the magnetic field.',
    )
    chamber_pressure = Quantity(
        type=np.dtype(np.float64),
        unit='torr',
        shape=['*'],
        description='Pressure inside the sample chamber.',
    )
    eto_measurement_mode = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        description='Integer indicating the measurement type for the row of data.',
    )
    eto_status_code = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        description='An encoded integer containing information on the current status\
              of the ETO hardware.',
    )
    maps = SubSection(section_def=MPMSData, repeats=True)
    dc_data = SubSection(section_def=MPMSDCData)


class ResistivityQDData(QDData):
    """Data section in Resistivity"""

    m_def = Section(
        a_eln=dict(lane_width='600px'),
    )
    status = Quantity(
        type=np.dtype(np.float64), shape=['*'], description='Status of the measurement'
    )
    sample_position = Quantity(
        type=np.dtype(np.float64),
        unit='deg',
        shape=['*'],
        description='Position of the sample in the device',
    )
    number_of_readings = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        description='Number of readings for averaging on the data point.',
    )
    bridge_1_resistance = Quantity(
        type=np.dtype(np.float64),
        unit='ohm',
        shape=['*'],
        description='Resistance of user bridge channel 1.',
    )
    bridge_1_resistivity = Quantity(
        type=np.dtype(np.float64),
        unit='ohm',
        shape=['*'],
        description='Resistivity of user bridge channel 1.',
    )
    bridge_1_std_dev = Quantity(
        type=np.dtype(np.float64),
        unit='ohm',
        shape=['*'],
        description='Standard deviation of user bridge channel 1.',
    )
    bridge_1_excitation = Quantity(
        type=np.dtype(np.float64),
        unit='uA',
        shape=['*'],
        description='Excitation current of user bridge channel 1.',
    )
    bridge_2_resistance = Quantity(
        type=np.dtype(np.float64),
        unit='ohm',
        shape=['*'],
        description='Resistance of user bridge channel 2.',
    )
    bridge_2_resistivity = Quantity(
        type=np.dtype(np.float64),
        unit='ohm',
        shape=['*'],
        description='Resistivity of user bridge channel 2.',
    )
    bridge_2_std_dev = Quantity(
        type=np.dtype(np.float64),
        unit='ohm',
        shape=['*'],
        description='Standard deviation of user bridge channel 2.',
    )
    bridge_2_excitation = Quantity(
        type=np.dtype(np.float64),
        unit='uA',
        shape=['*'],
        description='Excitation current of user bridge channel 2.',
    )
    bridge_3_resistance = Quantity(
        type=np.dtype(np.float64),
        unit='ohm',
        shape=['*'],
        description='Resistance of user bridge channel 3.',
    )
    bridge_3_resistivity = Quantity(
        type=np.dtype(np.float64),
        unit='ohm',
        shape=['*'],
        description='Resistivity of user bridge channel 3.',
    )
    bridge_3_std_dev = Quantity(
        type=np.dtype(np.float64),
        unit='ohm',
        shape=['*'],
        description='Standard deviation of user bridge channel 3.',
    )
    bridge_3_excitation = Quantity(
        type=np.dtype(np.float64),
        unit='uA',
        shape=['*'],
        description='Excitation current of user bridge channel 3.',
    )
    bridge_4_resistance = Quantity(
        type=np.dtype(np.float64),
        unit='ohm',
        shape=['*'],
        description='Resistance of user bridge channel 4.',
    )
    bridge_4_resistivity = Quantity(
        type=np.dtype(np.float64),
        unit='ohm',
        shape=['*'],
        description='Resistivity of user bridge channel 4.',
    )
    bridge_4_std_dev = Quantity(
        type=np.dtype(np.float64),
        unit='ohm',
        shape=['*'],
        description='Standard deviation of user bridge channel 4.',
    )
    bridge_4_excitation = Quantity(
        type=np.dtype(np.float64),
        unit='uA',
        shape=['*'],
        description='Excitation current of user bridge channel 4.',
    )
