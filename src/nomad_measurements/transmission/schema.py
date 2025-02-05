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
"""
Module for schemas related to Transmission Spectrophotometry. Contains the schema for
spectrophotometer, sample, and measurement.

To add a new schema for a measurement technique, create a new schema class with the
signature: `<MeasurementTechniqueName>Transmission(Measurement)`.
For example, UVVisNirTransmission(Measurement) for UV-Vis-NIR Transmission.

If you want a corresponding ELN schema, create a new class with the signature:
`ELN<MeasurementTechniqueName>Transmission(
    <MeasurementTechniqueName>Transmission, PlotSection, EntryData
)`.
For example, ELNUVVisNirTransmission(UVVisNirTransmission, PlotSection, EntryData).
"""

from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Union,
)

import numpy as np
import pint
import plotly.express as px
from fairmat_readers_transmission import read_perkin_elmer_asc
from nomad.datamodel.data import (
    ArchiveSection,
    EntryData,
)
from nomad.datamodel.metainfo.annotations import (
    ELNAnnotation,
    ELNComponentEnum,
    Filter,
    SectionProperties,
)
from nomad.datamodel.metainfo.basesections import (
    CompositeSystem,
    CompositeSystemReference,
    Entity,
    Instrument,
    InstrumentReference,
    Measurement,
    MeasurementResult,
    ReadableIdentifiers,
)
from nomad.datamodel.metainfo.plot import (
    PlotlyFigure,
    PlotSection,
)
from nomad.metainfo import (
    MEnum,
    MProxy,
    Quantity,
    SchemaPackage,
    Section,
    SubSection,
)

from nomad_measurements.utils import create_archive, merge_sections

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

from nomad.config import config

m_package = SchemaPackage()


class Detector(Entity):
    """
    Light detector used in the transmission spectroscopy instruments.
    """

    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                visible=Filter(
                    exclude=['datetime', 'lab_id'],
                ),
            ),
        ),
    )
    type = Quantity(
        type=str,
        description="""
        Type of the detector used in the instrument. Some of the popular detectors are:
        | Detector          | Description          |
        |-------------------|----------------------|
        | **PMT**           | Photomultiplier Tube detector used for the Ultra-Violet (UV) or visible range.|
        | **InGaAs**        | Indium Gallium Arsenide detector used for Near-Infra-red (NIR) range.|
        | **PbS**           | Lead Sulphide detector used for Infrared (IR) range.|
        """,  # noqa: E501
        a_eln={'component': 'StringEditQuantity'},
    )

    def normalize(self, archive, logger):
        self.name = f'{self.type} Detector' if self.type else 'Detector'
        super().normalize(archive, logger)


class LightSource(Entity):
    """
    Section to bring together different types of light sources.
    """

    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                visible=Filter(
                    exclude=['datetime', 'lab_id'],
                ),
            ),
        ),
    )
    power = Quantity(
        type=np.float64,
        description='Power of the light source.',
        a_eln={
            'component': 'NumberEditQuantity',
            'defaultDisplayUnit': 'mW',
        },
        unit='W',
    )


class Lamp(LightSource):
    """
    Lamp used in transmission spectroscopy instruments.
    """

    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                visible=Filter(
                    exclude=['datetime', 'lab_id'],
                ),
            ),
        ),
    )
    type = Quantity(
        type=str,
        description="""
        Type of the lamp used. Some of the popular materials are:
        | Detector          | Description          |
        |-------------------|----------------------|
        | **Deuterium**     | Used for light generation in the UV range (160 nm to 400 nm).|
        | **Tungsten**      | Used for light generation in the near-infrared range (320nm to 2500nm).|
        """,  # noqa: E501
        a_eln={'component': 'StringEditQuantity'},
    )

    def normalize(self, archive, logger):
        self.name = f'{self.type} Lamp' if self.type else 'Lamp'
        super().normalize(archive, logger)


class Monochromator(Entity):
    """
    Monochromator used to select a narrow band of wavelengths from the light source in
    transmission spectroscopy instruments.
    """

    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                visible=Filter(
                    exclude=['datetime', 'lab_id'],
                ),
            ),
        ),
    )


class GratingMonochromator(Monochromator):
    """
    Grating monochromator used in transmission spectroscopy instruments.
    """

    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                visible=Filter(
                    exclude=['datetime', 'lab_id'],
                ),
            ),
        ),
    )
    groove_density = Quantity(
        description='Number of grooves per unit length of the grating.',
        type=float,
        unit='1/m',
        a_eln={
            'component': 'NumberEditQuantity',
            'defaultDisplayUnit': '1/mm',
        },
    )

    def normalize(self, archive, logger):
        self.name = 'Grating Monochromator'
        super().normalize(archive, logger)


