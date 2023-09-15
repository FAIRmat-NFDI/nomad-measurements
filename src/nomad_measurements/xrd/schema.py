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

from nomad.datamodel.metainfo.basesections import (
    Measurement,
    MeasurementResult,
    CompositeSystemReference,
    ReadableIdentifiers,
)
from structlog.stdlib import (
    BoundLogger,
)
from nomad.metainfo import (
    Package,
    Quantity,
    Section,
    SubSection,
    MEnum,
)
from nomad.datamodel.data import (
    ArchiveSection,
    EntryData,
)
from nomad.datamodel.metainfo.annotations import (
    ELNAnnotation,
    ELNComponentEnum,
)
from nomad.units import (
    ureg,
)
from nomad.metainfo.metainfo import (
    Category,
)
from nomad.datamodel.data import (
    EntryDataCategory,
)
from nomad.datamodel.results import (
    Results,
    Properties,
    StructuralProperties,
    DiffractionPattern,
    Method,
    MeasurementMethod,
    XRDMethod,
)

from nomad_measurements.xrd.xrd_parser import parse_and_convert_file

m_package = Package(name='nomad-measurements')


def calculate_two_theta_or_scattering_vector(q=None, two_theta=None, wavelength=None):
    """
    Calculate the two-theta array from the scattering vector (q) or vice-versa,
    given the wavelength of the X-ray source.

    Args:
        q (array-like, optional): Array of scattering vectors, in angstroms^-1.
        two_theta (array-like, optional): Array of two-theta angles, in degrees.
        wavelength (float): Wavelength of the X-ray source, in angstroms.

    Returns:
        numpy.ndarray: Array of two-theta angles, in degrees.
    """
    if q is not None:
        return 2 * np.arcsin(q * wavelength / (4 * np.pi))
    elif two_theta is not None:
        return (4 * np.pi / wavelength) * np.sin(np.deg2rad(two_theta) / 2)
    else:
        raise ValueError("Either q or two_theta must be provided.")


def estimate_kalpha_wavelengths(source_material):
    """
    Estimate the K-alpha1 and K-alpha2 wavelengths of an X-ray source given the material 
    of the source.

    Args:
        source_material (str): Material of the X-ray source, such as 'Cu', 'Fe', 'Mo',
        'Ag', 'In', 'Ga', etc.

    Returns:
        Tuple[float, float]: Estimated K-alpha1 and K-alpha2 wavelengths of the X-ray
        source, in angstroms.
    """
    # Dictionary of K-alpha1 and K-alpha2 wavelengths for various X-ray source materials,
    # in angstroms
    kalpha_wavelengths = {
        'Cr': (2.2910, 2.2936),
        'Fe': (1.9359, 1.9397),
        'Cu': (1.5406, 1.5444),
        'Mo': (0.7093, 0.7136),
        'Ag': (0.5594, 0.5638),
        'In': (0.6535, 0.6577),
        'Ga': (1.2378, 1.2443)
    }

    try:
        kalpha1_wavelength, kalpha2_wavelength = kalpha_wavelengths[source_material]
    except KeyError:
        raise ValueError("Unknown X-ray source material.")

    return kalpha1_wavelength, kalpha2_wavelength


class XRayTubeSource(ArchiveSection):
    '''
    X-ray tube source used in conventional diffractometers.
    '''
    xray_tube_material = Quantity(
        type=MEnum(sorted(['Cu', 'Cr', 'Mo', 'Fe', 'Ag', 'In', 'Ga'])),
        description='Type of the X-ray tube',
        default='Cu',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.EnumEditQuantity,
        ),
    )
    xray_tube_current = Quantity(
        type=np.dtype(np.float64),
        unit='A',
        description='Current of the X-ray tube',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            label='Current of the X-ray tube',
        ),
    )
    xray_tube_voltage = Quantity(
        type=np.dtype(np.float64),
        unit='V',
        description='Voltage of the X-ray tube',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            label='Voltage of the X-ray tube',
        ),
    )
    kalpha_one = Quantity(
        type=np.dtype(np.float64),
        unit='angstrom',
        description='Wavelength of the Kα1 line',
    )
    kalpha_two = Quantity(
        type=np.dtype(np.float64),
        unit='angstrom',
        description='Wavelength of the Kα2 line',
    )
    ratio_kalphatwo_kalphaone = Quantity(
        type=np.dtype(np.float64),
        unit='dimensionless',
        description='Kα2/Kα1 intensity ratio',
    )
    kbeta = Quantity(
        type=np.dtype(np.float64),
        unit='angstrom',
        description='Wavelength of the Kβ line',
    )


class XRDSettings(ArchiveSection):
    source = SubSection(section_def=XRayTubeSource)


