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

from datetime import datetime

import numpy as np

from nomad_measurements.ppms.ppmsdatastruct import (
    ACMSData,
    ACMSPPMSData,
    ACTChannelData,
    ACTData,
    ACTPPMSData,
    ETOChannelData,
    ETOData,
    ETOPPMSData,
)
from nomad_measurements.ppms.ppmssteps import (
    PPMSMeasurementACTResistanceStep,
    PPMSMeasurementETOResistanceStep,
    PPMSMeasurementRemarkStep,
    PPMSMeasurementScanFieldEndStep,
    PPMSMeasurementScanFieldStep,
    PPMSMeasurementScanTempEndStep,
    PPMSMeasurementScanTempStep,
    PPMSMeasurementSetMagneticFieldStep,
    PPMSMeasurementSetPositionStep,
    PPMSMeasurementSetTemperatureStep,
    PPMSMeasurementStep,
    PPMSMeasurementWaitStep,
)


def clean_channel_keys(input_key: str) -> str:
    output_key = (
        input_key.split('(')[0]
        .replace('M. Std. Err.', 'moment std err')
        .replace('M-Std.Err.', 'moment std err')
        .replace('M-DC', 'moment dc')
        .replace("M''", 'moment second derivative')
        .replace("M'", 'moment derivative')
        .replace("Calcoil''", 'calcoil second derivative')
        .replace("Calcoil'", 'calcoil derivative')
        .replace("Signal'", 'Signal Derivative')
        .replace('M. Quad. Signal', 'moment quad signal')
        .replace('Std. Dev.', 'std dev')
        .replace('Std.Dev.', 'std dev')
        .replace('Res.', 'resistivity')
        .replace('Crit.Cur.', 'crit cur')
        .replace('C.Cur.', 'crit cur')
        .replace('Quad.Error', 'quad error')
        .replace('Harm.', 'harmonic')
        .replace('Min.', 'min ')
        .replace('Max.', 'max ')
        .replace('Temp.', 'temperature')
        .replace('-', ' ')
        .replace('Field (Oe)', 'Magnetic Field (Oe)')
        .lower()
        .replace('ch1', '')
        .replace('ch2', '')
        .strip()
        .replace('\s+', '_')
        .replace('3rd', 'third')
        .replace('2nd', 'second')
    )
    return output_key


