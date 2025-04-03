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
from collections.abc import Callable
from typing import (
    TYPE_CHECKING,
    Any,
)

import numpy as np
import plotly.express as px
from fairmat_readers_xrd import (
    read_bruker_brml,
    read_panalytical_xrdml,
    read_rigaku_rasx,
)
from nomad.config import config
from nomad.datamodel.data import (
    ArchiveSection,
    EntryData,
)
from nomad.datamodel.hdf5 import (
    HDF5Reference,
)
from nomad.datamodel.metainfo.annotations import (
    BrowserAnnotation,
    ELNAnnotation,
    ELNComponentEnum,
    Filter,
    H5WebAnnotation,
    SectionProperties,
)
from nomad.datamodel.metainfo.basesections import (
    CompositeSystemReference,
    Measurement,
    MeasurementResult,
    ReadableIdentifiers,
)
from nomad.datamodel.metainfo.plot import PlotlyFigure, PlotSection
from nomad.datamodel.results import (
    DiffractionPattern,
    MeasurementMethod,
    Method,
    Properties,
    Results,
    StructuralProperties,
    XRDMethod,
)
from nomad.metainfo import (
    MEnum,
    Quantity,
    SchemaPackage,
    Section,
    SubSection,
)
from scipy.interpolate import griddata

from nomad_measurements.general import (
    NOMADMeasurementsCategory,
)
from nomad_measurements.utils import (
    Dataset,
    HDF5Handler,
    get_bounding_range_2d,
    get_entry_id_from_file_name,
    get_reference,
    merge_sections,
)
from nomad_measurements.xrd.nx import NEXUS_DATASET_MAP

if TYPE_CHECKING:
    import pint
    from nomad.datamodel.datamodel import (
        EntryArchive,
    )
    from structlog.stdlib import (
        BoundLogger,
    )

schema_config = config.get_plugin_entry_point('nomad_measurements.xrd:schema')

m_package = SchemaPackage(aliases=['nomad_measurements.xrd.parser.parser'])


def calculate_two_theta_or_q(
    wavelength: 'pint.Quantity',
    q: 'pint.Quantity' = None,
    two_theta: 'pint.Quantity' = None,
) -> tuple['pint.Quantity', 'pint.Quantity']:
    """
    Calculate the two-theta array from the scattering vector (q) or vice-versa,
    given the wavelength of the X-ray source.

    Args:
        wavelength (pint.Quantity): Wavelength of the X-ray source.
        q (pint.Quantity, optional): Array of scattering vectors. Defaults to None.
        two_theta (pint.Quantity, optional): Array of two-theta angles.
            Defaults to None.

    Returns:
        tuple[pint.Quantity, pint.Quantity]: Tuple of scattering vector, two-theta
            angles.
    """
    if q is not None and two_theta is None:
        return q, 2 * np.arcsin(q * wavelength / (4 * np.pi))
    if two_theta is not None and q is None:
        return (4 * np.pi / wavelength) * np.sin(two_theta.to('radian') / 2), two_theta
    return q, two_theta