class Spectrophotometer(Instrument, EntryData):
    """
    Entry section for transmission spectrophotometer.

    When extending the section for a specific instrument, the components (detectors,
    light sources, and monochromators) should be instantiated in the `self.normalize`
    method based on what components are physically available in the instrument.
    The component list should be populated such that components used in lower wavelength
    ranges are listed first. For instance, PMT detector should be listed before InGaAs.
    Take a look at the `PerkinElmersLambdaSpectrophotometer` class for an example.
    """

    m_def = Section()
    serial_number = Quantity(
        type=str,
        description='Instrument serial number.',
        a_eln={'component': 'StringEditQuantity'},
    )
    software_version = Quantity(
        type=str,
        description='Software/firmware version.',
        a_eln={'component': 'StringEditQuantity'},
    )
    detectors = SubSection(
        section_def=Detector,
        repeats=True,
    )
    light_sources = SubSection(
        section_def=Lamp,
        repeats=True,
    )
    monochromators = SubSection(
        section_def=Monochromator,
        repeats=True,
    )


class PerkinElmersLambdaSpectrophotometer(Spectrophotometer):
    """
    Entry section for Perkin Elmers Lambda series transmission spectrophotometer.
    """

    monochromators = SubSection(
        section_def=GratingMonochromator,
        repeats=True,
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `PerkinElmersLambdaSpectrophotometer` class.

        Args:
            archive (EntryArchive): The NOMAD archive.
            logger (BoundLogger): A structlog logger.
        """
        # add detectors
        if not self.detectors:
            self.m_setdefault('detectors/0')
            self.detectors[0].type = 'PMT'
            self.detectors[0].description = """
            Photomultiplier Tube used for UV or visible range."""

            self.m_setdefault('detectors/1')
            self.detectors[1].type = 'InGaAs'
            self.detectors[1].description = """
            Indium Gallium Arsenide used for NIR range."""

            self.m_setdefault('detectors/2')
            self.detectors[2].type = 'PbS'
            self.detectors[2].description = 'Lead Sulphide used for IR range.'

            for detector in self.detectors:
                detector.normalize(archive, logger)

        # add light sources
        if not self.light_sources:
            self.m_setdefault('light_sources/0')
            self.light_sources[0].type = 'Deuterium'
            self.light_sources[0].description = """
            Deuterium lamp used for light generation in the UV range."""

            self.m_setdefault('light_sources/1')
            self.light_sources[1].type = 'Tungsten'
            self.light_sources[1].description = """
            Tungsten lamp used for light generation in the NIR range."""

            for light_source in self.light_sources:
                light_source.normalize(archive, logger)

        # add monochromators
        if not self.monochromators:
            self.m_setdefault('monochromators/0')
            self.monochromators[0].groove_density = 1440000
            self.monochromators[0].description = """
            Holographic gratings with 1440 lines/mm used for generating light in UV/Vis
            range."""

            self.m_setdefault('monochromators/1')
            self.monochromators[1].groove_density = 360000
            self.monochromators[1].description = """
            Holographic gratings with 360 lines/mm used for generating light in NIR
            range."""

            for monochromator in self.monochromators:
                monochromator.normalize(archive, logger)

        super().normalize(archive, logger)


class TransmissionSampleReference(CompositeSystemReference):
    """
    Reference to the sample used in the transmission measurement. Additionally,
    it contains specific sample properties important for transmission measurements.
    """

    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'name',
                    'lab_id',
                    'reference',
                    'geometric_path_length',
                    'optical_path_length',
                ]
            )
        )
    )
    reference = Quantity(
        type=CompositeSystem,
        description="""
        A reference to the sample used.
        """,
        a_eln=ELNAnnotation(
            component='ReferenceEditQuantity',
            label='sample reference',
        ),
    )
    geometric_path_length = Quantity(
        type=np.float64,
        description="""
        Length of the sample along the direction of the light beam, i.e., the Euclidean
        distance between the entry and exit points of the light beam on the sample.
        This is different from the optical path length, which is the product of the
        refractive index of the sample and the geometric path length.
        """,
        a_eln={
            'component': 'NumberEditQuantity',
            'defaultDisplayUnit': 'millimeter',
        },
        unit='meter',
    )
    optical_path_length = Quantity(
        type=np.float64,
        description="""
        Product of the refractive index of the sample and the geometric path length.
        """,
        a_eln={
            'component': 'NumberEditQuantity',
            'defaultDisplayUnit': 'millimeter',
        },
        unit='meter',
    )


class CrystallographicTransmissionSampleReference(TransmissionSampleReference):
    """
    Reference to the sample used in the transmission measurement. Additionally, it
    includes specific properties for crystallographic samples.
    """

    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'name',
                    'lab_id',
                    'reference',
                    'geometric_path_length',
                    'optical_path_length',
                    'crystal_orientation',
                ]
            )
        )
    )
    crystal_orientation = Quantity(
        type=str,
        description="""
        Crystallographic orientation of the sample surface on which the light beam is
        incident.
        """,
        a_eln={'component': 'StringEditQuantity'},
    )


class Accessory(ArchiveSection):
    """
    Section to specify settings of a custom accessory used in transmission spectroscopy
    instruments.
    """

    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'name',
                    'description',
                ],
            ),
        ),
    )
    name = Quantity(
        type=str,
        description='Name of the accessory.',
        a_eln={'component': 'StringEditQuantity'},
    )
    description = Quantity(
        type=str,
        description='Description of the accessory.',
        a_eln={'component': 'RichTextEditQuantity'},
    )


class PolDepol(Accessory):
    """
    Accessory to polarize or depolarize the light beam entering the sample chamber.
    """

    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'name',
                    'mode',
                    'polarizer_angle',
                ],
            ),
        ),
    )

    mode = Quantity(
        type=MEnum(['Polarizer', 'Depolarizer']),
        description='Mode of the accessory: either polarizer or depolarizer.',
        a_eln={'component': 'RadioEnumEditQuantity'},
    )
    polarizer_angle = Quantity(
        type=np.float64,
        description='Value of polarization angle when polarizer mode is used.',
        a_eln={'component': 'NumberEditQuantity'},
        unit='degrees',
    )

    def normalize(self, archive, logger):
        if (
            self.mode is None or self.mode == 'Depolarizer'
        ) and self.polarizer_angle is not None:
            logger.warning(
                'Ambiguous polarizer angle: '
                'PolDepol accessory is not set to "Polarizer" mode, '
                'but `polarizer_angle` is set.'
            )
        super().normalize(archive, logger)


class Aperture(Accessory):
    """
    Custom aperture placed in front of the sample inside the sample compartment.
    """

    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'name',
                    'diameter',
                ],
            ),
        ),
    )
    diameter = Quantity(
        type=np.float64,
        description='Diameter of the aperture.',
        a_eln={
            'component': 'NumberEditQuantity',
            'defaultDisplayUnit': 'mm',
        },
        unit='mm',
    )


class SettingOverWavelengthRange(ArchiveSection):
    """
    An instrument setting set over a wavelength range.
    """

    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'name',
                    'wavelength_lower_limit',
                    'wavelength_upper_limit',
                ],
            ),
        ),
    )
    name = Quantity(
        type=str,
        description='Short description containing wavelength range.',
        a_eln={'component': 'StringEditQuantity'},
    )
    wavelength_lower_limit = Quantity(
        type=np.float64,
        description='Lower limit of wavelength range.',
        a_eln={
            'component': 'NumberEditQuantity',
            'defaultDisplayUnit': 'nm',
        },
        unit='nm',
    )
    wavelength_upper_limit = Quantity(
        type=np.float64,
        description='Upper limit of wavelength range.',
        a_eln={
            'component': 'NumberEditQuantity',
            'defaultDisplayUnit': 'nm',
        },
        unit='nm',
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `SettingOverWavelengthRange` class.

        Args:
            archive (EntryArchive): The archive containing the section.
            logger (BoundLogger): A structlog logger.
        """
        super().normalize(archive, logger)

        upper_limit = '-'
        lower_limit = '-'
        if self.wavelength_upper_limit is not None:
            upper_limit = self.wavelength_upper_limit.magnitude
        if self.wavelength_lower_limit is not None:
            lower_limit = self.wavelength_lower_limit.magnitude
        if (
            isinstance(upper_limit, float)
            and isinstance(lower_limit, float)
            and upper_limit < lower_limit
        ):
            logger.warning(
                f'Upper limit of wavelength "{upper_limit}" should be greater than'
                f'lower limit of wavelength "{lower_limit}".'
            )
            upper_limit = '-'
            lower_limit = '-'
            self.wavelength_upper_limit = None
            self.wavelength_lower_limit = None
        self.name = f'[{lower_limit}, {upper_limit}]'


class MonochromatorSlitWidth(SettingOverWavelengthRange):
    """
    Monochromator slit width setting over a wavelength range.
    """

    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'name',
                    'wavelength_lower_limit',
                    'wavelength_upper_limit',
                    'slit_width_servo',
                    'slit_width',
                ],
            ),
        ),
    )
    slit_width = Quantity(
        type=np.float64,
        description='Slit width value.',
        a_eln={
            'component': 'NumberEditQuantity',
            'defaultDisplayUnit': 'nm',
        },
        unit='nm',
    )
    slit_width_servo = Quantity(
        type=bool,
        description="""
        True if slit width servo is on, i.e., the system monitors the reference
        beam energy and adjusts the slits to avoid over-saturation of the detectors.
        """,
        a_eln={'component': 'BoolEditQuantity'},
    )


