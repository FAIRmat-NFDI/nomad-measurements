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

import re
from io import StringIO
from typing import (
    TYPE_CHECKING,
)

import pandas as pd
from nomad.datamodel.data import (
    EntryData,
)
from nomad.datamodel.metainfo.annotations import (
    ELNAnnotation,
    SectionProperties,
)
from nomad.datamodel.metainfo.basesections import Measurement
from nomad.datamodel.metainfo.plot import PlotlyFigure, PlotSection
from nomad.metainfo import (
    Quantity,
    Section,
    SubSection,
)
from structlog.stdlib import (
    BoundLogger,
)

from nomad_measurements.ppms.ppmsdatastruct import (
    PPMSData,
    PPMSSample,
)
from nomad_measurements.ppms.ppmsfunctions import (
    find_ppms_steps_from_sequence,
    get_acms_ppms_steps_from_data,
    get_fileopentime,
    get_ppms_steps_from_data,
    split_ppms_data_acms,
    split_ppms_data_act,
    split_ppms_data_eto,
    split_ppms_data_mpms,
    split_ppms_data_resistivity,
)
from nomad_measurements.ppms.ppmssteps import (
    PPMSMeasurementStep,
)

if TYPE_CHECKING:
    from structlog.stdlib import (
        BoundLogger,
    )

from nomad.metainfo import SchemaPackage

m_package = SchemaPackage()


class PPMSMeasurement(Measurement):
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
        a_browser=dict(adaptor='RawFileAdaptor'),
    )
    file_open_time = Quantity(
        type=str, description='Time, where the PPMS file was created'
    )
    software = Quantity(
        type=str, description='PPMS software package used for the measurement'
    )

    steps = SubSection(
        section_def=PPMSMeasurementStep,
        repeats=True,
    )

    data = SubSection(section_def=PPMSData, repeats=True)

    sequence_file = Quantity(
        type=str,
        a_eln=dict(component='FileEditQuantity'),
        a_browser=dict(adaptor='RawFileAdaptor'),
    )

    # Additional parameters for separating the measurements
    temperature_tolerance = Quantity(
        type=float,
        unit='kelvin',
        a_eln=ELNAnnotation(
            component='NumberEditQuantity', defaultDisplayUnit='kelvin'
        ),
    )

    field_tolerance = Quantity(
        type=float,
        unit='gauss',
        a_eln=ELNAnnotation(component='NumberEditQuantity', defaultDisplayUnit='gauss'),
    )

    def normalize(self, archive, logger: BoundLogger) -> None:  # noqa: PLR0912, PLR0915
        super().normalize(archive, logger)
        if archive.data.data_file:
            logger.info('Parsing PPMS measurement file.')
            # For automatic step discovery, some parameters are needed:
            if not self.temperature_tolerance:
                self.temperature_tolerance = 0.2
            if not self.field_tolerance:
                self.field_tolerance = 5.0

            with archive.m_context.raw_file(self.data_file, 'r') as file:
                data = file.read()

            header_match = re.search(r'\[Header\](.*?)\[Data\]', data, re.DOTALL)
            header_section = header_match.group(1).strip()
            header_lines = header_section.split('\n')

            if len(self.samples) == 0:
                for i in ['1', '2']:
                    sample_headers = [
                        line
                        for line in header_lines
                        if line.startswith('INFO') and 'SAMPLE' + i + '_' in line
                    ]
                    if sample_headers:
                        sample = PPMSSample()
                        for line in sample_headers:
                            parts = re.split(r',\s*', line)
                            key = parts[-1].lower().replace('sample' + i + '_', '')
                            if hasattr(sample, key):
                                setattr(sample, key, ', '.join(parts[1:-1]))
                        self.m_add_sub_section(PPMSMeasurement.samples, sample)

            for line in header_lines:
                if line.startswith('FILEOPENTIME') and hasattr(self, 'datetime'):
                    iso_date = get_fileopentime(line)
                    if iso_date == 'Not found.':
                        logger.error('FILEOPENTIME not understood. Check the format.')
                    else:
                        setattr(self, 'datetime', iso_date)
                if line.startswith('BYAPP') and hasattr(self, 'software'):
                    setattr(self, 'software', line.replace('BYAPP,', '').strip())
                if line.startswith('TEMPERATURETOLERANCE') and hasattr(
                    self, 'temperature_tolerance'
                ):
                    setattr(
                        self,
                        'temperature_tolerance',
                        float(line.replace('TEMPERATURETOLERANCE,', '').strip()),
                    )
                if line.startswith('FIELDTOLERANCE') and hasattr(
                    self, 'field_tolerance'
                ):
                    setattr(
                        self,
                        'field_tolerance',
                        float(line.replace('FIELDTOLERANCE,', '').strip()),
                    )


