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
    Callable,
)
import numpy as np
import plotly.express as px
from scipy.interpolate import griddata

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
# from nomad.datamodel.metainfo.eln.nexus_data_converter import populate_nexus_subsection
from nomad_measurements import (
    NOMADMeasurementsCategory,
)
from nomad_measurements.xrd import readers
from nomad_measurements.utils import merge_sections, get_bounding_range_2d

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import (
        EntryArchive,
    )
    from structlog.stdlib import (
        BoundLogger,
    )
    import pint
    from pynxtools.dataconverter.template import Template

m_package = Package(name='nomad_xrd')


def populate_nexus_subsection(**kwargs):
    raise NotImplementedError

def handle_nexus_subsection(
        xrd_template: 'Template',
        nexus_out: str,
        archive: 'EntryArchive',
        logger: 'BoundLogger'
    ):
    '''
    Function for populating the NeXus section from the xrd_template.

    Args:
        xrd_template (Template): The xrd data in a NeXus Template.
        nexus_out (str): The name of the optional NeXus output file.
        archive (EntryArchive): The archive containing the section.
        logger (BoundLogger): A structlog logger.
    '''
    nxdl_name = 'NXxrd_pan'
    if nexus_out:
        if not nexus_out.endswith('.nxs'):
            nexus_out = nexus_out + '.nxs'
        populate_nexus_subsection(
            template=xrd_template,
            app_def=nxdl_name,
            archive=archive,
            logger=logger,
            output_file_path=nexus_out,
            on_temp_file=False,
        )
    else:
        populate_nexus_subsection(
            template=xrd_template,
            app_def=nxdl_name,
            archive=archive,
            logger=logger,
            output_file_path=nexus_out,
            on_temp_file=True,
        )


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