class MonochromatorSettings(SettingOverWavelengthRange):
    """
    Monochromator used over a wavelength range.
    """

    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'name',
                    'wavelength_lower_limit',
                    'wavelength_upper_limit',
                    'monochromator',
                ],
            ),
        ),
    )
    monochromator = Quantity(
        type=Monochromator,
        description='Monochromator used in the current wavelength range.',
        a_eln={'component': 'ReferenceEditQuantity'},
    )


class DetectorGain(SettingOverWavelengthRange):
    """
    Gain factor of the detector used in transmission spectrophotometry over a range of
    wavelength.
    """

    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'name',
                    'wavelength_lower_limit',
                    'wavelength_upper_limit',
                    'gain',
                ],
            ),
        ),
    )
    gain = Quantity(
        type=np.float64,
        description='Gain factor of the detector used over a wavelength range.',
        a_eln={'component': 'NumberEditQuantity'},
        unit='dimensionless',
    )


class DetectorIntegrationTime(SettingOverWavelengthRange):
    """
    Integration time of the detector used in transmission spectrophotometry over a
    wavelength range.
    """

    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'name',
                    'wavelength_lower_limit',
                    'wavelength_upper_limit',
                    'integration_time',
                ],
            ),
        ),
    )
    integration_time = Quantity(
        type=np.float64,
        description="""
        Integration time of the detector used in the given wavelength range.
        """,
        a_eln={
            'component': 'NumberEditQuantity',
            'defaultDisplayUnit': 's',
        },
        unit='s',
    )


