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
    Dict,
    Any,
)
import numpy as np
import plotly.express as px

from nomad.datamodel.metainfo.basesections import (
    Measurement,
    MeasurementResult,
    CompositeSystemReference,
    ReadableIdentifiers,
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
from nomad.datamodel.results import (
    Results,
    Properties,
    StructuralProperties,
    DiffractionPattern,
    Method,
    MeasurementMethod,
    XRDMethod,
)
from nomad.datamodel.metainfo.plot import (
    PlotSection,
    PlotlyFigure,
)

from nomad_measurements import (
    NOMADMeasurementsCategory,
)
from nomad_measurements.xrd.readers import (
    read_xrd,
)

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import (
        EntryArchive,
    )
    from structlog.stdlib import (
        BoundLogger,
    )
    import pint

m_package = Package(name='nomad-measurements')


def calculate_two_theta_or_q(
        wavelength: 'pint.Quantity',
        q: 'pint.Quantity'=None,
        two_theta: 'pint.Quantity'=None
    ) -> tuple['pint.Quantity', 'pint.Quantity']:
    '''
    Calculate the two-theta array from the scattering vector (q) or vice-versa,
    given the wavelength of the X-ray source.

    Args:
        wavelength (pint.Quantity): Wavelength of the X-ray source.
        q (pint.Quantity, optional): Array of scattering vectors. Defaults to None.
        two_theta (pint.Quantity, optional): Array of two-theta angles. Defaults to None.

    Returns:
       tuple[pint.Quantity, pint.Quantity]: Tuple of scattering vector, two-theta angles.
    '''
    if q is not None and two_theta is None:
        return q, 2 * np.arcsin(q * wavelength / (4 * np.pi))
    if two_theta is not None and q is None:
        return (4 * np.pi / wavelength) * np.sin(two_theta.to('radian') / 2), two_theta
    return q, two_theta


def estimate_kalpha_wavelengths(source_material):
    '''
    Estimate the K-alpha1 and K-alpha2 wavelengths of an X-ray source given the material 
    of the source.

    Args:
        source_material (str): Material of the X-ray source, such as 'Cu', 'Fe', 'Mo',
        'Ag', 'In', 'Ga', etc.

    Returns:
        Tuple[float, float]: Estimated K-alpha1 and K-alpha2 wavelengths of the X-ray
        source, in angstroms.
    '''
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
        kalpha_one_wavelength, kalpha_two_wavelength = kalpha_wavelengths[source_material]
    except KeyError as exc:
        raise ValueError('Unknown X-ray source material.') from exc

    return kalpha_one_wavelength, kalpha_two_wavelength


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

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger'):
        '''
        The normalize function of the `XRayTubeSource` section.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        '''
        super().normalize(archive, logger)
        if self.kalpha_one is None and self.xray_tube_material is not None:
            self.kalpha_one, self.kalpha_two = estimate_kalpha_wavelengths(
                source_material=self.xray_tube_material,
            )


class XRDSettings(ArchiveSection):
    '''
    Section containing the settings for an XRD measurement.
    '''
    source = SubSection(section_def=XRayTubeSource)


class XRDResult(MeasurementResult):
    '''
    Section containing the result of an X-ray diffraction scan.
    '''
    m_def = Section()

    def derive_n_values(self):
        '''
        Method for determining the length of the diffractogram array.

        Returns:
            int: The length of the diffractogram array.
        '''
        if self.intensity is not None:
            return len(self.intensity)
        if self.two_theta is not None:
            return len(self.two_theta)
        return 0

    n_values = Quantity(
        type=int,
        derived=derive_n_values,
    )
    two_theta = Quantity(
        type=np.dtype(np.float64), shape=['n_values'],
        unit='deg',
        description='The 2-theta range of the diffractogram',
        a_plot={
            'x': 'two_theta', 'y': 'intensity'
        },
    )
    q_vector = Quantity(
        type=np.dtype(np.float64), shape=['*'],
        unit='meter**(-1)',
        description='The scattering vector *Q* of the diffractogram',
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
        description='The omega range of the diffractogram',
    )
    phi = Quantity(
        type=np.dtype(np.float64), shape=['*'],
        unit='deg',
        description='The phi range of the diffractogram',
    )
    chi = Quantity(
        type=np.dtype(np.float64), shape=['*'],
        unit='deg',
        description='The chi range of the diffractogram',
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

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger'):
        '''
        The normalize function of the `XRDResult` section.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        '''
        super().normalize(archive, logger)
        if self.source_peak_wavelength is not None:
            self.q_vector, self.two_theta = calculate_two_theta_or_q(
                wavelength=self.source_peak_wavelength,
                two_theta=self.two_theta,
                q=self.q_vector,
            )


class XRayDiffraction(Measurement):
    '''
    Generic X-ray diffraction measurement.
    '''
    m_def = Section()
    method = Quantity(
        type=str,
        default='X-Ray Diffraction (XRD)',
    )
    xrd_settings = SubSection(
        section_def=XRDSettings,
    )
    diffraction_method_name = Quantity(
        type=MEnum(
            [
                'Powder X-ray Diffraction (PXRD)',
                'Single Crystal X-ray Diffraction (SCXRD)',
                'High-Resolution X-ray Diffraction (HRXRD)',
                'Small-Angle X-ray Scattering (SAXS)',
                'X-ray Reflectivity (XRR)',
                'Grazing Incidence X-ray Diffraction (GIXRD)',
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

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger'):
        '''
        The normalize function of the `XRayDiffraction` section.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        '''
        super().normalize(archive, logger)
        if (
            self.xrd_settings is not None
            and self.xrd_settings.source is not None
            and self.xrd_settings.source.kalpha_one is not None
        ):
            for result in self.results:
                if result.source_peak_wavelength is None:
                    result.source_peak_wavelength = self.xrd_settings.source.kalpha_one
                    result.normalize(archive, logger)
        if not archive.results:
            archive.results = Results()
        if not archive.results.properties:
            archive.results.properties = Properties()
        if not archive.results.properties.structural:
            archive.results.properties.structural = StructuralProperties(
                diffraction_pattern=[DiffractionPattern(
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


class ELNXRayDiffraction(XRayDiffraction, PlotSection, EntryData):
    '''
    Example section for how XRayDiffraction can be implemented with a general reader for
    common XRD file types.
    '''
    m_def = Section(
        categories=[NOMADMeasurementsCategory],
        label='X-Ray Diffraction (XRD)',
        a_eln=ELNAnnotation(
            lane_width='800px',
        ),
        a_template={
            'measurement_identifiers': {},
        },
    )
    data_file = Quantity(
        type=str,
        description='Data file containing the diffractogram',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.FileEditQuantity,
        ),
    )
    measurement_identifiers = SubSection(
        section_def=ReadableIdentifiers,
    )
    diffraction_method_name = XRayDiffraction.diffraction_method_name.m_copy()
    diffraction_method_name.m_annotations['eln'] = ELNAnnotation(
        component=ELNComponentEnum.EnumEditQuantity,
    )

    def write_xrd_data(
            self,
            xrd_dict: Dict[str, Any],
            archive: 'EntryArchive',
            logger: 'BoundLogger',
        ) -> None:
        '''
        Write method for populating the `ELNXRayDiffraction` section from a dict.

        Args:
            xrd_dict (Dict[str, Any]): A dictionary with the XRD data.
            archive (EntryArchive): The archive containing the section.
            logger (BoundLogger): A structlog logger.
        '''
        metadata_dict: dict = xrd_dict.get('metadata', {})
        source_dict: dict = metadata_dict.get('source', {})

        result = XRDResult(
            intensity=xrd_dict.get('detector', None),
            two_theta=xrd_dict.get('2Theta', None),
            omega=xrd_dict.get('Omega',None),
            chi=xrd_dict.get('Chi', None),
            phi=xrd_dict.get('Phi', None),
            scan_axis=metadata_dict.get('scan_axis', None),
            integration_time=xrd_dict.get('countTime',None),
        )
        result.normalize(archive, logger)

        source = XRayTubeSource(
            xray_tube_material=source_dict.get('anode_material', None),
            kalpha_one=source_dict.get('kAlpha1', None),
            kalpha_two=source_dict.get('kAlpha2', None),
            ratio_kalphatwo_kalphaone=source_dict.get('ratioKAlpha2KAlpha1', None),
            kbeta=source_dict.get('kBeta', None),
            xray_tube_voltage=source_dict.get('voltage', None),
            xray_tube_current=source_dict.get('current', None),
        )
        source.normalize(archive, logger)

        xrd_settings = XRDSettings(
            source=source
        )
        xrd_settings.normalize(archive, logger)

        sample = CompositeSystemReference(
            lab_id=metadata_dict.get('sample_id', None),
        )
        sample.normalize(archive, logger)

        self.results = [result]
        self.xrd_settings = xrd_settings
        self.samples = [sample]

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger'):
        '''
        The normalize function of the `ELNXRayDiffraction` section.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        '''
        if not self.results and self.data_file is not None:
            with archive.m_context.raw_file(self.data_file) as file:
                xrd_dict = read_xrd(file.name, logger)
            self.write_xrd_data(xrd_dict, archive, logger)
        super().normalize(archive, logger)

        if not self.results:
            return

        line_linear = px.line(
            x=self.results[0].two_theta,
            y=self.results[0].intensity,
            labels={
                'x': '2θ (°)',
                'y': 'Intensity',
            },
            title='Intensity (linear scale)',
        )
        line_log = px.line(
            x=self.results[0].two_theta,
            y=self.results[0].intensity,
            log_y=True,
            labels={
                'x': '2θ (°)',
                'y': 'Intensity',
            },
            title='Intensity (log scale)',
        )
        self.figures.extend([
            PlotlyFigure(
                label="Log Plot",
                index=1,
                figure=line_log.to_plotly_json(),
            ),
            PlotlyFigure(
                label="Linear Plot",
                index=2,
                figure=line_linear.to_plotly_json(),
            ),
        ])


m_package.__init_metainfo__()