def find_ppms_steps_from_sequence(sequence):  # noqa: PLR0912, PLR0915
    all_steps = []
    for line in sequence:
        if line.startswith('!'):
            continue
        elif line.startswith('REM '):
            all_steps.append(
                PPMSMeasurementRemarkStep(
                    name='Remark: ' + line[4:],
                    remark_text=line[4:],
                )
            )
        elif line.startswith('WAI '):
            details = line.split()
            onerror = ['No Action', 'Abort', 'Shutdown']
            all_steps.append(
                PPMSMeasurementWaitStep(
                    name='Wait for ' + details[2] + ' s.',
                    delay=float(details[2]),
                    condition_temperature=bool(int(details[3])),
                    condition_field=bool(int(details[4])),
                    condition_position=bool(int(details[5])),
                    condition_chamber=bool(int(details[6])),
                    on_error_execute=onerror[int(details[7])],
                )
            )
        elif line.startswith('MVP'):
            details = line.split()
            mode = [
                'Move to position',
                'Move to index and define',
                'Redefine present position',
            ]
            all_steps.append(
                PPMSMeasurementSetPositionStep(
                    name='Move sample to position ' + details[2] + '.',
                    position_set=float(details[2]),
                    position_rate=float(details[5].strip('"')),
                    mode=mode[int(details[3])],
                )
            )
        elif line.startswith('TMP'):
            details = line.split()
            mode = ['Fast Settle', 'No Overshoot']
            all_steps.append(
                PPMSMeasurementSetTemperatureStep(
                    name='Set temperature to '
                    + details[2]
                    + ' K with '
                    + details[3]
                    + ' K/min.',  # noqa: E501
                    temperature_set=float(details[2]),
                    temperature_rate=float(details[3]) / 60.0,
                    mode=mode[int(details[4])],
                )
            )
        elif line.startswith('FLD'):
            details = line.split()
            approach = ['Linear', 'No Overshoot', 'Oscillate']
            end_mode = ['Persistent', 'Driven']
            all_steps.append(
                PPMSMeasurementSetMagneticFieldStep(
                    name='Set field to '
                    + details[2]
                    + ' Oe with '
                    + details[3]
                    + ' Oe/min.',  # noqa: E501
                    field_set=float(details[2]),
                    field_rate=float(details[3]),
                    approach=approach[int(details[4])],
                    end_mode=end_mode[int(details[5])],
                )
            )
        elif line.startswith('LPB'):
            details = line.split()
            spacing_code = ['Uniform', 'H*H', 'H^1/2', '1/H', 'log(H)']
            approach = ['Linear', 'No Overshoot', 'Oscillate', 'Sweep']
            end_mode = ['Persistent', 'Driven']
            all_steps.append(
                PPMSMeasurementScanFieldStep(
                    name='Scan field from '
                    + details[2]
                    + ' Oe to '
                    + details[3]
                    + ' Oe.',
                    initial_field=float(details[2]),
                    final_field=float(details[3]),
                    spacing_code=spacing_code[int(details[6])],
                    rate=float(details[4]),
                    number_of_steps=int(details[5]),
                    approach=approach[int(details[7])],
                    end_mode=end_mode[int(details[8])],
                )
            )
        elif line.startswith('ENB'):
            all_steps.append(PPMSMeasurementScanFieldEndStep(name='End Field Scan.'))
        elif line.startswith('LPT'):
            details = line.split()
            spacing_code = ['Uniform', '1/T', 'log(T)']
            approach = ['Fast', 'No Overshoot', 'Sweep']
            all_steps.append(
                PPMSMeasurementScanTempStep(
                    name='Scan temperature from '
                    + details[2]
                    + ' K to '
                    + details[3]
                    + ' K.',  # noqa: E501
                    initial_temp=float(details[2]),
                    final_temp=float(details[3]),
                    spacing_code=spacing_code[int(details[6])],
                    rate=float(details[4]) / 60.0,
                    number_of_steps=int(details[5]),
                    approach=approach[int(details[7])],
                )
            )
        elif line.startswith('ENT'):
            all_steps.append(
                PPMSMeasurementScanTempEndStep(name='End Temperature Scan.')
            )
        elif line.startswith('ACTR'):
            details = line.split()
            autorange = ['Fixed Gain', 'Always Autorange', 'Sticky Autorange']
            fixedgain = [
                5,
                1,
                0.5,
                0.2,
                0.1,
                0.05,
                0.04,
                0.02,
                0.01,
                0.005,
                0.004,
                0.002,
                0.001,
                0.0004,
                0.0002,
                0.00004,
            ]
            all_steps.append(
                PPMSMeasurementACTResistanceStep(
                    name='AC Transport Resistance measurement.',
                    measurement_active=[
                        bool(int(details[4])),
                        bool(int(details[12])),
                    ],
                    excitation=[
                        float(details[5]) / 1000,
                        float(details[13]) / 1000,
                    ],
                    frequency=[float(details[6]), float(details[14])],
                    duration=[float(details[7]), float(details[15])],
                    constant_current_mode=[
                        bool(int(details[8])),
                        bool(int(details[16])),
                    ],
                    low_resistance_mode=[
                        bool(int(details[11])),
                        bool(int(details[19])),
                    ],
                    autorange=[
                        autorange[int(details[9])],
                        autorange[int(details[17])],
                    ],
                    fixed_gain=[
                        fixedgain[int(details[10])],
                        fixedgain[int(details[18])],
                    ],
                )
            )
        elif line.startswith('ETOR'):
            details = line.split()
            mode = [
                'Do Nothing',
                'Start Excitation',
                'Start Continuous Measure',
                'Perform N Measurements',
                'Stop Measurement',
                'Stop Excitation',
            ]
            sample_wiring = ['4-wire', '2-wire']
            shift = 0
            name = ''
            mode_int = []
            number_of_measure = []
            amplitude = []
            frequency = []
            wiring = []
            autorange = []
            averaging_time = []
            for i in range(2):
                mode_int.append(int(details[3 + shift]))
                if mode_int[i] in [0, 4, 5]:
                    number_of_measure.append(0)
                    amplitude.append(0)
                    frequency.append(0)
                    wiring.append(0)
                    autorange.append(False)
                    averaging_time.append(0)
                    shift += 1
                elif mode_int[i] in [1, 2, 3]:
                    if mode_int[i] == 3:  # noqa: PLR2004
                        number_of_measure.append(int(details[4 + shift]))
                        shift += 1
                    else:
                        number_of_measure.append(0)
                    amplitude.append(float(details[5 + shift]) / 1000.0)
                    frequency.append(float(details[6 + shift]))
                    wiring.append(int(details[12 + shift]))
                    autorange.append(bool(int(details[8 + shift])))
                    averaging_time.append(float(details[7 + shift]))
                    shift += 10
                name += 'Channel ' + str(i + 1) + ': ' + mode[mode_int[i]]
                if i == 0:
                    name += '; '
            all_steps.append(
                PPMSMeasurementETOResistanceStep(
                    name=name,
                    mode=[mode[mode_int[0]], mode[mode_int[1]]],
                    excitation_amplitude=amplitude,
                    excitation_frequency=frequency,
                    preamp_sample_wiring=[
                        sample_wiring[wiring[0]],
                        sample_wiring[wiring[1]],
                    ],
                    preamp_autorange=autorange,
                    config_averaging_time=averaging_time,
                    config_number_of_measurements=number_of_measure,
                )
            )
        elif line.startswith('SHT'):
            continue
        elif line.startswith('CHN'):
            continue
        else:
            # TODO: add error back for wrong/unknown steps
            continue
            # logger.error('Found unknown keyword ' + line[:4])
    return all_steps