class XRDResult(MeasurementResult):
    '''
    Section containing the result of an X-ray diffraction scan.
    '''
    m_def = Section()

    def derive_n_values(self):
        if self.intensity is not None:
            return len(self.intensity)
        if self.two_theta is not None:
            return len(self.two_theta)
        else:
            return 0
    
    n_values = Quantity(
        type=int,
        derived=derive_n_values,
    )
    two_theta = Quantity(
        type=np.dtype(np.float64), shape=['n_values'], 
        unit='deg',
        description='The 2-theta range of the difractogram',
        a_plot={
            'x': 'two_theta', 'y': 'intensity'
        },
    )
    q_vector = Quantity(
        type=np.dtype(np.float64), shape=['*'],
        unit='meter**(-1)',
        description='The scattering vector *Q* of the difractogram',
        a_plot={
            'x': 'q_vector', 'y': 'intensity'
        },
    )
    intensity = Quantity(
        type=np.dtype(np.float64), shape=['*'],
        description='The count at each 2-theta value, dimensionless',
        a_plot={
            'x': 'two_theta', 'y': 'intensity'
        },
    )
    omega = Quantity(
        type=np.dtype(np.float64), shape=['*'],
        unit='deg',
        description='The omega range of the difractogram',
    )
    phi = Quantity(
        type=np.dtype(np.float64), shape=['*'],
        unit='deg',
        description='The phi range of the difractogram',
    )
    chi = Quantity(
        type=np.dtype(np.float64), shape=['*'],
        unit='deg',
        description='The chi range of the difractogram',
    )
    source_peak_wavelength = Quantity(
        type=np.dtype(np.float64),
        unit='angstrom',
        description='''Wavelength of the X-ray source. Used to convert from 2-theta to Q
        and vice-versa.''',
    )
    scan_axis = Quantity(
        type=str,
        description='Axis scanned',
    )
    integration_time = Quantity(
        type=np.dtype(np.float64),
        unit='s',
        shape=['*'],
        description='Integration time per channel',
    )

    def normalize(self, archive, logger: BoundLogger) -> None:
        '''
        The normalizer for the `XRDResult` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        '''
        super(XRDResult, self).normalize(archive, logger)