class PPMSETOMeasurement(PPMSMeasurement, PlotSection, EntryData):
    def normalize(self, archive, logger: BoundLogger) -> None:  # noqa: PLR0912, PLR0915
        super().normalize(archive, logger)

        ### Start of the PPMSMeasurement normalizer
        if archive.data.data_file:
            logger.info('Parsing ETO measurement.')
            with archive.m_context.raw_file(self.data_file, 'r') as file:
                data = file.read()

            header_match = re.search(r'\[Header\](.*?)\[Data\]', data, re.DOTALL)

            data_section = header_match.string[header_match.end() :]
            data_section = data_section.replace(',Field', ',Magnetic Field')
            data_buffer = StringIO(data_section)
            data_df = pd.read_csv(
                data_buffer,
                header=0,
                skipinitialspace=True,
                sep=',',
                engine='python',
            )

            all_steps, runs_list = get_ppms_steps_from_data(
                data_df, self.temperature_tolerance, self.field_tolerance
            )

            if self.sequence_file:
                logger.info('Parsing PPMS sequence file.')
                with archive.m_context.raw_file(self.sequence_file, 'r') as file:
                    sequence = file.readlines()
                    self.steps = find_ppms_steps_from_sequence(sequence)
            else:
                self.steps = all_steps

            self.data = split_ppms_data_eto(data_df, runs_list)

            # Now create the according plots
            import plotly.express as px
            from plotly.subplots import make_subplots

            for data in self.data:
                if data.measurement_type == 'field':
                    resistivity_ch1 = px.scatter(
                        x=data.magnetic_field, y=data.channels[0].resistance
                    )
                    resistivity_ch2 = px.scatter(
                        x=data.magnetic_field, y=data.channels[1].resistance
                    )
                    x_title = 'Magnetic field H (Oe)'
                if data.measurement_type == 'temperature':
                    resistivity_ch1 = px.scatter(
                        x=data.temperature, y=data.channels[0].resistance
                    )
                    resistivity_ch2 = px.scatter(
                        x=data.temperature, y=data.channels[1].resistance
                    )
                    x_title = 'Temperature T (K)'
                figure1 = make_subplots(rows=2, cols=1, shared_xaxes=True)
                figure1.add_trace(resistivity_ch1.data[0], row=1, col=1)
                figure1.add_trace(resistivity_ch2.data[0], row=2, col=1)
                # figure1.update_layout(height=400, width=716, title_text=data.name)
                figure1.update_layout(
                    title_text=data.name,
                    template='plotly_white',
                    dragmode='zoom',
                    xaxis2=dict(
                        fixedrange=False,
                        autorange=True,
                        title=x_title,
                        mirror='all',
                        showline=True,
                        gridcolor='#EAEDFC',
                    ),
                    yaxis=dict(
                        fixedrange=False,
                        title='Resistance (Ohm)',
                        tickfont=dict(color='#2A4CDF'),
                        gridcolor='#EAEDFC',
                    ),
                    yaxis2=dict(
                        fixedrange=False,
                        title='Resistance (Ohm)',
                        tickfont=dict(color='#2A4CDF'),
                        gridcolor='#EAEDFC',
                    ),
                    showlegend=True,
                )
                self.figures.append(
                    PlotlyFigure(label=data.name, figure=figure1.to_plotly_json())
                )