def calculate_q_vectors_rsm(
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
    # Dictionary of K-alpha1 and K-alpha2 wavelengths for various X-ray source
    # materials, in angstroms
    kalpha_wavelengths = {
        'Cr': (2.2910, 2.2936),
        'Fe': (1.9359, 1.9397),
        'Cu': (1.5406, 1.5444),
        'Mo': (0.7093, 0.7136),
        'Ag': (0.5594, 0.5638),
        'In': (0.6535, 0.6577),
        'Ga': (1.2378, 1.2443),
    }

    try:
        kalpha_one_wavelength, kalpha_two_wavelength = kalpha_wavelengths[
            source_material
        ]
    except KeyError as exc:
        raise ValueError('Unknown X-ray source material.') from exc

    return kalpha_one_wavelength, kalpha_two_wavelength


class XRayTubeSource(ArchiveSection):
    """
    X-ray tube source used in conventional diffractometers.
    """

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
        """
        The normalize function of the `XRayTubeSource` section.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        super().normalize(archive, logger)
        if self.kalpha_one is None and self.xray_tube_material is not None:
            self.kalpha_one, self.kalpha_two = estimate_kalpha_wavelengths(
                source_material=self.xray_tube_material,
            )


class XRDSettings(ArchiveSection):
    """
    Section containing the settings for an XRD measurement.
    """

    source = SubSection(section_def=XRayTubeSource)


class IntensityPlot(ArchiveSection):
    """
    Section for plotting the intensity over 2-theta. A separate sub-section allows to
    create a separate group in `.h5` file. Attributes are added to the group to generate
    the plot.
    """

    m_def = Section(
        a_h5web=H5WebAnnotation(
            axes=['two_theta', 'omega', 'phi', 'chi'], signal='intensity'
        )
    )
    intensity = Quantity(
        type=HDF5Reference,
        description='The count at each 2-theta value, dimensionless',
    )
    two_theta = Quantity(
        type=HDF5Reference,
        description='The 2-theta range of the diffractogram',
    )
    omega = Quantity(
        type=HDF5Reference,
        description='The omega range of the diffractogram',
    )
    phi = Quantity(
        type=HDF5Reference,
        description='The phi range of the diffractogram',
    )
    chi = Quantity(
        type=HDF5Reference,
        description='The chi range of the diffractogram',
    )

    def generate_hdf5_plots(self, hdf5_handler: HDF5Handler):
        """
        Add datasets and attributes to the HDF5 file for plotting the intensity over
        available positions.

        Args:
            hdf5_handler (HDF5Handler): The handler for the HDF5 file.
        """
        prefix = '/ENTRY[entry]/experiment_result'

        intensity = hdf5_handler.read_dataset(path=f'{prefix}/intensity')
        two_theta = hdf5_handler.read_dataset(path=f'{prefix}/two_theta')
        if intensity is None or two_theta is None:
            return

        hdf5_handler.add_dataset(
            path=f'{prefix}/intensity_plot/two_theta',
            dataset=Dataset(
                data=f'{prefix}/two_theta',
                archive_path='data.results[0].intensity_plot.two_theta',
                internal_reference=True,
            ),
            validate_path=False,
        )
        hdf5_handler.add_dataset(
            path=f'{prefix}/intensity_plot/intensity',
            dataset=Dataset(
                data=f'{prefix}/intensity',
                archive_path='data.results[0].intensity_plot.intensity',
                internal_reference=True,
            ),
            validate_path=False,
        )
        hdf5_handler.add_attribute(
            path=f'{prefix}/intensity_plot',
            params=dict(
                axes='two_theta',
                signal='intensity',
                NX_class='NXdata',
            ),
        )
        if isinstance(self.m_parent, XRDResult1DHDF5):
            return

        for var_axis in ['omega', 'phi', 'chi']:
            var_axis_data = hdf5_handler.read_dataset(
                path=f'/ENTRY[entry]/experiment_result/{var_axis}'
            )
            if var_axis_data is not None:
                hdf5_handler.add_dataset(
                    path=f'{prefix}/intensity_plot/{var_axis}',
                    dataset=Dataset(
                        data=f'{prefix}/{var_axis}',
                        archive_path=f'data.results[0].intensity_plot.{var_axis}',
                        internal_reference=True,
                    ),
                    validate_path=False,
                )
                hdf5_handler.add_attribute(
                    path=f'{prefix}/intensity_plot',
                    params=dict(
                        axes=[var_axis, 'two_theta'],
                        signal='intensity',
                        NX_class='NXdata',
                    ),
                )
                break


class IntensityScatteringVectorPlot(ArchiveSection):
    """
    Section for plotting the intensity over scattering vector. A separate sub-section
    allows to create a separate group in `.h5` file. Attributes are added to the group
    to generate the plot.
    """

    m_def = Section(
        a_h5web=H5WebAnnotation(
            axes=['q_parallel', 'q_perpendicular', 'q_norm'], signal='intensity'
        )
    )
    intensity = Quantity(
        type=HDF5Reference,
        description="""
        The count at each q value. In case of RSM, it contains interpolated values of
        `intensity` at regularized grid of `q` vectors.
        """,
    )
    q_norm = Quantity(
        type=HDF5Reference,
        description='The q range of the diffractogram',
    )
    q_parallel = Quantity(
        type=HDF5Reference,
        description='The regularized grid of `q_parallel` range for plotting.',
    )
    q_perpendicular = Quantity(
        type=HDF5Reference,
        description='The regularized grid of `q_perpendicular` range for plotting.',
    )

    def generate_hdf5_plots(self, hdf5_handler: HDF5Handler):
        """
        Add datasets and attributes to the HDF5 file for plotting the intensity over
        scattering vector.

        Args:
            hdf5_handler (HDF5Handler): The handler for the HDF5 file.
        """
        prefix = '/ENTRY[entry]/experiment_result'

        intensity = hdf5_handler.read_dataset(path=f'{prefix}/intensity')
        q_norm = hdf5_handler.read_dataset(path=f'{prefix}/q_norm')
        q_parallel = hdf5_handler.read_dataset(path=f'{prefix}/q_parallel')
        q_perpendicular = hdf5_handler.read_dataset(path=f'{prefix}/q_perpendicular')

        if intensity is None:
            return

        if q_norm is not None:
            hdf5_handler.add_dataset(
                path=f'{prefix}/intensity_scattering_vector_plot/intensity',
                dataset=Dataset(
                    data=f'{prefix}/intensity',
                    archive_path='data.results[0].intensity_scattering_vector_plot.intensity',
                    internal_reference=True,
                ),
                validate_path=False,
            )
            hdf5_handler.add_dataset(
                path=f'{prefix}/intensity_scattering_vector_plot/q_norm',
                dataset=Dataset(
                    data=f'{prefix}/q_norm',
                    archive_path='data.results[0].intensity_scattering_vector_plot.q_norm',
                    internal_reference=True,
                ),
                validate_path=False,
            )
            hdf5_handler.add_attribute(
                path=f'{prefix}/intensity_scattering_vector_plot',
                params=dict(
                    axes='q_norm',
                    signal='intensity',
                    NX_class='NXdata',
                ),
            )
        elif q_parallel is not None and q_perpendicular is not None:
            # q_vectors lead to irregular grid
            # generate a regular grid using interpolation
            x = q_parallel.to('1/angstrom').magnitude.flatten()
            y = q_perpendicular.to('1/angstrom').magnitude.flatten()
            x_regular = np.linspace(x.min(), x.max(), intensity.shape[0])
            y_regular = np.linspace(y.min(), y.max(), intensity.shape[1])
            x_grid, y_grid = np.meshgrid(x_regular, y_regular)
            z_interpolated = griddata(
                points=(x, y),
                values=intensity.flatten(),
                xi=(x_grid, y_grid),
                method='linear',
                fill_value=intensity.min(),
            )
            hdf5_handler.add_dataset(
                path=f'{prefix}/intensity_scattering_vector_plot/q_parallel',
                dataset=Dataset(
                    data=x_regular,
                    archive_path='data.results[0].intensity_scattering_vector_plot.q_parallel',
                ),
                validate_path=False,
            )
            hdf5_handler.add_dataset(
                path=f'{prefix}/intensity_scattering_vector_plot/q_perpendicular',
                dataset=Dataset(
                    data=y_regular,
                    archive_path='data.results[0].intensity_scattering_vector_plot.q_perpendicular',
                ),
                validate_path=False,
            )
            hdf5_handler.add_dataset(
                path=f'{prefix}/intensity_scattering_vector_plot/intensity',
                dataset=Dataset(
                    data=z_interpolated,
                    archive_path='data.results[0].intensity_scattering_vector_plot.intensity',
                ),
                validate_path=False,
            )
            hdf5_handler.add_attribute(
                path=f'{prefix}/intensity_scattering_vector_plot',
                params=dict(
                    axes=['q_perpendicular', 'q_parallel'],
                    signal='intensity',
                    NX_class='NXdata',
                ),
            )


class XRDResult(MeasurementResult):
    """
    Section containing the result of an X-ray diffraction scan.
    """

    m_def = Section()

    array_index = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        description=(
            'A placeholder for the indices of vectorial quantities. '
            'Used as x-axis for plots within quantities.'
        ),
        a_display={'visible': False},
    )
    intensity = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        unit='dimensionless',
        description='The count at each 2-theta value, dimensionless',
        a_plot={'x': 'array_index', 'y': 'intensity'},
    )
    two_theta = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        unit='deg',
        description='The 2-theta range of the diffractogram',
        a_plot={'x': 'array_index', 'y': 'two_theta'},
    )
    q_norm = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        unit='meter**(-1)',
        description='The norm of scattering vector *Q* of the diffractogram',
        a_plot={'x': 'array_index', 'y': 'q_norm'},
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

    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                visible=Filter(
                    exclude=['array_index'],
                ),
            ),
        )
    )

    def generate_plots(self):
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
                'text': '<i>Intensity</i> over 2<i>θ</i> (linear scale)',
                'x': 0.5,
                'xanchor': 'center',
            },
            xaxis_title='2<i>θ</i> (°)',
            yaxis_title='<i>Intensity</i>',
            xaxis=dict(
                fixedrange=False,
            ),
            yaxis=dict(
                fixedrange=False,
            ),
            template='plotly_white',
            hovermode='closest',
            hoverlabel=dict(
                bgcolor='white',
            ),
            dragmode='zoom',
            width=600,
            height=600,
        )
        fig_line_linear.update_traces(
            hovertemplate='<i>Intensity</i>: %{y:.2f}<br>2<i>θ</i>: %{x}°',
        )
        plot_json = fig_line_linear.to_plotly_json()
        plot_json['config'] = dict(
            scrollZoom=False,
        )
        plots.append(
            PlotlyFigure(
                label='Intensity over 2θ (linear scale)',
                index=1,
                figure=plot_json,
            )
        )

        fig_line_log = px.line(
            x=x,
            y=y,
            log_y=True,
        )
        fig_line_log.update_layout(
            title={
                'text': '<i>Intensity</i> over 2<i>θ</i> (log scale)',
                'x': 0.5,
                'xanchor': 'center',
            },
            xaxis_title='2<i>θ</i> (°)',
            yaxis_title='<i>Intensity</i>',
            xaxis=dict(
                fixedrange=False,
            ),
            yaxis=dict(
                fixedrange=False,
            ),
            template='plotly_white',
            hovermode='closest',
            hoverlabel=dict(
                bgcolor='white',
            ),
            dragmode='zoom',
            width=600,
            height=600,
        )
        fig_line_log.update_traces(
            hovertemplate='<i>Intensity</i>: %{y:.2f}<br>2<i>θ</i>: %{x}°',
        )
        plot_json = fig_line_log.to_plotly_json()
        plot_json['config'] = dict(
            scrollZoom=False,
        )
        plots.append(
            PlotlyFigure(
                label='Intensity over 2θ (log scale)',
                index=0,
                figure=plot_json,
            )
        )

        if self.q_norm is None:
            return plots

        x = self.q_norm.to('1/angstrom').magnitude
        fig_line_log = px.line(
            x=x,
            y=y,
            log_y=True,
        )
        fig_line_log.update_layout(
            title={
                'text': '<i>Intensity</i> over |<em>q</em>| (log scale)',
                'x': 0.5,
                'xanchor': 'center',
            },
            xaxis_title='|<em>q</em>| (Å<sup>-1</sup>)',
            yaxis_title='<i>Intensity</i>',
            xaxis=dict(
                fixedrange=False,
            ),
            yaxis=dict(
                fixedrange=False,
            ),
            template='plotly_white',
            hovermode='closest',
            hoverlabel=dict(
                bgcolor='white',
            ),
            dragmode='zoom',
            width=600,
            height=600,
        )
        fig_line_log.update_traces(
            hovertemplate=(
                '<i>Intensity</i>: %{y:.2f}<br>|<em>q</em>|: %{x} Å<sup>-1</sup>'
            ),
        )
        plot_json = fig_line_log.to_plotly_json()
        plot_json['config'] = dict(
            scrollZoom=False,
        )
        plots.append(
            PlotlyFigure(
                label='Intensity over q_norm (log scale)',
                index=2,
                figure=plot_json,
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

    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                visible=Filter(
                    exclude=['array_index'],
                ),
            ),
        )
    )
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

    def generate_plots(self):
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
                'title': 'log<sub>10</sub> <i>Intensity</i>',
                'ticks': 'outside',
                'tickformat': '5',
            },
        )
        fig_2theta_omega.update_layout(
            title={
                'text': 'Reciprocal Space Map over 2<i>θ</i>-<i>ω</i>',
                'x': 0.5,
                'xanchor': 'center',
            },
            xaxis_title='<i>ω</i> (°)',
            yaxis_title='2<i>θ</i> (°)',
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
            hovermode='closest',
            hoverlabel=dict(
                bgcolor='white',
            ),
            dragmode='zoom',
            width=600,
            height=600,
        )
        fig_2theta_omega.update_traces(
            hovertemplate=(
                '<i>Intensity</i>: 10<sup>%{z:.2f}</sup><br>'
                '2<i>θ</i>: %{y}°<br>'
                '<i>ω</i>: %{x}°'
                '<extra></extra>'
            )
        )
        plot_json = fig_2theta_omega.to_plotly_json()
        plot_json['config'] = dict(
            scrollZoom=False,
        )
        plots.append(
            PlotlyFigure(
                label='RSM 2θ-ω',
                index=1,
                figure=plot_json,
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
                    'title': 'log<sub>10</sub> <i>Intensity</i>',
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
                xaxis_title='<i>q</i><sub>&#x2016;</sub> (Å<sup>-1</sup>)',  # q ‖
                yaxis_title='<i>q</i><sub>&#x22A5;</sub> (Å<sup>-1</sup>)',  # q ⊥
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
                hovermode='closest',
                hoverlabel=dict(
                    bgcolor='white',
                ),
                dragmode='zoom',
                width=600,
                height=600,
            )
            fig_q_vector.update_traces(
                hovertemplate=(
                    '<i>Intensity</i>: 10<sup>%{z:.2f}</sup><br>'
                    '<i>q</i><sub>&#x22A5;</sub>: %{y} Å<sup>-1</sup><br>'
                    '<i>q</i><sub>&#x2016;</sub>: %{x} Å<sup>-1</sup>'
                    '<extra></extra>'
                )
            )
            plot_json = fig_q_vector.to_plotly_json()
            plot_json['config'] = dict(
                scrollZoom=False,
            )
            plots.append(
                PlotlyFigure(
                    label='RSM Q-vectors',
                    index=0,
                    figure=plot_json,
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
                    self.q_parallel, self.q_perpendicular = calculate_q_vectors_rsm(
                        wavelength=self.source_peak_wavelength,
                        two_theta=self.two_theta * np.ones_like(self.intensity),
                        omega=self[var_axis],
                    )
                    break


class XRDResult1DHDF5(XRDResult):
    """
    Section containing the result of a 1D X-ray diffraction scan.
    """

    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                visible=Filter(
                    exclude=['array_index'],
                ),
            ),
        )
    )
    intensity = Quantity(
        type=HDF5Reference,
        description='The count at each 2-theta value, dimensionless',
        shape=[],
    )
    two_theta = Quantity(
        type=HDF5Reference,
        description='The 2-theta range of the diffractogram',
        shape=[],
    )
    q_norm = Quantity(
        type=HDF5Reference,
        description='The norm of scattering vector *Q* of the diffractogram',
        shape=[],
    )
    omega = Quantity(
        type=HDF5Reference,
        description='The omega range of the diffractogram',
        shape=[],
    )
    phi = Quantity(
        type=HDF5Reference,
        description='The phi range of the diffractogram',
        shape=[],
    )
    chi = Quantity(
        type=HDF5Reference,
        description='The chi range of the diffractogram',
        shape=[],
    )
    integration_time = Quantity(
        type=HDF5Reference,
        description='Integration time per channel',
        shape=[],
    )
    intensity_plot: IntensityPlot = SubSection(section_def=IntensityPlot)
    intensity_scattering_vector_plot: IntensityScatteringVectorPlot = SubSection(
        section_def=IntensityScatteringVectorPlot
    )

    def generate_plots(self, hdf5_handler: HDF5Handler):
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

        two_theta = hdf5_handler.read_dataset(path='entry/experiment_result/two_theta')
        intensity = hdf5_handler.read_dataset(path='entry/experiment_result/intensity')
        if two_theta is None or intensity is None:
            return plots

        x = two_theta.to('degree').magnitude
        y = intensity.magnitude
        fig_line_linear = px.line(
            x=x,
            y=y,
        )
        fig_line_linear.update_layout(
            title={
                'text': '<i>Intensity</i> over 2<i>θ</i> (linear scale)',
                'x': 0.5,
                'xanchor': 'center',
            },
            xaxis_title='2<i>θ</i> (°)',
            yaxis_title='<i>Intensity</i>',
            xaxis=dict(
                fixedrange=False,
            ),
            yaxis=dict(
                fixedrange=False,
            ),
            template='plotly_white',
            hovermode='closest',
            hoverlabel=dict(
                bgcolor='white',
            ),
            dragmode='zoom',
            width=600,
            height=600,
        )
        fig_line_linear.update_traces(
            hovertemplate='<i>Intensity</i>: %{y:.2f}<br>2<i>θ</i>: %{x}°',
        )
        plot_json = fig_line_linear.to_plotly_json()
        plot_json['config'] = dict(
            scrollZoom=False,
        )
        plots.append(
            PlotlyFigure(
                label='Intensity over 2θ (linear scale)',
                index=1,
                figure=plot_json,
            )
        )

        fig_line_log = px.line(
            x=x,
            y=y,
            log_y=True,
        )
        fig_line_log.update_layout(
            title={
                'text': '<i>Intensity</i> over 2<i>θ</i> (log scale)',
                'x': 0.5,
                'xanchor': 'center',
            },
            xaxis_title='2<i>θ</i> (°)',
            yaxis_title='<i>Intensity</i>',
            xaxis=dict(
                fixedrange=False,
            ),
            yaxis=dict(
                fixedrange=False,
            ),
            template='plotly_white',
            hovermode='closest',
            hoverlabel=dict(
                bgcolor='white',
            ),
            dragmode='zoom',
            width=600,
            height=600,
        )
        fig_line_log.update_traces(
            hovertemplate='<i>Intensity</i>: %{y:.2f}<br>2<i>θ</i>: %{x}°',
        )
        plot_json = fig_line_log.to_plotly_json()
        plot_json['config'] = dict(
            scrollZoom=False,
        )
        plots.append(
            PlotlyFigure(
                label='Intensity over 2θ (log scale)',
                index=0,
                figure=plot_json,
            )
        )

        q_norm = hdf5_handler.read_dataset(path='entry/experiment_result/q_norm')
        if q_norm is None:
            return plots

        x = q_norm.to('1/angstrom').magnitude
        fig_line_log = px.line(
            x=x,
            y=y,
            log_y=True,
        )
        fig_line_log.update_layout(
            title={
                'text': '<i>Intensity</i> over |<em>q</em>| (log scale)',
                'x': 0.5,
                'xanchor': 'center',
            },
            xaxis_title='|<em>q</em>| (Å<sup>-1</sup>)',
            yaxis_title='<i>Intensity</i>',
            xaxis=dict(
                fixedrange=False,
            ),
            yaxis=dict(
                fixedrange=False,
            ),
            template='plotly_white',
            hovermode='closest',
            hoverlabel=dict(
                bgcolor='white',
            ),
            dragmode='zoom',
            width=600,
            height=600,
        )
        fig_line_log.update_traces(
            hovertemplate=(
                '<i>Intensity</i>: %{y:.2f}<br>|<em>q</em>|: %{x} Å<sup>-1</sup>'
            ),
        )
        plot_json = fig_line_log.to_plotly_json()
        plot_json['config'] = dict(
            scrollZoom=False,
        )
        plots.append(
            PlotlyFigure(
                label='Intensity over q_norm (log scale)',
                index=2,
                figure=plot_json,
            )
        )

        return plots

    def calculate_scattering_vectors(self, hdf5_handler: HDF5Handler):
        """
        Calculate the scattering vector norm and add to the HDF5 handler.

        Args:
            hdf5_handler (HDF5Handler): A handler for the HDF5 file.
        """
        if hdf5_handler is None:
            return
        intensity = hdf5_handler.read_dataset(
            path='/ENTRY[entry]/experiment_result/intensity'
        )
        two_theta = hdf5_handler.read_dataset(
            path='/ENTRY[entry]/experiment_result/two_theta'
        )
        if intensity is None or two_theta is None:
            return

        if self.source_peak_wavelength is not None:
            q_norm = hdf5_handler.read_dataset(
                path='/ENTRY[entry]/experiment_result/q_norm'
            )
            q_norm, two_theta = calculate_two_theta_or_q(
                wavelength=self.source_peak_wavelength,
                two_theta=two_theta,
                q=q_norm,
            )
            hdf5_handler.add_dataset(
                path='/ENTRY[entry]/experiment_result/q_norm',
                dataset=Dataset(
                    data=q_norm,
                    archive_path='data.results[0].q_norm',
                ),
            )
            hdf5_handler.add_dataset(
                path='/ENTRY[entry]/experiment_result/two_theta',
                dataset=Dataset(
                    data=two_theta,
                    archive_path='data.results[0].two_theta',
                ),
            )

    def generate_hdf5_plots(self, hdf5_handler: HDF5Handler):
        """
        Initializes sections to generate the plots for intensity over position and
        scattering vectors.

        Args:
            hdf5_handler (HDF5Handler): The handler for the HDF5 file.
        """
        if hdf5_handler is None:
            return
        self.m_setdefault('intensity_plot')
        self.intensity_plot.generate_hdf5_plots(hdf5_handler)

        if self.source_peak_wavelength is not None:
            self.m_setdefault('intensity_scattering_vector_plot')
            self.intensity_scattering_vector_plot.generate_hdf5_plots(hdf5_handler)

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


class XRDResultRSMHDF5(XRDResult):
    """
    Section containing the result of a Reciprocal Space Map (RSM) scan.
    """

    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                visible=Filter(
                    exclude=['array_index'],
                ),
            ),
        )
    )
    intensity = Quantity(
        type=HDF5Reference,
        description='The count at each 2-theta value, dimensionless',
        shape=[],
    )
    two_theta = Quantity(
        type=HDF5Reference,
        description='The 2-theta range of the diffractogram',
        shape=[],
    )
    q_norm = Quantity(
        type=HDF5Reference,
        description='The norm of scattering vector *Q* of the diffractogram',
        shape=[],
    )
    omega = Quantity(
        type=HDF5Reference,
        description='The omega range of the diffractogram',
        shape=[],
    )
    phi = Quantity(
        type=HDF5Reference,
        description='The phi range of the diffractogram',
        shape=[],
    )
    chi = Quantity(
        type=HDF5Reference,
        description='The chi range of the diffractogram',
        shape=[],
    )
    integration_time = Quantity(
        type=HDF5Reference,
        description='Integration time per channel',
        shape=[],
    )
    q_parallel = Quantity(
        type=HDF5Reference,
        description='The scattering vector *Q_parallel* of the diffractogram',
    )
    q_perpendicular = Quantity(
        type=HDF5Reference,
        description='The scattering vector *Q_perpendicular* of the diffractogram',
    )
    intensity_plot: IntensityPlot = SubSection(section_def=IntensityPlot)
    intensity_scattering_vector_plot: IntensityScatteringVectorPlot = SubSection(
        section_def=IntensityScatteringVectorPlot
    )

    def generate_plots(self, hdf5_handler: HDF5Handler):
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

        two_theta = hdf5_handler.read_dataset(path='entry/experiment_result/two_theta')
        intensity = hdf5_handler.read_dataset(path='entry/experiment_result/intensity')
        omega = hdf5_handler.read_dataset(path='entry/experiment_result/omega')
        if two_theta is None or intensity is None or omega is None:
            return plots

        # Plot for 2theta-omega RSM
        # Zero values in intensity become -inf in log scale and are not plotted
        x = omega.to('degree').magnitude
        y = two_theta.to('degree').magnitude
        z = intensity.magnitude
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
                'title': 'log<sub>10</sub> <i>Intensity</i>',
                'ticks': 'outside',
                'tickformat': '5',
            },
        )
        fig_2theta_omega.update_layout(
            title={
                'text': 'Reciprocal Space Map over 2<i>θ</i>-<i>ω</i>',
                'x': 0.5,
                'xanchor': 'center',
            },
            xaxis_title='<i>ω</i> (°)',
            yaxis_title='2<i>θ</i> (°)',
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
            hovermode='closest',
            hoverlabel=dict(
                bgcolor='white',
            ),
            dragmode='zoom',
            width=600,
            height=600,
        )
        fig_2theta_omega.update_traces(
            hovertemplate=(
                '<i>Intensity</i>: 10<sup>%{z:.2f}</sup><br>'
                '2<i>θ</i>: %{y}°<br>'
                '<i>ω</i>: %{x}°'
                '<extra></extra>'
            )
        )
        plot_json = fig_2theta_omega.to_plotly_json()
        plot_json['config'] = dict(
            scrollZoom=False,
        )
        plots.append(
            PlotlyFigure(
                label='RSM 2θ-ω',
                index=1,
                figure=plot_json,
            ),
        )

        # Plot for RSM in Q-vectors
        q_parallel = hdf5_handler.read_dataset(
            path='entry/experiment_result/q_parallel',
        )
        q_perpendicular = hdf5_handler.read_dataset(
            path='entry/experiment_result/q_perpendicular',
        )
        if q_parallel is not None and q_perpendicular is not None:
            x = q_parallel.to('1/angstrom').magnitude.flatten()
            y = q_perpendicular.to('1/angstrom').magnitude.flatten()
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
                    'title': 'log<sub>10</sub> <i>Intensity</i>',
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
                xaxis_title='<i>q</i><sub>&#x2016;</sub> (Å<sup>-1</sup>)',  # q ‖
                yaxis_title='<i>q</i><sub>&#x22A5;</sub> (Å<sup>-1</sup>)',  # q ⊥
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
                hovermode='closest',
                hoverlabel=dict(
                    bgcolor='white',
                ),
                dragmode='zoom',
                width=600,
                height=600,
            )
            fig_q_vector.update_traces(
                hovertemplate=(
                    '<i>Intensity</i>: 10<sup>%{z:.2f}</sup><br>'
                    '<i>q</i><sub>&#x22A5;</sub>: %{y} Å<sup>-1</sup><br>'
                    '<i>q</i><sub>&#x2016;</sub>: %{x} Å<sup>-1</sup>'
                    '<extra></extra>'
                )
            )
            plot_json = fig_q_vector.to_plotly_json()
            plot_json['config'] = dict(
                scrollZoom=False,
            )
            plots.append(
                PlotlyFigure(
                    label='RSM Q-vectors',
                    index=0,
                    figure=plot_json,
                ),
            )

        return plots

    def calculate_scattering_vectors(self, hdf5_handler: HDF5Handler):
        """
        Calculate the scattering vectors for the RSM scan and add to the HDF5Handler.

        Args:
            hdf5_handler (HDF5Handler): The handler for the HDF5 file.
        """
        if hdf5_handler is None:
            return
        intensity = hdf5_handler.read_dataset(
            path='/ENTRY[entry]/experiment_result/intensity'
        )
        two_theta = hdf5_handler.read_dataset(
            path='/ENTRY[entry]/experiment_result/two_theta'
        )
        var_axis = None
        for axis in ['omega', 'chi', 'phi']:
            axis_value = hdf5_handler.read_dataset(
                path=f'/ENTRY[entry]/experiment_result/{axis}'
            )
            if axis_value is not None and len(np.unique(axis_value.magnitude)) > 1:
                var_axis = axis
                break
        if intensity is None or two_theta is None or var_axis is None:
            return

        if self.source_peak_wavelength is not None:
            q_parallel, q_perpendicular = calculate_q_vectors_rsm(
                wavelength=self.source_peak_wavelength,
                two_theta=two_theta * np.ones_like(intensity),
                omega=hdf5_handler.read_dataset(
                    path=f'/ENTRY[entry]/experiment_result/{var_axis}'
                ),
            )
            hdf5_handler.add_dataset(
                path='/ENTRY[entry]/experiment_result/q_parallel',
                dataset=Dataset(
                    data=q_parallel,
                    archive_path='data.results[0].q_parallel',
                ),
            )
            hdf5_handler.add_dataset(
                path='/ENTRY[entry]/experiment_result/q_perpendicular',
                dataset=Dataset(
                    data=q_perpendicular,
                    archive_path='data.results[0].q_perpendicular',
                ),
            )

    def generate_hdf5_plots(self, hdf5_handler: HDF5Handler):
        """
        Initializes sections to generate the plots for intensity over position and
        scattering vectors.

        Args:
            hdf5_handler (HDF5Handler): The handler for the HDF5 file.
        """
        if hdf5_handler is None:
            return
        self.m_setdefault('intensity_plot')
        self.intensity_plot.generate_hdf5_plots(hdf5_handler)
        if self.source_peak_wavelength is not None:
            self.m_setdefault('intensity_scattering_vector_plot')
            self.intensity_scattering_vector_plot.generate_hdf5_plots(hdf5_handler)

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger'):
        super().normalize(archive, logger)

        if self.name is None:
            self.name = 'RSM Scan Result'


class XRayDiffraction(Measurement):
    """
    Generic X-ray diffraction measurement.
    """

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
                'Reciprocal Space Mapping (RSM)',
            ]
        ),
        description="""
        The diffraction method used to obtain the diffraction pattern.
        | X-ray Diffraction Method                                   | Description                                                                                                                                                                                                 |
        |------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
        | **Powder X-ray Diffraction (PXRD)**                        | The term "powder" refers more to the random orientation of small crystallites than to the physical form of the sample. Can be used with non-powder samples if they present random crystallite orientations. |
        | **Single Crystal X-ray Diffraction (SCXRD)**               | Used for determining the atomic structure of a single crystal.                                                                                                                                              |
        | **High-Resolution X-ray Diffraction (HRXRD)**              | A technique typically used for detailed characterization of epitaxial thin films using precise diffraction measurements.                                                                                    |
        | **Small-Angle X-ray Scattering (SAXS)**                    | Used for studying nanostructures in the size range of 1-100 nm. Provides information on particle size, shape, and distribution.                                                                             |
        | **X-ray Reflectivity (XRR)**                               | Used to study thin film layers, interfaces, and multilayers. Provides info on film thickness, density, and roughness.                                                                                       |
        | **Grazing Incidence X-ray Diffraction (GIXRD)**            | Primarily used for the analysis of thin films with the incident beam at a fixed shallow angle.                                                                                                              |
        | **Reciprocal Space Mapping (RSM)**                         | High-resolution XRD method to measure diffracted intensity in a 2-dimensional region of reciprocal space. Provides information about the real-structure (lattice mismatch, domain structure, stress and defects) in single-crystalline and epitaxial samples.|
        """,  # noqa: E501
    )
    results = Measurement.results.m_copy()
    results.section_def = XRDResult
    hdf5_handler: HDF5Handler = None

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger'):  # noqa: PLR0912
        """
        The normalize function of the `XRayDiffraction` section.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
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
        if not archive.results.method:
            archive.results.method = Method(
                method_name='XRD',
                measurement=MeasurementMethod(
                    xrd=XRDMethod(diffraction_method_name=self.diffraction_method_name)
                ),
            )

        if not archive.results.properties.structural:
            diffraction_patterns = []
            for result in self.results:
                if self.hdf5_handler and isinstance(
                    result, XRDResult1DHDF5 | XRDResultRSMHDF5
                ):
                    intensity = self.hdf5_handler.read_dataset(
                        '/ENTRY[entry]/experiment_result/intensity'
                    )
                    two_theta = self.hdf5_handler.read_dataset(
                        '/ENTRY[entry]/experiment_result/two_theta'
                    )
                    q_norm = self.hdf5_handler.read_dataset(
                        '/ENTRY[entry]/experiment_result/q_norm'
                    )
                elif isinstance(result, XRDResult1D | XRDResultRSM):
                    intensity = result.intensity
                    two_theta = result.two_theta
                    q_norm = result.q_norm
                else:
                    intensity = two_theta = q_norm = None

                if intensity is not None and len(intensity.shape) == 1:
                    diffraction_patterns.append(
                        DiffractionPattern(
                            incident_beam_wavelength=result.source_peak_wavelength,
                            two_theta_angles=two_theta,
                            intensity=intensity,
                            q_vector=q_norm,
                        )
                    )
            archive.results.properties.structural = StructuralProperties(
                diffraction_pattern=diffraction_patterns
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
            properties=SectionProperties(
                order=[
                    'name',
                    'datetime',
                    'data_file',
                    'diffraction_method_name',
                    'lab_id',
                    'location',
                    'auxiliary_file',
                    'nexus_view',
                    'overwrite_auxiliary_file',
                    'description',
                ]
            ),
        ),
        a_template={
            'measurement_identifiers': {},
        },
        a_h5web=H5WebAnnotation(
            paths=[
                'results/0/intensity_plot',
                'results/0/intensity_scattering_vector_plot',
            ]
        ),
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
    auxiliary_file = Quantity(
        type=str,
        description='Auxiliary file (like .h5 or .nxs) containing the entry data.',
        a_browser=BrowserAnnotation(adaptor='RawFileAdaptor'),
    )
    nexus_view = Quantity(
        type=ArchiveSection,
        description='Reference to the NeXus entry.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.ReferenceEditQuantity),
    )
    trigger_switch_results_section = Quantity(
        type=bool,
        description="""
        Switches the results section. If it is a non-HDF5 section, it will be converted
        to HDF5 section (which uses NeXus file in the backend) and vice versa.
        If the results contains large datasets and the entry takes longer to process,
        it is recommended to use the HDF5 section.
        """,
        a_eln=dict(component='ActionEditQuantity', label='Switch To/From HDF5 Results'),
    )
    trigger_update_nexus_file = Quantity(
        type=bool,
        description="""
        Updates the nexus file with the current ELN state when using HDF5 results
        section.
        """,
        a_eln=dict(component='ActionEditQuantity', label='Update NeXus File'),
    )

    def get_read_write_functions(self) -> tuple[Callable, Callable]:
        """
        Method for getting the correct read and write functions for the current data
        file.
        Returns:
            tuple[Callable, Callable]: The read, write functions.
        """
        if self.data_file.endswith('.rasx'):
            return read_rigaku_rasx, self.write_xrd_data
        if self.data_file.endswith('.xrdml'):
            return read_panalytical_xrdml, self.write_xrd_data
        if self.data_file.endswith('.brml'):
            return read_bruker_brml, self.write_xrd_data
        return None, None

    def write_xrd_data(
        self,
        xrd_dict: dict[str, Any],
        archive: 'EntryArchive',
        logger: 'BoundLogger',
    ) -> None:
        """
        Write method for populating the `ELNXRayDiffraction` section from a dict.

        Args:
            xrd_dict (Dict[str, Any]): A dictionary with the XRD data.
            archive (EntryArchive): The archive containing the section.
            logger (BoundLogger): A structlog logger.
        """
        metadata_dict: dict = xrd_dict.get('metadata', {})
        source_dict: dict = metadata_dict.get('source', {})

        source = XRayTubeSource(
            xray_tube_material=source_dict.get('anode_material'),
            kalpha_one=source_dict.get('kAlpha1'),
            kalpha_two=source_dict.get('kAlpha2'),
            ratio_kalphatwo_kalphaone=source_dict.get('ratioKAlpha2KAlpha1'),
            kbeta=source_dict.get('kBeta'),
            xray_tube_voltage=source_dict.get('voltage'),
            xray_tube_current=source_dict.get('current'),
        )
        source.normalize(archive, logger)
        xrd_settings = XRDSettings(source=source)
        xrd_settings.normalize(archive, logger)

        samples = []
        if metadata_dict.get('sample_id') is not None:
            sample = CompositeSystemReference(
                lab_id=metadata_dict['sample_id'],
            )
            sample.normalize(archive, logger)
            samples.append(sample)

        xrd = ELNXRayDiffraction(
            results=[],
            xrd_settings=xrd_settings,
            samples=samples,
        )

        merge_sections(self, xrd, logger)

    def switch_results_section(self):
        """
        Switches the results section between HDF5 and non-HDF5 sections.
        """
        if isinstance(self.results[0], XRDResult1D):
            self.results = [XRDResult1DHDF5()]
            self.figures = []
            self.trigger_update_nexus_file = True
        elif isinstance(self.results[0], XRDResultRSM):
            self.results = [XRDResultRSMHDF5()]
            self.figures = []
            self.trigger_update_nexus_file = True
        elif isinstance(self.results[0], XRDResult1DHDF5):
            self.results = [XRDResult1D()]
            self.auxiliary_file = None
            self.nexus_view = None
        elif isinstance(self.results[0], XRDResultRSMHDF5):
            self.results = [XRDResultRSM()]
            self.auxiliary_file = None
            self.nexus_view = None

    def populate_measurement_results(
        self, xrd_dict: dict, archive: 'EntryArchive', logger: 'BoundLogger'
    ):
        """
        Populate the results section of the X-ray diffraction data. It performs the
        appropriate actions based on the type of results section (HDF5 or non-HDF5) and
        updates the results and figures accordingly.

        Args:
            xrd_dict (Dict): The XRD data dictionary.
            archive (EntryArchive): The archive containing the section.
            logger (BoundLogger): A structlog logger.
        """
        metadata_dict: dict = xrd_dict.get('metadata', {})

        result_dict = dict(
            scan_axis=metadata_dict.get('scan_axis'),
            intensity=xrd_dict.get('intensity'),
            two_theta=xrd_dict.get('2Theta'),
            omega=xrd_dict.get('Omega'),
            chi=xrd_dict.get('Chi'),
            phi=xrd_dict.get('Phi'),
            integration_time=xrd_dict.get('countTime'),
        )
        if (
            self.xrd_settings is not None
            and self.xrd_settings.source is not None
            and self.xrd_settings.source.kalpha_one is not None
        ):
            result_dict['source_peak_wavelength'] = self.xrd_settings.source.kalpha_one

        if isinstance(self.results[0], XRDResult1D | XRDResultRSM):
            for k, v in result_dict.items():
                if v is not None:
                    setattr(self.results[0], k, v)
            self.results[0].normalize(archive, logger)
            self.figures = self.results[0].generate_plots()
        elif (
            isinstance(self.results[0], XRDResult1DHDF5 | XRDResultRSMHDF5)
            and self.trigger_update_nexus_file
        ):
            filename = self.data_file.rsplit('.', 1)[0]
            self.auxiliary_file = (
                f'{filename}.h5'
                if archive.m_context.raw_path_exists(f'{filename}.h5')
                else f'{filename}.nxs'
            )
            self.hdf5_handler = HDF5Handler(
                filename=self.auxiliary_file,
                archive=archive,
                logger=logger,
            )
            if self.auxiliary_file.endswith('.nxs'):
                self.hdf5_handler.nexus_dataset_map = NEXUS_DATASET_MAP

            self.hdf5_handler.add_dataset(
                path='/ENTRY[entry]/experiment_result/intensity',
                dataset=Dataset(
                    data=xrd_dict.get('intensity'),
                    archive_path='data.results[0].intensity',
                ),
            )
            self.hdf5_handler.add_dataset(
                path='/ENTRY[entry]/experiment_result/two_theta',
                dataset=Dataset(
                    data=xrd_dict.get('2Theta'),
                    archive_path='data.results[0].two_theta',
                ),
            )
            self.hdf5_handler.add_dataset(
                path='/ENTRY[entry]/experiment_result/omega',
                dataset=Dataset(
                    data=xrd_dict.get('Omega'),
                    archive_path='data.results[0].omega',
                ),
            )
            self.hdf5_handler.add_dataset(
                path='/ENTRY[entry]/experiment_result/chi',
                dataset=Dataset(
                    data=xrd_dict.get('Chi'),
                    archive_path='data.results[0].chi',
                ),
            )
            self.hdf5_handler.add_dataset(
                path='/ENTRY[entry]/experiment_result/phi',
                dataset=Dataset(
                    data=xrd_dict.get('Phi'),
                    archive_path='data.results[0].phi',
                ),
            )
            self.hdf5_handler.add_dataset(
                path='/ENTRY[entry]/experiment_config/count_time',
                dataset=Dataset(
                    data=xrd_dict.get('countTime'),
                    archive_path='data.results[0].integration_time',
                ),
            )
            self.results[0].scan_axis = result_dict.get('scan_axis')
            self.results[0].source_peak_wavelength = result_dict.get(
                'source_peak_wavelength'
            )
            self.results[0].calculate_scattering_vectors(self.hdf5_handler)
            self.results[0].generate_hdf5_plots(self.hdf5_handler)
            self.results[0].normalize(archive, logger)

            self.hdf5_handler.write_file()

            if self.hdf5_handler.filename != self.auxiliary_file:
                self.auxiliary_file = self.hdf5_handler.filename
            self.nexus_view = None
            if self.auxiliary_file.endswith('.nxs'):
                nx_entry_id = get_entry_id_from_file_name(
                    archive=archive, file_name=self.auxiliary_file
                )
                self.nexus_view = get_reference(archive.metadata.upload_id, nx_entry_id)

        self.trigger_update_nexus_file = False

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger'):
        """
        The normalize function of the `ELNXRayDiffraction` section.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        if self.data_file is None:
            super().normalize(archive, logger)
            return

        read_function, write_function = self.get_read_write_functions()
        if read_function is None or write_function is None:
            logger.warn(f'No compatible reader found for the file: "{self.data_file}".')
            super().normalize(archive, logger)
            return
        with archive.m_context.raw_file(self.data_file) as file:
            xrd_dict = read_function(file.name, logger)
        write_function(xrd_dict, archive, logger)

        # set up results section
        if not self.results:
            scan_type = xrd_dict.get('metadata', {}).get('scan_type')
            if scan_type not in ['line', 'rsm']:
                logger.error(f'Scan type `{scan_type}` is not supported.')
                return
            if schema_config.use_hdf5_results and scan_type == 'line':
                self.results = [XRDResult1DHDF5()]
            elif not schema_config.use_hdf5_results and scan_type == 'line':
                self.results = [XRDResult1D()]
            elif schema_config.use_hdf5_results and scan_type == 'rsm':
                self.results = [XRDResultRSMHDF5()]
            elif not schema_config.use_hdf5_results and scan_type == 'rsm':
                self.results = [XRDResultRSM()]
            self.trigger_update_nexus_file = True
        elif self.trigger_switch_results_section:
            self.switch_results_section()
            self.trigger_switch_results_section = False

        # populate the measurement results section
        self.populate_measurement_results(xrd_dict, archive, logger)

        super().normalize(archive, logger)


class RawFileXRDData(EntryData):
    """
    Section for an XRD data file.
    """

    measurement = Quantity(
        type=ELNXRayDiffraction,
        a_eln=ELNAnnotation(
            component='ReferenceEditQuantity',
        ),
    )


m_package.__init_metainfo__()