def get_fileopentime(line_time):
    try:
        iso_date = datetime.strptime(line_time.split(',')[3], '%m/%d/%Y %H:%M:%S')
    except ValueError:
        try:
            iso_date = datetime.strptime(
                ' '.join(line_time.split(',')[2:4]), '%m-%d-%Y %I:%M %p'
            )
        except ValueError:
            try:
                iso_date = datetime.strptime(
                    line_time.split(',')[3], '%Y-%m-%d %H:%M:%S'
                )
            except ValueError:
                try:
                    iso_date = datetime.strptime(
                        line_time.split(',')[3], '%m/%d/%Y %I:%M:%S %p'
                    )
                except ValueError:
                    try:
                        iso_date = datetime.strptime(
                            ' '.join(line_time.split(',')[2:]), '%m/%d/%Y %I:%M %p'
                        )
                    except ValueError:
                        iso_date = 'Not found.'
    return iso_date


def get_ppms_steps_from_data(data, temperature_tolerance, field_tolerance):  # noqa: PLR0912
    all_steps = []
    runs_list = []

    startval = 0
    measurement_type = 'undefined'
    block_found = False
    for i in range(len(data)):
        if i == len(data) - 1:
            block_found = True
        elif measurement_type == 'undefined':
            for k in [2, 5, 10, 20, 40]:
                if i + k - 1 > len(data):
                    continue
                if (
                    abs(
                        float(data['Temperature (K)'].iloc[i])
                        - float(data['Temperature (K)'].iloc[i + k])
                    )
                    * temperature_tolerance.units
                    < temperature_tolerance
                ):
                    measurement_type = 'field'

                if (
                    abs(
                        float(data['Magnetic Field (Oe)'].iloc[i])
                        - float(data['Magnetic Field (Oe)'].iloc[i + k])
                    )
                    * field_tolerance.units
                    < field_tolerance
                ):
                    if measurement_type == 'undefined':
                        measurement_type = 'temperature'
                    else:
                        measurement_type = 'undefined'
                if measurement_type != 'undefined':
                    break
                    # TODO: Add back error messages
                    # else:
                    # logger.warning(
                    "Can't identify measurement type in line "
                    +str(i)
                    +'.'
                # )
        elif measurement_type == 'field':
            if (
                abs(
                    float(data['Temperature (K)'].iloc[i - 1])
                    - float(data['Temperature (K)'].iloc[i])
                )
                * temperature_tolerance.units
                > temperature_tolerance
            ):
                block_found = True
        elif measurement_type == 'temperature':
            if (
                abs(
                    float(data['Magnetic Field (Oe)'].iloc[i - 1])
                    - float(data['Magnetic Field (Oe)'].iloc[i])
                )
                * field_tolerance.units
                > field_tolerance
            ):
                block_found = True
        if block_found:
            block_found = False
            if measurement_type == 'temperature':
                value = np.round(float(data['Magnetic Field (Oe)'].iloc[i - 1]), -1)
                all_steps.append(
                    PPMSMeasurementStep(
                        name='Temperature sweep at ' + str(value) + ' Oe.'
                    )
                )
            if measurement_type == 'field':
                value = np.round(float(data['Temperature (K)'].iloc[i - 1]), 1)
                all_steps.append(
                    PPMSMeasurementStep(name='Field sweep at ' + str(value) + ' K.')
                )
            runs_list.append([measurement_type, value, startval, i])
            startval = i
            measurement_type = 'undefined'

    return all_steps, runs_list