class DetectorSettings(SettingOverWavelengthRange):
    """
    Settings of the detector used in transmission spectrophotometry instruments.
    """

    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'name',
                    'wavelength_lower_limit',
                    'wavelength_upper_limit',
                    'detector',
                ],
            ),
        ),
    )

    detector = Quantity(
        type=Detector,
        description='Detector used in the current wavelength range',
        a_eln={'component': 'ReferenceEditQuantity'},
    )


class LampSettings(SettingOverWavelengthRange):
    """
    Settings of the lamp used in transmission spectrophotometry instruments.
    """

    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'name',
                    'wavelength_lower_limit',
                    'wavelength_upper_limit',
                    'lamp',
                ],
            ),
        ),
    )

    lamp = Quantity(
        type=Lamp,
        description='Lamp used in the current wavelength range.',
        a_eln={'component': 'ReferenceEditQuantity'},
    )


class AttenuatorSettings(ArchiveSection):
    """
    Settings of the attenuator used for the sample and reference light beam.
    """

    m_def = Section()
    sample_beam_attenuation = Quantity(
        type=float,
        description='Value of sample beam attenuation ranging from 0 to 1.',
        a_eln={
            'component': 'NumberEditQuantity',
            'minValue': 0,
            'maxValue': 1,
        },
        unit='dimensionless',
    )
    reference_beam_attenuation = Quantity(
        type=float,
        description='Value of reference beam attenuation ranging from 0 to 1.',
        a_eln={
            'component': 'NumberEditQuantity',
            'minValue': 0,
            'maxValue': 1,
        },
        unit='dimensionless',
    )


class UVVisNirTransmissionResult(MeasurementResult):
    """
    Section for the results of the Transmission Spectroscopy measurement in UV, visible,
    and near IR ranges of wavelength.
    """

    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'transmittance',
                    'absorbance',
                    'wavelength',
                ],
                visible=Filter(
                    exclude=[
                        'array_index',
                    ],
                ),
            )
        ),
    )
    array_index = Quantity(
        type=int,
        description='Array of indices used for plotting quantity vectors.',
        shape=['*'],
    )
    transmittance = Quantity(
        type=np.float64,
        description='Measured transmittance ranging from 0 to 1.',
        shape=['*'],
        unit='dimensionless',
        a_plot={'x': 'array_index', 'y': 'transmittance'},
    )
    absorbance = Quantity(
        type=np.float64,
        description="""
        Calculated absorbance using the relation A = -log(T), where T denotes
        transmittance.""",
        shape=['*'],
        unit='dimensionless',
        a_plot={'x': 'array_index', 'y': 'absorbance'},
    )
    wavelength = Quantity(
        type=np.float64,
        description='Wavelength values for which the measurement was conducted.',
        shape=['*'],
        unit='m',
        a_plot={'x': 'array_index', 'y': 'wavelength'},
    )

    def generate_plots(self) -> list[PlotlyFigure]:
        """
        Generate the plotly figures for the `UVVisNirTransmissionResult` section.

        Returns:
            list[PlotlyFigure]: The plotly figures.
        """
        figures = []
        if self.wavelength is None:
            return figures

        for key in ['transmittance', 'absorbance']:
            if getattr(self, key) is None:
                continue

            x_label = 'Wavelength'
            xaxis_title = f'{x_label} (nm)'
            x = self.wavelength.to('nm').magnitude

            y_label = key.capitalize()
            yaxis_title = y_label
            y = getattr(self, key).magnitude

            line_linear = px.line(x=x, y=y)

            line_linear.update_layout(
                title=f'{y_label} over {x_label}',
                xaxis_title=xaxis_title,
                yaxis_title=yaxis_title,
                xaxis=dict(
                    fixedrange=False,
                ),
                yaxis=dict(
                    fixedrange=False,
                ),
                template='plotly_white',
            )

            figures.append(
                PlotlyFigure(
                    label=f'{y_label} linear plot',
                    figure=line_linear.to_plotly_json(),
                ),
            )

        return figures