class XRayDiffraction(Measurement):
    '''
    Generic X-ray diffraction measurement.
    '''
    m_def = Section()
    method = Quantity(
        type=str,
        default="X-Ray Diffraction (XRD)",
    )
    xrd_settings = SubSection(
        section_def=XRDSettings,
    )
    data_file = Quantity(
        type=str,
        description='Data file containing the difractogram',
        a_eln=dict(
            component='FileEditQuantity',
        ),
    )
    diffraction_method_name = Quantity(
        type=MEnum(
            [
                "Powder X-ray Diffraction (PXRD)",
                "Single Crystal X-ray Diffraction (SCXRD)",
                "High-Resolution X-ray Diffraction (HRXRD)",
                "Small-Angle X-ray Scattering (SAXS)",
                "X-ray Reflectivity (XRR)",
                "Grazing Incidence X-ray Diffraction (GIXRD)",
            ]
        ),
        description='''
        The diffraction method used to obtain the diffraction pattern.
        | X-ray Diffraction Method                                   | Description                                                                                                                                                                                                 |
        |------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
        | **Powder X-ray Diffraction (PXRD)**                        | The term "powder" refers more to the random orientation of small crystallites than to the physical form of the sample. Can be used with non-powder samples if they present random crystallite orientations. |
        | **Single Crystal X-ray Diffraction (SCXRD)**               | Used for determining the atomic structure of a single crystal.                                                                                                                                              |
        | **High-Resolution X-ray Diffraction (HRXRD)**              | A technique typically used for detailed characterization of epitaxial thin films using precise diffraction measurements.                                                                                    |
        | **Small-Angle X-ray Scattering (SAXS)**                    | Used for studying nanostructures in the size range of 1-100 nm. Provides information on particle size, shape, and distribution.                                                                             |
        | **X-ray Reflectivity (XRR)**                               | Used to study thin film layers, interfaces, and multilayers. Provides info on film thickness, density, and roughness.                                                                                       |
        | **Grazing Incidence X-ray Diffraction (GIXRD)**            | Primarily used for the analysis of thin films with the incident beam at a fixed shallow angle.                                                                                                              |
        ''',
    )
    results = Measurement.results.m_copy()
    results.section_def = XRDResult

    def normalize(self, archive, logger: BoundLogger) -> None:
        '''
        The normalizer for the `XRayDiffraction` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        '''
        super(XRayDiffraction, self).normalize(archive, logger)

        # Use the xrd parser to populate the schema reading the data file
        if not self.data_file:
            return

        result = XRDResult()
        settings = XRDSettings()
        with archive.m_context.raw_file(self.data_file) as file:
            xrd_dict = parse_and_convert_file(file.name)
            result.intensity = xrd_dict.get('detector', None)
            result.two_theta = xrd_dict['2Theta'] * ureg('degree') if '2Theta' in xrd_dict and xrd_dict['2Theta'] is not None else None
            result.omega = xrd_dict['Omega'] * ureg('degree') if 'Omega' in xrd_dict and xrd_dict['Omega'] is not None else None
            result.chi = xrd_dict['Chi'] * ureg('degree') if 'Chi' in xrd_dict and xrd_dict['Chi'] is not None else None
            if settings.source is None:
                settings.source = XRayTubeSource()
            metadata_dict = xrd_dict.get('metadata', {})
            source_dict = metadata_dict.get('source', {})
            settings.source.xray_tube_material = source_dict.get('anode_material', None)
            settings.source.kalpha_one = source_dict.get('kAlpha1', None)
            settings.source.kalpha_two = source_dict.get('kAlpha2', None)
            settings.source.ratio_kalphatwo_kalphaone = source_dict.get('ratioKAlpha2KAlpha1', None)
            settings.source.kbeta = source_dict.get('kBeta', None)
            settings.source.xray_tube_voltage = source_dict.get('voltage', None)
            settings.source.xray_tube_current = source_dict.get('current', None)
            result.scan_axis = metadata_dict.get('scan_axis', None)
            result.integration_time = xrd_dict['countTime'] * ureg('second') if xrd_dict['countTime'] is not None else None
            samples=CompositeSystemReference()
            samples.lab_id=xrd_dict['metadata']["sample_id"]
            samples.normalize(archive, logger)
            self.samples=[samples]
            
        if settings.source.xray_tube_material is not None:
            xray_tube_material = settings.source.xray_tube_material
            settings.source.kalpha_one, settings.source.kalpha_two = estimate_kalpha_wavelengths(source_material=xray_tube_material)
        try:
            if settings.source.kalpha_one is not None:
                result.source_peak_wavelength = settings.source.kalpha_one
            else:
                logger.warning("Unable to set source_peak_wavelegth because source.kalpha_one is None")
        except Exception:
            logger.warning("Unable to set source_peak_wavelegth")

        try:
            if result.source_peak_wavelength is not None and result.q_vector is not None:
                result.two_theta = calculate_two_theta_or_scattering_vector(
                    q=result.q_vector, wavelength=result.source_peak_wavelength)

            elif result.source_peak_wavelength is not None and result.two_theta is not None:
                result.q_vector = calculate_two_theta_or_scattering_vector(
                    two_theta=result.two_theta, wavelength=result.source_peak_wavelength)
        except Exception:
            logger.warning("Unable to convert from two_theta to q_vector vice-versa")
        self.xrd_settings = settings
        self.results = [result]

        if not archive.results:
            archive.results = Results()
        if not archive.results.properties:
            archive.results.properties = Properties()
        if not archive.results.properties.structural:
            archive.results.properties.structural = StructuralProperties(
                diffraction_patterns=[DiffractionPattern(
                    incident_beam_wavelength=result.source_peak_wavelength,
                    two_theta_angles=result.two_theta,
                    intensity=result.intensity,
                    q_vector=result.q_vector,
                ) for result in self.results]
            )
        if not archive.results.method:
            archive.results.method = Method(
                method_name='XRD',
                measurement=MeasurementMethod(
                    xrd=XRDMethod(
                        diffraction_method_name=self.diffraction_method_name
                    )
                )
            )


class NOMADMeasurementsCategory(EntryDataCategory):
    m_def = Category(label='NOMAD Measurements', categories=[EntryDataCategory])


class ELNXRayDiffraction(XRayDiffraction, EntryData):
    m_def = Section(
        categories=[NOMADMeasurementsCategory],
        label='X-Ray Diffraction (XRD)',
        a_eln=dict(
            lane_width='800px',
        ),
        a_template=dict(
            measurement_identifiers=dict(),
        ),
        a_plot=[
            {
                'label': 'Intensity (log scale)',
                'x': 'results/:/two_theta',
                'y': 'results/:/intensity',
                'layout': {'yaxis': {'type': 'log'}},
            },
            {
                'label': 'Intensity (lin scale)',
                'x': 'results/:/two_theta',
                'y': 'results/:/intensity',
                'layout': {'yaxis': {'type': 'lin'}},
            }
        ],
    )
    measurement_identifiers = SubSection(
        section_def=ReadableIdentifiers,
    )
    diffraction_method_name = XRayDiffraction.diffraction_method_name.m_copy()
    diffraction_method_name.m_annotations['eln'] = ELNAnnotation(
        component=ELNComponentEnum.EnumEditQuantity,
    )


m_package.__init_metainfo__()