class PPMSACTMeasurement(PPMSMeasurement, PlotSection, EntryData):
    def normalize(self, archive, logger: BoundLogger) -> None:  # noqa: PLR0912, PLR0915
        super().normalize(archive, logger)

        ### Start of the PPMSMeasurement normalizer
        if archive.data.data_file:
            logger.info('Parsing ACT measurement.')
            with archive.m_context.raw_file(self.data_file, 'r') as file:
                data = file.read()

            header_match = re.search(r'\[Header\](.*?)\[Data\]', data, re.DOTALL)

            data_section = header_match.string[header_match.end() :]
            data_section = data_section.replace(',Field', ',Magnetic Field')
            data_buffer = StringIO(data_section)
            data_df = pd.read_csv(
                data_buffer,
                header=0,
                skipinitialspace=True,
                sep=',',
                engine='python',
            )

            all_steps, runs_list = get_ppms_steps_from_data(
                data_df, self.temperature_tolerance, self.field_tolerance
            )

            if self.sequence_file:
                logger.info('Parsing PPMS sequence file.')
                with archive.m_context.raw_file(self.sequence_file, 'r') as file:
                    sequence = file.readlines()
                    self.steps = find_ppms_steps_from_sequence(sequence)
            else:
                self.steps = all_steps

            self.data = split_ppms_data_act(data_df, runs_list)

            # Now create the according plots
            import plotly.express as px
            from plotly.subplots import make_subplots

            for data in self.data:
                if data.measurement_type == 'field':
                    resistivity_ch1 = px.scatter(
                        x=data.magnetic_field, y=data.channels[0].resistivity
                    )
                    resistivity_ch2 = px.scatter(
                        x=data.magnetic_field, y=data.channels[1].resistivity
                    )
                    x_title = 'Magnetic field H (Oe)'
                if data.measurement_type == 'temperature':
                    resistivity_ch1 = px.scatter(
                        x=data.temperature, y=data.channels[0].resistivity
                    )
                    resistivity_ch2 = px.scatter(
                        x=data.temperature, y=data.channels[1].resistivity
                    )
                    x_title = 'Temperature T (K)'
                figure1 = make_subplots(rows=2, cols=1, shared_xaxes=True)
                figure1.add_trace(resistivity_ch1.data[0], row=1, col=1)
                figure1.add_trace(resistivity_ch2.data[0], row=2, col=1)
                # figure1.update_layout(height=400, width=716, title_text=data.name)
                figure1.update_layout(
                    title_text=data.name,
                    template='plotly_white',
                    dragmode='zoom',
                    xaxis2=dict(
                        fixedrange=False,
                        autorange=True,
                        title=x_title,
                        mirror='all',
                        showline=True,
                        gridcolor='#EAEDFC',
                    ),
                    yaxis=dict(
                        fixedrange=False,
                        title='Resistivity (Ohm/cm)',
                        tickfont=dict(color='#2A4CDF'),
                        gridcolor='#EAEDFC',
                    ),
                    yaxis2=dict(
                        fixedrange=False,
                        title='Resistivity (Ohm/cm)',
                        tickfont=dict(color='#2A4CDF'),
                        gridcolor='#EAEDFC',
                    ),
                    showlegend=True,
                )
                self.figures.append(
                    PlotlyFigure(label=data.name, figure=figure1.to_plotly_json())
                )