class UVVisNirTransmissionSettings(ArchiveSection):
    """
    Section for the settings of the Transmission Spectroscopy measurement in UV,
    visible, and near IR ranges of wavelength.
    """

    m_def = Section()
    sample_beam_position = Quantity(
        type=MEnum(['Front', 'Rear']),
        description=(
            'Position of the sample beam: either the front or the back of the sample '
            'chamber.'
        ),
        a_eln={'component': 'EnumEditQuantity'},
    )
    common_beam_mask = Quantity(
        type=float,
        description=(
            'Mask setting for the common beam ranging from 0 to 1.'
            '1 means the mask is fully open and the beam passes completely. '
            '0 means the mask is closed and no light passes.'
        ),
        a_eln={
            'component': 'NumberEditQuantity',
            'minValue': 0,
            'maxValue': 1,
        },
        unit='dimensionless',
    )
    common_beam_depolarizer = Quantity(
        type=bool,
        description=(
            'True if the common beam depolarizer (CBD) is on, else False. CBD is an '
            'optional accessory used to depolarize the radiation coming from the '
            'monochromator.'
        ),
        default=False,
        a_eln={'component': 'BoolEditQuantity'},
    )
    detector_module = Quantity(
        type=MEnum(
            [
                'Three Detector Module',
                'Two Detector Module',
                '150-mm Integrating Sphere',
            ]
        ),
        a_eln={'component': 'EnumEditQuantity'},
        description="""
        Modules containing multiple detectors for different wavelength ranges.
        | Detector Module                      | Description          |
        |--------------------------------------|----------------------|
        | **Three Detector Module**            | Installed as standard module on Perkin-Elmer Lambda 1050 WB and NB spectrophotometers. Contains three detectors for different wavelength ranges: PMT, InGaAs, PbS. |
        | **Two Detector Module**              | Installed on Perkin-Elmer Lambda 750, 900, 950 spectrophotometers. Contains two detectors for different wavelength ranges: PMT, PbS. |
        | **150-mm Integrating Sphere**        | Includes an integrating sphere with a diameter of 150 mm which is equipped with PMT (R928) and InGaAs detector. The PMT covers 200-860.8 nm and the InGaAs detector covers 860.8-2500 nm. |
        """,  # noqa: E501
    )
    light_sources = SubSection(
        section_def=LampSettings,
        repeats=True,
    )
    attenuator = SubSection(
        section_def=AttenuatorSettings,
    )
    monochromators = SubSection(
        section_def=MonochromatorSettings,
        repeats=True,
    )
    monochromator_slit_width = SubSection(
        section_def=MonochromatorSlitWidth,
        repeats=True,
    )
    detectors = SubSection(
        section_def=DetectorSettings,
        repeats=True,
    )
    detector_gain = SubSection(
        section_def=DetectorGain,
        repeats=True,
    )
    detector_integration_time = SubSection(
        section_def=DetectorIntegrationTime,
        repeats=True,
    )
    accessories = SubSection(
        section_def=Accessory,
        repeats=True,
    )


class UVVisNirTransmission(Measurement):
    """
    Section for Transmission Spectroscopy measurement in UV, visible, and near IR ranges
    of wavelength.
    """

    m_def = Section()

    user = Quantity(
        type=str,
        description='Name of user or analyst.',
        a_eln={'component': 'StringEditQuantity'},
    )

    method = Quantity(
        type=str,
        default='UV-Vis-NIR Transmission Spectrophotometry',
    )

    samples = SubSection(
        section_def=TransmissionSampleReference,
        description='A list of all the samples measured during the measurement.',
        repeats=True,
    )
    results = SubSection(
        section_def=UVVisNirTransmissionResult,
        description='The result of the UV-Vis-NIR measurement.',
        repeats=True,
    )

    transmission_settings = SubSection(
        section_def=UVVisNirTransmissionSettings,
    )