def calculate_q_vectors_RSM(
    wavelength: 'pint.Quantity',
    two_theta: 'pint.Quantity',
    omega: 'pint.Quantity',
):
    """
    Calculate the q-vectors for RSM scans in coplanar configuration.

    Args:
        wavelength (pint.Quantity): Wavelength of the X-ray source.
        two_theta (pint.Quantity): Array of 2theta or detector angles.
        omega (pint.Quantity): Array of omega or rocking/incidence angles.

    Returns:
        tuple[pint.Quantity, pint.Quantity]: Tuple of q-vectors.
    """
    omega = omega[:, None] * np.ones_like(two_theta.magnitude)
    qx = (
        2
        * np.pi
        / wavelength
        * (
            np.cos(two_theta.to('radian') - omega.to('radian'))
            - np.cos(omega.to('radian'))
        )
    )
    qz = (
        2
        * np.pi
        / wavelength
        * (
            np.sin(two_theta.to('radian') - omega.to('radian'))
            + np.sin(omega.to('radian'))
        )
    )

    q_parallel = qx
    q_perpendicular = qz

    return q_parallel, q_perpendicular


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
    """
    Section containing the result of an X-ray diffraction scan.
    """

    m_def = Section()

    intensity = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        unit='dimensionless',
        description='The count at each 2-theta value, dimensionless',
    )
    two_theta = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        unit='deg',
        description='The 2-theta range of the diffractogram',
    )
    q_norm = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        unit='meter**(-1)',
        description='The norm of scattering vector *Q* of the diffractogram',
    )
    omega = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        unit='deg',
        description='The omega range of the diffractogram',
    )
    phi = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        unit='deg',
        description='The phi range of the diffractogram',
    )
    chi = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        unit='deg',
        description='The chi range of the diffractogram',
    )
    source_peak_wavelength = Quantity(
        type=np.dtype(np.float64),
        unit='angstrom',
        description='Wavelength of the X-ray source. Used to convert from 2-theta to Q\
        and vice-versa.',
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


class XRDResult1D(XRDResult):
    """
    Section containing the result of a 1D X-ray diffraction scan.
    """

    m_def = Section()

    def generate_plots(self, archive: 'EntryArchive', logger: 'BoundLogger'):
        """
        Plot the 1D diffractogram.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.

        Returns:
            (dict, dict): line_linear, line_log
        """
        plots = []
        if self.two_theta is None or self.intensity is None:
            return plots

        x = self.two_theta.to('degree').magnitude
        y = self.intensity.magnitude

        fig_line_linear = px.line(
            x=x,
            y=y,
        )
        fig_line_linear.update_layout(
            title={
                'text': 'Intensity vs 2θ (linear scale)',
                'x': 0.5,
                'xanchor': 'center',
            },
            xaxis_title='2θ (°)',
            yaxis_title='Intensity',
            xaxis=dict(
                fixedrange=False,
            ),
            yaxis=dict(
                fixedrange=False,
            ),
            template='plotly_white',
            width=600,
            height=600,
        )
        plots.append(
            PlotlyFigure(
                label='Intensity (linear scale)',
                index=1,
                figure=fig_line_linear.to_plotly_json(),
            )
        )

        fig_line_log = px.line(
            x=x,
            y=y,
            log_y=True,
        )
        fig_line_log.update_layout(
            title={
                'text': 'Intensity vs 2θ (log scale)',
                'x': 0.5,
                'xanchor': 'center',
            },
            xaxis_title='2θ (°)',
            yaxis_title='Intensity',
            xaxis=dict(
                fixedrange=False,
            ),
            yaxis=dict(
                fixedrange=False,
            ),
            template='plotly_white',
            width=600,
            height=600,
        )
        plots.append(
            PlotlyFigure(
                label='Intensity (log scale)',
                index=0,
                figure=fig_line_log.to_plotly_json(),
            )
        )

        return plots

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger'):
        """
        The normalize function of the `XRDResult` section.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        super().normalize(archive, logger)
        if self.name is None:
            if self.scan_axis:
                self.name = f'{self.scan_axis} Scan Result'
            else:
                self.name = 'XRD Scan Result'
        if self.source_peak_wavelength is not None:
            self.q_norm, self.two_theta = calculate_two_theta_or_q(
                wavelength=self.source_peak_wavelength,
                two_theta=self.two_theta,
                q=self.q_norm,
            )


class XRDResultRSM(XRDResult):
    """
    Section containing the result of a Reciprocal Space Map (RSM) scan.
    """

    m_def = Section()
    q_parallel = Quantity(
        type=np.dtype(np.float64),
        shape=['*', '*'],
        unit='meter**(-1)',
        description='The scattering vector *Q_parallel* of the diffractogram',
    )
    q_perpendicular = Quantity(
        type=np.dtype(np.float64),
        shape=['*', '*'],
        unit='meter**(-1)',
        description='The scattering vector *Q_perpendicular* of the diffractogram',
    )
    intensity = Quantity(
        type=np.dtype(np.float64),
        shape=['*', '*'],
        unit='dimensionless',
        description='The count at each position, dimensionless',
    )

    def generate_plots(self, archive: 'EntryArchive', logger: 'BoundLogger'):
        """
        Plot the 2D RSM diffractogram.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.

        Returns:
            (dict, dict): json_2theta_omega, json_q_vector
        """
        plots = []
        if self.two_theta is None or self.intensity is None or self.omega is None:
            return plots

        # Plot for 2theta-omega RSM
        # Zero values in intensity become -inf in log scale and are not plotted
        x = self.omega.to('degree').magnitude
        y = self.two_theta.to('degree').magnitude
        z = self.intensity.magnitude
        log_z = np.log10(z)
        x_range, y_range = get_bounding_range_2d(x, y)

        fig_2theta_omega = px.imshow(
            img=np.around(log_z, 3).T,
            x=np.around(x, 3),
            y=np.around(y, 3),
        )
        fig_2theta_omega.update_coloraxes(
            colorscale='inferno',
            cmin=np.nanmin(log_z[log_z != -np.inf]),
            cmax=log_z.max(),
            colorbar={
                'len': 0.9,
                'title': '<em>log<sub>10</sub></em> Intensity<em></em>',
                'ticks': 'outside',
                'tickformat': '5',
            },
        )
        fig_2theta_omega.update_layout(
            title={
                    'text': 'Reciprocal Space Map over 2θ-ω',
                    'x': 0.5,
                    'xanchor': 'center',
                },
            xaxis_title='ω (°)',
            yaxis_title='2θ (°)',
            xaxis=dict(
                autorange=False,
                fixedrange=False,
                range=x_range,
            ),
            yaxis=dict(
                autorange=False,
                fixedrange=False,
                range=y_range,
            ),
            template='plotly_white',
            width=600,
            height=600,
        )
        plots.append(
            PlotlyFigure(
                label='RSM 2θ-ω',
                index=1,
                figure=fig_2theta_omega.to_plotly_json(),
            ),
        )

        # Plot for RSM in Q-vectors
        if self.q_parallel is not None and self.q_perpendicular is not None:
            x = self.q_parallel.to('1/angstrom').magnitude.flatten()
            y = self.q_perpendicular.to('1/angstrom').magnitude.flatten()
            # q_vectors lead to irregular grid
            # generate a regular grid using interpolation
            x_regular = np.linspace(x.min(), x.max(), z.shape[0])
            y_regular = np.linspace(y.min(), y.max(), z.shape[1])
            x_grid, y_grid = np.meshgrid(x_regular, y_regular)
            z_interpolated = griddata(
                points=(x, y),
                values=z.flatten(),
                xi=(x_grid, y_grid),
                method='linear',
                fill_value=z.min(),
            )
            log_z_interpolated = np.log10(z_interpolated)
            x_range, y_range = get_bounding_range_2d(x_regular, y_regular)

            fig_q_vector = px.imshow(
                img=np.around(log_z_interpolated, 3),
                x=np.around(x_regular, 3),
                y=np.around(y_regular, 3),
            )
            fig_q_vector.update_coloraxes(
                colorscale='inferno',
                cmin=np.nanmin(log_z[log_z != -np.inf]),
                cmax=log_z_interpolated.max(),
                colorbar={
                    'len': 0.9,
                    'title': '<em>log<sub>10</sub></em> Intensity<em></em>',
                    'ticks': 'outside',
                    'tickformat': '5',
                },
            )
            fig_q_vector.update_layout(
                title={
                    'text': 'Reciprocal Space Map over Q-vectors',
                    'x': 0.5,
                    'xanchor': 'center',
                },
                xaxis_title='<em>q<sub>&#x2016;</sub></em> (Å<sup>-1</sup>)', # q ‖
                yaxis_title='<em>q<sub>&#x22A5;</sub></em> (Å<sup>-1</sup>)', # q ⊥
                xaxis=dict(
                    autorange=False,
                    fixedrange=False,
                    range=x_range,
                ),
                yaxis=dict(
                    autorange=False,
                    fixedrange=False,
                    range=y_range,
                ),
                template='plotly_white',
                width=600,
                height=600,
            )
            plots.append(
                PlotlyFigure(
                    label='RSM Q-Vectors',
                    index=0,
                    figure=fig_q_vector.to_plotly_json(),
                ),
            )

        return plots

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger'):
        super().normalize(archive, logger)
        if self.name is None:
            self.name = 'RSM Scan Result'
        var_axis = 'omega'
        if self.source_peak_wavelength is not None:
            for var_axis in ['omega', 'chi', 'phi']:
                if (
                    self[var_axis] is not None
                    and len(np.unique(self[var_axis].magnitude)) > 1
                ):
                    self.q_parallel, self.q_perpendicular = calculate_q_vectors_RSM(
                        wavelength=self.source_peak_wavelength,
                        two_theta=self.two_theta * np.ones_like(self.intensity),
                        omega=self[var_axis],
                    )
                    break

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
                'Powder X-Ray Diffraction (PXRD)',
                'Single Crystal X-Ray Diffraction (SCXRD)',
                'High-Resolution X-Ray Diffraction (HRXRD)',
                'Small-Angle X-Ray Scattering (SAXS)',
                'X-Ray Reflectivity (XRR)',
                'Grazing Incidence X-Ray Diffraction (GIXRD)',
                # 'Reciprocal Space Mapping (RSM)',
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
        # | **Reciprocal Space Mapping (RSM)**                         | High-resolution XRD method to measure a reciprocal space map. Provides additional information used to aid the interpretation of peak displacement, peak broadening or peak overlap.                                                                                                                                                             |
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
                    q_vector=result.q_norm,
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


class ELNXRayDiffraction(XRayDiffraction, EntryData, PlotSection):
    """
    Example section for how XRayDiffraction can be implemented with a general reader for
    common XRD file types.
    """

    m_def = Section(
        categories=[NOMADMeasurementsCategory],
        label='X-Ray Diffraction (XRD)',
        a_eln=ELNAnnotation(
            lane_width='800px',
            hide=['generate_nexus_file'],
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
    generate_nexus_file = Quantity(
        type=bool,
        description='Whether or not to generate a NeXus output file (if possible).',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.BoolEditQuantity,
            label='Generate NeXus file',
        ),
    )

    def get_read_write_functions(self) -> tuple[Callable, Callable]:
        """
        Method for getting the correct read and write functions for the current data file.

        Returns:
            tuple[Callable, Callable]: The read, write functions.
        """
        if self.data_file.endswith('.rasx'):
            return readers.read_rigaku_rasx, self.write_xrd_data
        if self.data_file.endswith('.xrdml'):
            return readers.read_panalytical_xrdml, self.write_xrd_data
        if self.data_file.endswith('.brml'):
            return readers.read_bruker_brml, self.write_xrd_data
        return None, None

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

        scan_type = metadata_dict.get('scan_type', None)
        if scan_type == 'line':
            result = XRDResult1D(
                intensity=xrd_dict.get('intensity', None),
                two_theta=xrd_dict.get('2Theta', None),
                omega=xrd_dict.get('Omega', None),
                chi=xrd_dict.get('Chi', None),
                phi=xrd_dict.get('Phi', None),
                scan_axis=metadata_dict.get('scan_axis', None),
                integration_time=xrd_dict.get('countTime', None),
            )
            result.normalize(archive, logger)

        elif scan_type == 'rsm':
            result = XRDResultRSM(
                intensity=xrd_dict.get('intensity', None),
                two_theta=xrd_dict.get('2Theta', None),
                omega=xrd_dict.get('Omega', None),
                chi=xrd_dict.get('Chi', None),
                phi=xrd_dict.get('Phi', None),
                scan_axis=metadata_dict.get('scan_axis', None),
                integration_time=xrd_dict.get('countTime', None),
            )
            result.normalize(archive, logger)
        else:
            raise NotImplementedError(f'Scan type `{scan_type}` is not supported.')

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

        samples = []
        if metadata_dict.get('sample_id', None) is not None:
            sample = CompositeSystemReference(
                lab_id=metadata_dict['sample_id'],
            )
            sample.normalize(archive, logger)
            samples.append(sample)

        xrd = ELNXRayDiffraction(
            results = [result],
            xrd_settings = xrd_settings,
            samples = samples,
        )
        merge_sections(self, xrd, logger)

    def write_nx_xrd(
            self,
            xrd_dict: 'Template',
            archive: 'EntryArchive',
            logger: 'BoundLogger',
        ) -> None:
        '''
        Populate `ELNXRayDiffraction` section from a NeXus Template.

        Args:
            xrd_dict (Dict[str, Any]): A dictionary with the XRD data.
            archive (EntryArchive): The archive containing the section.
            logger (BoundLogger): A structlog logger.
        '''
        # TODO add the result section based on the scan_type
        result = XRDResult(
            intensity=xrd_dict.get(
                '/ENTRY[entry]/2theta_plot/intensity',
                None,
            ),
            two_theta=xrd_dict.get(
                '/ENTRY[entry]/2theta_plot/two_theta',
                None,
            ),
            omega=xrd_dict.get(
                '/ENTRY[entry]/2theta_plot/omega',
                None,
            ),
            chi=xrd_dict.get(
                '/ENTRY[entry]/2theta_plot/chi',
                None),
            phi=xrd_dict.get(
                '/ENTRY[entry]/2theta_plot/phi',
                None,
            ),
            scan_axis=xrd_dict.get(
                '/ENTRY[entry]/INSTRUMENT[instrument]/DETECTOR[detector]/scan_axis',
                None,
            ),
            integration_time=xrd_dict.get(
                '/ENTRY[entry]/COLLECTION[collection]/count_time',
                None
            ),
        )
        result.normalize(archive, logger)

        source = XRayTubeSource(
            xray_tube_material=xrd_dict.get(
                '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/xray_tube_material',
                None,
            ),
            kalpha_one=xrd_dict.get(
                '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/k_alpha_one',
                None,
            ),
            kalpha_two=xrd_dict.get(
                '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/k_alpha_two',
                None,
                ),
            ratio_kalphatwo_kalphaone=xrd_dict.get(
                '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/ratio_k_alphatwo_k_alphaone',
                None,
                ),
            kbeta=xrd_dict.get(
                '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/kbeta',
                None,
            ),
            xray_tube_voltage=xrd_dict.get(
                'ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/xray_tube_voltage',
                None
            ),
            xray_tube_current=xrd_dict.get(
                '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/xray_tube_current',
                None,
            ),
        )
        source.normalize(archive, logger)

        xrd_settings = XRDSettings(
            source=source
        )
        xrd_settings.normalize(archive, logger)

        sample = CompositeSystemReference(
            lab_id=xrd_dict.get(
                '/ENTRY[entry]/SAMPLE[sample]/sample_id', 
                None,
                ),
        )
        sample.normalize(archive, logger)

        xrd = ELNXRayDiffraction(
            results = [result],
            xrd_settings = xrd_settings,
            samples = [sample],
        )
        merge_sections(self, xrd, logger)

        nexus_output = None
        if self.generate_nexus_file:
            archive_name = archive.metadata.mainfile.split('.')[0]
            nexus_output = f'{archive_name}_output.nxs'
        handle_nexus_subsection(
            xrd_dict,
            nexus_output,
            archive,
            logger,
        )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger'):
        """
        The normalize function of the `ELNXRayDiffraction` section.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        if self.data_file is not None:
            read_function, write_function = self.get_read_write_functions()
            if read_function is None or write_function is None:
                logger.warn(
                    f'No compatible reader found for the file: "{self.data_file}".'
                )
            else:
                with archive.m_context.raw_file(self.data_file) as file:
                    xrd_dict = read_function(file.name, logger)
                write_function(xrd_dict, archive, logger)
        super().normalize(archive, logger)
        if not self.results:
            return
        self.figures = self.results[0].generate_plots(archive, logger)


m_package.__init_metainfo__()