class PPMSACMSMeasurement(PPMSMeasurement, PlotSection, EntryData):
    # Additional parameters for separating the measurements
    frequency_tolerance = Quantity(
        type=float,
        unit='hertz',
        a_eln=ELNAnnotation(component='NumberEditQuantity', defaultDisplayUnit='hertz'),
    )

    amplitude_tolerance = Quantity(
        type=float,
        unit='gauss',
        a_eln=ELNAnnotation(component='NumberEditQuantity', defaultDisplayUnit='gauss'),
    )

    def normalize(self, archive, logger: BoundLogger) -> None:  # noqa: PLR0912, PLR0915
        super().normalize(archive, logger)

        if archive.data.data_file:
            logger.info('Parsing PPMS measurement file.')
            # For automatic step discovery, some parameters are needed:
            if not self.temperature_tolerance:
                self.frequency_tolerance = 10
            if not self.amplitude_tolerance:
                self.amplitude_tolerance = 0.1

            with archive.m_context.raw_file(self.data_file, 'r') as file:
                data = file.read()

            header_match = re.search(r'\[Header\](.*?)\[Data\]', data, re.DOTALL)

            data_section = header_match.string[header_match.end() :]
            data_section = data_section.replace(',Field', ',Magnetic Field')
            data_buffer = StringIO(data_section)
            data_df = pd.read_csv(
                data_buffer,
                header=0,
                skipinitialspace=True,
                sep=',',
                engine='python',
            )

            all_steps, runs_list = get_acms_ppms_steps_from_data(
                data_df,
            )

            if not self.sequence_file:
                self.steps = all_steps

            logger.info('Parsing ACMS measurement.')
            self.data = split_ppms_data_acms(data_df, runs_list)

            # Now create the according plots
            import plotly.express as px
            from plotly.subplots import make_subplots

            for data in self.data:
                if data.measurement_type == 'frequency':
                    moment = px.scatter(x=data.frequency, y=data.moment)
                    moment_derivative = px.scatter(
                        x=data.frequency, y=data.moment_derivative
                    )
                    moment_second_derivative = px.scatter(
                        x=data.frequency, y=data.moment_second_derivative
                    )
                figure1 = make_subplots(rows=3, cols=1, shared_xaxes=True)
                figure1.add_trace(moment.data[0], row=1, col=1)
                figure1.add_trace(moment_derivative.data[0], row=2, col=1)
                figure1.add_trace(moment_second_derivative.data[0], row=3, col=1)
                # figure1.update_layout(height=400, width=716, title_text=data.name)
                figure1.update_layout(
                    title_text=data.name,
                    template='plotly_white',
                    dragmode='zoom',
                    xaxis3=dict(
                        fixedrange=False,
                        autorange=True,
                        title='Frequency (Hz)',
                        mirror='all',
                        showline=True,
                        gridcolor='#EAEDFC',
                    ),
                    yaxis=dict(
                        fixedrange=False,
                        title='Moment (emu)',
                        tickfont=dict(color='#2A4CDF'),
                        gridcolor='#EAEDFC',
                    ),
                    yaxis2=dict(
                        fixedrange=False,
                        title=' Derivative of moment (emu)',
                        tickfont=dict(color='#2A4CDF'),
                        gridcolor='#EAEDFC',
                    ),
                    yaxis3=dict(
                        fixedrange=False,
                        title='Second derivative of moment (emu)',
                        tickfont=dict(color='#2A4CDF'),
                        gridcolor='#EAEDFC',
                    ),
                    showlegend=True,
                )
                self.figures.append(
                    PlotlyFigure(label=data.name, figure=figure1.to_plotly_json())
                )


class PPMSMPMSMeasurement(PPMSMeasurement, PlotSection, EntryData):
    def normalize(self, archive, logger: BoundLogger) -> None:  # noqa: PLR0912, PLR0915
        super().normalize(archive, logger)

        ### Start of the PPMSMeasurement normalizer
        if archive.data.data_file:
            logger.info('Parsing MPMS measurement.')
            with archive.m_context.raw_file(self.data_file, 'r') as file:
                data = file.read()

            header_match = re.search(r'\[Header\](.*?)\[Data\]', data, re.DOTALL)

            data_section = header_match.string[header_match.end() :]
            data_section = data_section.replace(',Field', ',Magnetic Field')
            data_buffer = StringIO(data_section)
            data_df = pd.read_csv(
                data_buffer,
                header=0,
                skipinitialspace=True,
                sep=',',
                engine='python',
            )

            all_steps, runs_list = get_ppms_steps_from_data(
                data_df, self.temperature_tolerance, self.field_tolerance
            )

            if self.sequence_file:
                logger.info('Parsing PPMS sequence file.')
                with archive.m_context.raw_file(self.sequence_file, 'r') as file:
                    sequence = file.readlines()
                    self.steps = find_ppms_steps_from_sequence(sequence)
            else:
                self.steps = all_steps

            self.data = split_ppms_data_mpms(data_df, runs_list)

        # Now create the according plots
        import plotly.express as px
        from plotly.subplots import make_subplots

        for data in self.data:
            if data.measurement_type == 'field':
                magnetization = px.scatter(x=data.magnetic_field, y=data.moment)
                x_title = 'Magnetic field H (Oe)'
            if data.measurement_type == 'temperature':
                magnetization = px.scatter(x=data.temperature, y=data.moment)
                x_title = 'Temperature T (K)'
            figure1 = make_subplots(rows=1, cols=1, shared_xaxes=True)
            figure1.add_trace(magnetization.data[0], row=1, col=1)
            # figure1.update_layout(height=400, width=716, title_text=data.name)
            figure1.update_layout(
                title_text=data.name,
                template='plotly_white',
                dragmode='zoom',
                xaxis=dict(
                    fixedrange=False,
                    autorange=True,
                    title=x_title,
                    mirror='all',
                    showline=True,
                    gridcolor='#EAEDFC',
                ),
                yaxis=dict(
                    fixedrange=False,
                    title='Magnetic moment (emu)',
                    tickfont=dict(color='#2A4CDF'),
                    gridcolor='#EAEDFC',
                ),
                showlegend=True,
            )
            self.figures.append(
                PlotlyFigure(label=data.name, figure=figure1.to_plotly_json())
            )