def split_ppms_data_act(data_full, runs):  # noqa: PLR0912
    all_data = []
    for i in range(len(runs)):
        block = data_full.iloc[runs[i][2] : runs[i][3]]
        data = ACTPPMSData()
        data.measurement_type = runs[i][0]
        if data.measurement_type == 'field':
            data.name = 'Field sweep at ' + str(runs[i][1]) + ' K.'
        if data.measurement_type == 'temperature':
            data.name = 'Temperature sweep at ' + str(runs[i][1]) + ' Oe.'
        data.title = data.name
        other_data = [
            key
            for key in block.keys()
            if 'ch1' not in key and 'ch2' not in key and 'map' not in key.lower()
        ]
        for key in other_data:
            clean_key = (
                key.split('(')[0].strip().replace(' ', '_').lower()
            )  # .replace('time stamp','timestamp')
            if hasattr(data, clean_key):
                setattr(
                    data,
                    clean_key,
                    block[key],  # * ureg(data_template[f'{key}/@units'])
                )
        channel_1_data = [key for key in block.keys() if 'ch1' in key.lower()]
        if channel_1_data:
            channel_1 = ACTChannelData()
            setattr(channel_1, 'name', 'Channel 1')
            for key in channel_1_data:
                clean_key = clean_channel_keys(key)
                if hasattr(channel_1, clean_key):
                    setattr(
                        channel_1,
                        clean_key,
                        block[key],  # * ureg(data_template[f'{key}/@units'])
                    )
            data.m_add_sub_section(ACTPPMSData.channels, channel_1)
        channel_2_data = [key for key in block.keys() if 'ch2' in key.lower()]
        if channel_2_data:
            channel_2 = ACTChannelData()
            setattr(channel_2, 'name', 'Channel 2')
            for key in channel_2_data:
                clean_key = clean_channel_keys(key)
                if hasattr(channel_2, clean_key):
                    setattr(
                        channel_2,
                        clean_key,
                        block[key],  # * ureg(data_template[f'{key}/@units'])
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

        all_data.append(data)

    return all_data


def split_ppms_data_eto(data_full, runs):  # noqa: PLR0912
    all_data = []
    for i in range(len(runs)):
        block = data_full.iloc[runs[i][2] : runs[i][3]]
        data = ETOPPMSData()
        data.measurement_type = runs[i][0]
        if data.measurement_type == 'field':
            data.name = 'Field sweep at ' + str(runs[i][1]) + ' K.'
        if data.measurement_type == 'temperature':
            data.name = 'Temperature sweep at ' + str(runs[i][1]) + ' Oe.'
        data.title = data.name
        other_data = [
            key
            for key in block.keys()
            if 'ch1' not in key and 'ch2' not in key and 'map' not in key.lower()
        ]
        for key in other_data:
            clean_key = (
                key.split('(')[0].strip().replace(' ', '_').lower()
            )  # .replace('time stamp','timestamp')
            if hasattr(data, clean_key):
                setattr(
                    data,
                    clean_key,
                    block[key],  # * ureg(data_template[f'{key}/@units'])
                )
        channel_1_data = [key for key in block.keys() if 'ch1' in key.lower()]
        if channel_1_data:
            channel_1 = ETOChannelData()
            setattr(channel_1, 'name', 'Channel 1')
            for key in channel_1_data:
                clean_key = clean_channel_keys(key)
                if hasattr(channel_1, clean_key):
                    setattr(
                        channel_1,
                        clean_key,
                        block[key].astype(
                            'float64'
                        ),  # * ureg(data_template[f'{key}/@units'])
                    )
            data.m_add_sub_section(ETOPPMSData.channels, channel_1)
        channel_2_data = [key for key in block.keys() if 'ch2' in key.lower()]
        if channel_2_data:
            channel_2 = ETOChannelData()
            setattr(channel_2, 'name', 'Channel 2')
            for key in channel_2_data:
                clean_key = clean_channel_keys(key)
                if hasattr(channel_2, clean_key):
                    setattr(
                        channel_2,
                        clean_key,
                        block[key].astype(
                            'float64'
                        ),  # * ureg(data_template[f'{key}/@units'])
                    )
            data.m_add_sub_section(ETOPPMSData.channels, channel_2)

        eto_channel_data = [key for key in block.keys() if 'ETO Channel' in key]
        if eto_channel_data:
            for key in eto_channel_data:
                eto_channel = ETOData()
                if hasattr(eto_channel, 'name'):
                    setattr(eto_channel, 'name', key)
                if hasattr(eto_channel, 'ETO_channel'):
                    setattr(eto_channel, 'ETO_channel', data[key])
                data.m_add_sub_section(ETOPPMSData.eto_channels, eto_channel)

        all_data.append(data)

    return all_data


def split_ppms_data_acms(data_full, runs):
    all_data = []
    for i in range(len(runs)):
        block = data_full.iloc[runs[i][2] : runs[i][3]]
        data = ACMSPPMSData()
        data.measurement_type = runs[i][0]
        if data.measurement_type == 'field':
            data.name = 'Field sweep at ' + str(runs[i][1]) + ' K.'
        if data.measurement_type == 'temperature':
            data.name = 'Temperature sweep at ' + str(runs[i][1]) + ' Oe.'
        data.title = data.name
        other_data = [
            key
            for key in block.keys()
            if 'ch1' not in key and 'ch2' not in key and 'map' not in key.lower()
        ]
        for key in other_data:
            clean_key = (
                key.split('(')[0].strip().replace(' ', '_').lower()
            )  # .replace('time stamp','timestamp')
            if hasattr(data, clean_key):
                setattr(
                    data,
                    clean_key,
                    block[key],  # * ureg(data_template[f'{key}/@units'])
                )
        map_data = [key for key in block.keys() if 'Map' in key]
        if map_data:
            for key in map_data:
                map = ACMSData()
                if hasattr(map, 'name'):
                    setattr(map, 'name', key)
                if hasattr(map, 'map'):
                    setattr(map, 'map', block[key])
                data.m_add_sub_section(ACMSPPMSData.maps, map)

        all_data.append(data)

    return all_data