class ELNUVVisNirTransmission(UVVisNirTransmission, PlotSection, EntryData):
    """
    Entry section for UVVisNirTransmission. Handles the population of the schema and
    plotting. Data is added either through manual input in the GUI or by parsing
    the measurement files coming from the instrument.
    """

    m_def = Section(
        label='UV-Vis-NIR Transmission',
        a_template={
            'measurement_identifiers': {},
        },
    )

    measurement_identifiers = SubSection(
        section_def=ReadableIdentifiers,
    )

    data_file = Quantity(
        type=str,
        description='File generated by the instrument containing data and metadata.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.FileEditQuantity,
        ),
    )

    def get_read_write_functions(self) -> tuple[Callable, Callable]:
        """
        Method for getting the correct read and write functions for the current data
        file.

        Returns:
            tuple[Callable, Callable]: The read, write functions.
        """
        if self.data_file.endswith('.asc'):
            return read_perkin_elmer_asc, self.write_transmission_data
        return None, None

    def create_instrument_entry(
        self, data_dict: dict[str, Any], archive: 'EntryArchive', logger: 'BoundLogger'
    ) -> InstrumentReference:
        """
        Method for creating the instrument entry. Returns a reference to the created
        instrument.

        Args:
            data_dict (dict[str, Any]): The dictionary containing the instrument data.
            archive (EntryArchive): The archive containing the section.
            logger (BoundLogger): A structlog logger.

        Returns:
            InstrumentReference: The instrument reference.
        """
        instrument_name = data_dict['instrument_name'].lower()

        if 'lambda' in instrument_name:
            instrument = PerkinElmersLambdaSpectrophotometer()
        else:
            instrument = Spectrophotometer()

        instrument.name = data_dict['instrument_name']
        instrument.serial_number = data_dict['instrument_serial_number']
        instrument.software_version = data_dict['instrument_firmware_version']
        if data_dict['start_datetime'] is not None:
            instrument.datetime = data_dict['start_datetime']

        instrument.normalize(archive, logger)

        file_name = f'{instrument.name}_{instrument.serial_number}.archive.json'
        file_name = file_name.replace(' ', '_')
        m_proxy_value = create_archive(instrument, archive, file_name)
        logger.info('Created instrument entry.')

        return InstrumentReference(reference=m_proxy_value)

    def get_instrument_reference(
        self, data_dict: dict[str, Any], archive: 'EntryArchive', logger: 'BoundLogger'
    ) -> Union[InstrumentReference, None]:
        """
        Method for getting the instrument reference.
        Looks for an existing instrument with the given serial number.
        If found, it returns a reference to this instrument.
        If no instrument is found, logs a warning, creates a new entry for the
        instrument and returns a reference to this entry.
        If multiple instruments are found, it logs a warning and returns None.

        Args:
            data_dict (dict[str, Any]): The dictionary containing the instrument data.
            archive (EntryArchive): The archive containing the section.
            logger (BoundLogger): A structlog logger.

        Returns:
            Union[InstrumentReference, None]: The instrument reference or None.
        """
        from nomad.datamodel.context import ClientContext

        if isinstance(archive.m_context, ClientContext):
            return None

        from nomad.search import search

        serial_number = data_dict['instrument_serial_number']
        api_query = {
            'entry_type:any': [
                'Spectrophotometer',
                'PerkinElmersLambdaSpectrophotometer',
            ]
        }
        search_result = search(
            owner='visible',
            query=api_query,
            user_id=archive.metadata.main_author.user_id,
        )

        valid_instruments = [
            entry
            for entry in search_result.data
            if entry['data']['serial_number'] == serial_number
        ]

        if not valid_instruments:
            logger.warning(
                f'No "Spectrophotometer" instrument found with the serial '
                f'number "{serial_number}". Creating an entry for the instrument.'
            )
            return self.create_instrument_entry(data_dict, archive, logger)

        if len(valid_instruments) > 1:
            logger.warning(
                f'Multiple "Spectrophotometer" instruments found with the '
                f'serial number "{serial_number}". Please select it manually.'
            )
            return None

        upload_id = valid_instruments[0]['upload_id']
        entry_id = valid_instruments[0]['entry_id']
        m_proxy_value = f'../uploads/{upload_id}/archive/{entry_id}#/data'

        return InstrumentReference(reference=m_proxy_value)

    def write_transmission_data(  # noqa: PLR0912, PLR0915
        self,
        transmission: UVVisNirTransmission,
        data_dict: dict[str, Any],
        archive: 'EntryArchive',
        logger: 'BoundLogger',
    ) -> None:
        """
        Populate `UVVisNirTransmission` section using data from a dict.

        Args:
            data_dict (dict[str, Any]): A dictionary with the transmission data.
            archive (EntryArchive): The archive containing the section.
            logger (BoundLogger): A structlog logger.
        """
        transmission.user = data_dict['analyst_name']
        if data_dict['start_datetime'] is not None:
            transmission.datetime = data_dict['start_datetime']

        # add instrument
        instruments = []
        instrument_reference = self.get_instrument_reference(data_dict, archive, logger)
        if instrument_reference:
            if isinstance(instrument_reference.reference, MProxy):
                instrument_reference.reference.m_proxy_context = archive.m_context
            instruments = [instrument_reference]
        transmission.instruments = instruments

        # add results
        transmission.m_setdefault('results/0')
        transmission.results[0].wavelength = data_dict['measured_wavelength']
        if data_dict['ordinate_type'] == 'A':
            transmission.results[0].absorbance = data_dict['measured_ordinate']
        elif data_dict['ordinate_type'] == '%T':
            transmission.results[0].transmittance = data_dict['measured_ordinate'] / 100
        else:
            logger.warning(f"Unknown ordinate type '{data_dict['ordinate']}'.")
        transmission.results[0].normalize(archive, logger)

        # add settings
        transmission.m_setdefault('transmission_settings')
        transmission.transmission_settings.sample_beam_position = data_dict[
            'sample_beam_position'
        ]
        transmission.transmission_settings.common_beam_depolarizer = data_dict[
            'is_common_beam_depolarizer_on'
        ]
        if data_dict['common_beam_mask_percentage'] is not None:
            transmission.transmission_settings.common_beam_mask = (
                data_dict['common_beam_mask_percentage'] / 100
            )

        # add settings: light sources
        lamps = []
        if data_dict['is_d2_lamp_used']:
            lamps.append('Deuterium')
        if data_dict['is_tungsten_lamp_used']:
            lamps.append('Tungsten')
        try:
            i = 0
            for light_source in instrument_reference.reference.light_sources:
                if light_source.type in lamps:
                    transmission.m_setdefault(
                        f'transmission_settings/light_sources/{i}'
                    )
                    transmission.transmission_settings.light_sources[
                        i
                    ].lamp = light_source
                    i += 1
        except Exception as e:
            logger.warning(
                f'Failed to add lamp settings. Error: {e}',
            )
        lamp_change_points = data_dict['lamp_change_wavelength']
        if (
            lamp_change_points is not None
            and len(lamp_change_points)
            == len(transmission.transmission_settings.light_sources) - 1
        ):
            for idx, lamp_change_point in enumerate(lamp_change_points):
                transmission.transmission_settings.light_sources[
                    idx
                ].wavelength_upper_limit = lamp_change_point
                transmission.transmission_settings.light_sources[
                    idx + 1
                ].wavelength_lower_limit = lamp_change_point
        for light_source_setting in transmission.transmission_settings.light_sources:
            light_source_setting.normalize(archive, logger)

        # add settings: detector
        detector_module = data_dict['detector_module']
        detector_list = []
        if detector_module == 'uv/vis/nir detector':
            if 'lambda 1050' in data_dict['instrument_name'].lower():
                transmission.transmission_settings.detector_module = (
                    'Three Detector Module'
                )
                detector_list = ['PMT', 'InGaAs', 'PbS']
            elif any(
                [
                    'lambda 950' in data_dict['instrument_name'].lower(),
                    'lambda 900' in data_dict['instrument_name'].lower(),
                    'lambda 750' in data_dict['instrument_name'].lower(),
                ]
            ):
                transmission.transmission_settings.detector_module = (
                    'Two Detector Module'
                )
                detector_list = ['PMT', 'PbS']
        if detector_module == '150mm sphere':
            transmission.transmission_settings.detector_module = (
                '150-mm Integrating Sphere'
            )
            detector_list = ['PMT', 'InGaAs']
        try:
            i = 0
            for detector in instrument_reference.reference.detectors:
                if detector.type in detector_list:
                    transmission.m_setdefault(f'transmission_settings/detectors/{i}')
                    transmission.transmission_settings.detectors[i].detector = detector
                    i += 1
        except Exception as e:
            logger.warning(
                f'Failed to add detector settings. Error: {e}',
            )
        detector_change_points = data_dict['detector_change_wavelength']
        if (
            detector_change_points is not None
            and len(detector_change_points)
            == len(transmission.transmission_settings.detectors) - 1
        ):
            for idx, change_point in enumerate(detector_change_points):
                transmission.transmission_settings.detectors[
                    idx
                ].wavelength_upper_limit = change_point
                transmission.transmission_settings.detectors[
                    idx + 1
                ].wavelength_lower_limit = change_point
        for detector_setting in transmission.transmission_settings.detectors:
            detector_setting.normalize(archive, logger)

        # add settings: monochromators
        try:
            i = 0
            for monochromator in instrument_reference.reference.monochromators:
                transmission.m_setdefault(f'transmission_settings/monochromators/{i}')
                transmission.transmission_settings.monochromators[
                    i
                ].monochromator = monochromator
                i += 1
        except Exception as e:
            logger.warning(
                f'Failed to add monochromator settings. Error: {e}',
            )
        monochromator_change_points = data_dict['monochromator_change_wavelength']
        if (
            monochromator_change_points is not None
            and len(monochromator_change_points)
            == len(transmission.transmission_settings.monochromators) - 1
        ):
            for idx, change_point in enumerate(monochromator_change_points):
                transmission.transmission_settings.monochromators[
                    idx
                ].wavelength_upper_limit = change_point
                transmission.transmission_settings.monochromators[
                    idx + 1
                ].wavelength_lower_limit = change_point
        for monochromator_setting in transmission.transmission_settings.monochromators:
            monochromator_setting.normalize(archive, logger)

        # add settings: monochromator slit width
        for idx, wavelength_value in enumerate(data_dict['monochromator_slit_width']):
            transmission.m_setdefault(
                f'transmission_settings/monochromator_slit_width/{idx}'
            )
            transmission.transmission_settings.monochromator_slit_width[
                idx
            ].wavelength_upper_limit = wavelength_value['wavelength']
            if (
                isinstance(wavelength_value['value'], str)
                and wavelength_value['value'].lower() == 'servo'
            ):
                transmission.transmission_settings.monochromator_slit_width[
                    idx
                ].slit_width = None
                transmission.transmission_settings.monochromator_slit_width[
                    idx
                ].slit_width_servo = True
            elif isinstance(wavelength_value['value'], pint.Quantity):
                transmission.transmission_settings.monochromator_slit_width[
                    idx
                ].slit_width = wavelength_value['value']
                transmission.transmission_settings.monochromator_slit_width[
                    idx
                ].slit_width_servo = False
            else:
                logger.warning(
                    f'Invalid slit width value "{wavelength_value["value"]}" for '
                    f'wavelength "{wavelength_value["wavelength"]}".'
                )
                continue
            if idx - 1 >= 0:
                transmission.transmission_settings.monochromator_slit_width[
                    idx
                ].wavelength_lower_limit = data_dict['monochromator_slit_width'][
                    idx - 1
                ]['wavelength']
            transmission.transmission_settings.monochromator_slit_width[idx].normalize(
                archive, logger
            )

        # add settings: NIR gain
        for idx, wavelength_value in enumerate(data_dict['detector_NIR_gain']):
            transmission.m_setdefault(f'transmission_settings/detector_gain/{idx}')
            transmission.transmission_settings.detector_gain[
                idx
            ].wavelength_upper_limit = wavelength_value['wavelength']
            transmission.transmission_settings.detector_gain[
                idx
            ].gain = wavelength_value['value']
            if idx - 1 >= 0:
                transmission.transmission_settings.detector_gain[
                    idx
                ].wavelength_lower_limit = data_dict['detector_NIR_gain'][idx - 1][
                    'wavelength'
                ]
            transmission.transmission_settings.detector_gain[idx].normalize(
                archive, logger
            )

        # add settings: integration time
        for idx, wavelength_value in enumerate(data_dict['detector_integration_time']):
            transmission.m_setdefault(
                f'transmission_settings/detector_integration_time/{idx}'
            )
            transmission.transmission_settings.detector_integration_time[
                idx
            ].wavelength_upper_limit = wavelength_value['wavelength']
            transmission.transmission_settings.detector_integration_time[
                idx
            ].integration_time = wavelength_value['value']
            if idx - 1 >= 0:
                transmission.transmission_settings.detector_integration_time[
                    idx
                ].wavelength_lower_limit = data_dict['detector_integration_time'][
                    idx - 1
                ]['wavelength']
            transmission.transmission_settings.detector_integration_time[idx].normalize(
                archive, logger
            )

        # add settings: attenuator
        transmission.m_setdefault('transmission_settings/attenuator')
        if data_dict['attenuation_percentage']['sample'] is not None:
            transmission.transmission_settings.attenuator.sample_beam_attenuation = (
                data_dict['attenuation_percentage']['sample'] / 100
            )
        if data_dict['attenuation_percentage']['reference'] is not None:
            transmission.transmission_settings.attenuator.reference_beam_attenuation = (
                data_dict['attenuation_percentage']['reference'] / 100
            )
        transmission.transmission_settings.attenuator.normalize(archive, logger)

        if self.get('transmission_settings') and self.transmission_settings.get(
            'accessory'
        ):
            for idx, accessory in enumerate(self.transmission_settings.accessory):
                if isinstance(accessory, PolDepol) and accessory.mode == 'Polarizer':
                    self.transmission_settings.accessory[
                        idx
                    ].polarizer_angle = data_dict['polarizer_angle']

        transmission.transmission_settings.normalize(archive, logger)

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger'):
        """
        The normalize function of the `ELNUVVisNirTransmission` section.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        if self.data_file is not None:
            read_function, write_function = self.get_read_write_functions()
            if read_function is None or write_function is None:
                logger.warning(
                    f'No compatible reader found for the file: "{self.data_file}".'
                )
            else:
                with archive.m_context.raw_file(self.data_file) as file:
                    data_dict = read_function(file.name, logger)
                transmission = self.m_def.section_cls()
                write_function(transmission, data_dict, archive, logger)
                merge_sections(self, transmission, logger)

        super().normalize(archive, logger)

        if not self.results:
            return

        self.figures = self.results[0].generate_plots()


class RawFileTransmissionData(EntryData):
    """
    Entry section for transmission spectrophotometry data file.
    """

    measurement = Quantity(
        type=ELNUVVisNirTransmission,
        a_eln=ELNAnnotation(
            component='ReferenceEditQuantity',
        ),
    )


m_package.__init_metainfo__()