class PPMSResistivityMeasurement(PPMSMeasurement, PlotSection, EntryData):
    def normalize(self, archive, logger: BoundLogger) -> None:  # noqa: PLR0912, PLR0915
        super().normalize(archive, logger)

        ### Start of the PPMSMeasurement normalizer
        if archive.data.data_file:
            logger.info('Parsing Resistivity measurement.')
            with archive.m_context.raw_file(self.data_file, 'r') as file:
                data = file.read()

            header_match = re.search(r'\[Header\](.*?)\[Data\]', data, re.DOTALL)

            data_section = header_match.string[header_match.end() :]
            data_section = data_section.replace(',Field', ',Magnetic Field')
            data_buffer = StringIO(data_section)
            data_df = pd.read_csv(
                data_buffer,
                header=0,
                skipinitialspace=True,
                sep=',',
                engine='python',
            )

            all_steps, runs_list = get_ppms_steps_from_data(
                data_df, self.temperature_tolerance, self.field_tolerance
            )

            if self.sequence_file:
                logger.info('Parsing PPMS sequence file.')
                with archive.m_context.raw_file(self.sequence_file, 'r') as file:
                    sequence = file.readlines()
                    self.steps = find_ppms_steps_from_sequence(sequence)
            else:
                self.steps = all_steps

            self.data = split_ppms_data_resistivity(data_df, runs_list)

        # Now create the according plots
        import plotly.express as px
        from plotly.subplots import make_subplots

        for data in self.data:
            if data.measurement_type == 'field':
                resistivity_ch1 = px.scatter(
                    x=data.magnetic_field, y=data.bridge_1_resistivity
                )
                resistivity_ch2 = px.scatter(
                    x=data.magnetic_field, y=data.bridge_2_resistivity
                )
                x_title = 'Magnetic field H (Oe)'
            if data.measurement_type == 'temperature':
                resistivity_ch1 = px.scatter(
                    x=data.temperature, y=data.bridge_1_resistivity
                )
                resistivity_ch2 = px.scatter(
                    x=data.temperature, y=data.bridge_2_resistivity
                )
                x_title = 'Temperature T (K)'
            figure1 = make_subplots(rows=2, cols=1, shared_xaxes=True)
            figure1.add_trace(resistivity_ch1.data[0], row=1, col=1)
            figure1.add_trace(resistivity_ch2.data[0], row=2, col=1)
            # figure1.update_layout(height=400, width=716, title_text=data.name)
            figure1.update_layout(
                title_text=data.name,
                template='plotly_white',
                dragmode='zoom',
                xaxis2=dict(
                    fixedrange=False,
                    autorange=True,
                    title=x_title,
                    mirror='all',
                    showline=True,
                    gridcolor='#EAEDFC',
                ),
                yaxis=dict(
                    fixedrange=False,
                    title='Resistivity (Ohm/cm)',
                    tickfont=dict(color='#2A4CDF'),
                    gridcolor='#EAEDFC',
                ),
                yaxis2=dict(
                    fixedrange=False,
                    title='Resistivity (Ohm/cm)',
                    tickfont=dict(color='#2A4CDF'),
                    gridcolor='#EAEDFC',
                ),
                showlegend=True,
            )
            self.figures.append(
                PlotlyFigure(label=data.name, figure=figure1.to_plotly_json())
            )


m_package.__init_metainfo__()
