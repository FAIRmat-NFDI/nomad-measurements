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
import collections
import re
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Optional,
)

import h5py
import numpy as np
import pint
import plotly.express as px
from fairmat_readers_xrd import (
    read_bruker_brml,
    read_panalytical_xrdml,
    read_rigaku_rasx,
)
from nomad.datamodel.data import (
    ArchiveSection,
    EntryData,
)
from nomad.datamodel.hdf5 import (
    HDF5Reference,
)
from nomad.datamodel.metainfo.annotations import (
    ELNAnnotation,
    ELNComponentEnum,
)
from nomad.datamodel.metainfo.basesections import (
    CompositeSystemReference,
    Measurement,
    MeasurementResult,
    ReadableIdentifiers,
)
from nomad.datamodel.metainfo.plot import (
    PlotlyFigure,
    PlotSection,
)
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
    AttrDict,
    get_bounding_range_2d,
    get_data,
    merge_sections,
    set_data,
)
from nomad_measurements.xrd.nx import (
    CONCEPT_MAP,
    NEXUS_DATASET_PATHS,
    remove_nexus_annotations,
    walk_through_object,
)

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import (
        EntryArchive,
    )
    from structlog.stdlib import (
        BoundLogger,
    )


from nomad.config import config

configuration = config.get_plugin_entry_point('nomad_measurements.xrd:schema')

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
        two_theta = get_data(self, 'two_theta')
        intensity = get_data(self, 'intensity')
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
                '<i>Intensity</i>: %{y:.2f}<br>' '|<em>q</em>|: %{x} Å<sup>-1</sup>'
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
        q_norm = get_data(self, 'q_norm')
        two_theta = get_data(self, 'two_theta')
        if self.source_peak_wavelength is not None:
            q_norm, two_theta = calculate_two_theta_or_q(
                wavelength=self.source_peak_wavelength,
                two_theta=two_theta,
                q=q_norm,
            )
            set_data(self, q_norm=q_norm, two_theta=two_theta)


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
        two_theta = get_data(self, 'two_theta')
        intensity = get_data(self, 'intensity')
        omega = get_data(self, 'omega')
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
        if self.q_parallel is not None and self.q_perpendicular is not None:
            x = get_data(self, 'q_parallel').to('1/angstrom').magnitude.flatten()
            y = get_data(self, 'q_perpendicular').to('1/angstrom').magnitude.flatten()
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

        if self.source_peak_wavelength is not None:
            for var_axis in ['omega', 'chi', 'phi']:
                var_axis_value = get_data(self, var_axis)
                if (
                    var_axis_value is not None
                    and len(np.unique(var_axis_value.magnitude)) > 1
                ):
                    q_parallel, q_perpendicular = calculate_q_vectors_RSM(
                        wavelength=self.source_peak_wavelength,
                        two_theta=self.two_theta * np.ones_like(self.intensity),
                        omega=var_axis_value,
                    )
                    set_data(
                        self,
                        q_parallel=q_parallel,
                        q_perpendicular=q_perpendicular,
                    )
                    break


class XRDResult1D_HDF5(XRDResult1D):
    intensity = Quantity(
        type=HDF5Reference,
        description='The count at each 2-theta value, dimensionless',
    )
    two_theta = Quantity(
        type=HDF5Reference,
        description='The 2-theta range of the diffractogram',
    )
    q_norm = Quantity(
        type=HDF5Reference,
        description='The norm of scattering vector *Q* of the diffractogram',
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
    integration_time = Quantity(
        type=HDF5Reference,
        description='Integration time per channel',
    )


class XRDResultRSM_HDF5(XRDResultRSM):
    intensity = Quantity(
        type=HDF5Reference,
        description='The count at each 2-theta value, dimensionless',
    )
    two_theta = Quantity(
        type=HDF5Reference,
        description='The 2-theta range of the diffractogram',
    )
    q_norm = Quantity(
        type=HDF5Reference,
        description='The norm of scattering vector *Q* of the diffractogram',
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
    q_parallel = Quantity(
        type=HDF5Reference,
        description='The scattering vector *Q_parallel* of the diffractogram',
    )
    q_perpendicular = Quantity(
        type=HDF5Reference,
        description='The scattering vector *Q_perpendicular* of the diffractogram',
    )


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

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger'):
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
        if not archive.results.properties.structural:
            diffraction_patterns = []
            for result in self.results:
                intensity = get_data(result, 'intensity')
                if intensity is None or len(intensity) != 1:
                    diffraction_patterns.append(
                        DiffractionPattern(
                            incident_beam_wavelength=result.source_peak_wavelength,
                            two_theta_angles=get_data(result, 'two_theta'),
                            intensity=result.intensity,
                            q_vector=get_data(result, 'q_norm'),
                        )
                    )
            archive.results.properties.structural = StructuralProperties(
                diffraction_pattern=diffraction_patterns
            )
        if not archive.results.method:
            archive.results.method = Method(
                method_name='XRD',
                measurement=MeasurementMethod(
                    xrd=XRDMethod(diffraction_method_name=self.diffraction_method_name)
                ),
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
    auxiliary_file = Quantity(
        type=str,
        description='Auxiliary file (like .h5 or .nxs) containing the entry data.',
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

    hdf5_data_dict = collections.OrderedDict()
    hdf5_dataset_paths = []
    hdf5_references = dict()

    def populate_hdf5_data_dict(
        self,
        hdf5_path: str,
        archive_path: str,
        value: Any,
        logger: 'BoundLogger',
    ):
        """
        Populates the `hdf5_data_dict` with the given value. The `hdf5_path` is
        used to find a valid dataset path from `self.hdf5_dataset_paths`, and if it
        exists, the value is added to the corresponding path.

        Args:
            hdf5_path (str): The dataset path to be used in the HDF5 file.
            archive_path (str): The path of the quantity in the archive.
            value (Any): The value to be stored in the HDF5 file.
        """
        if not self.hdf5_dataset_paths:
            logger.warning(
                f'Unable to add "{hdf5_path}" to HDF5 file as no valid '
                'collection of dataset paths found.'
            )
            return

        # find the corresponding dataset for the given hdf5_path
        for dataset_path in self.hdf5_dataset_paths:
            if hdf5_path == dataset_path:
                if isinstance(value, pint.Quantity):
                    self.hdf5_data_dict[dataset_path] = value.magnitude
                    self.hdf5_data_dict[f'{dataset_path}/@units'] = str(value.units)
                else:
                    self.hdf5_data_dict[dataset_path] = value
            ref = (
                f'/uploads/{self.m_parent.m_context.upload_id}/raw'
                f'/{self.auxiliary_file}#{dataset_path}'
            )
            self.hdf5_references[archive_path] = ref
            return

        logger.warning(
            f'Unable to add "{hdf5_path}" to HDF5 file no compatible dataset '
            'path found.'
        )

    def prepare_hdf5_data(
        self,
        raw_data: 'AttrDict' = AttrDict(),
        archive: 'EntryArchive' = None,
        logger: 'BoundLogger' = None,
    ):
        """
        Prepares data for the HDF5 file. Based on the concept map, the data is extracted
        either from the `raw_data` or the `archive`.

        If the data extracted from the raw data is an array, the data is stored in the HDF5 file and the path to the data is
        overwritten in the `raw_data` (in-place modification). For example,
        {'intensity': array([1, 2, 3])} becomes
        {'intensity': '{file_path}{file_name}.h5#intensity'}
        and the array [1, 2, 3] is stored in the HDF5 file.

        Args:
            raw_data (AttrDict, optional): A dictionary with the raw data from
                the instrument.
            archive (EntryArchive, optional): A NOMAD archive.
            logger (BoundLogger, optional): A structlog logger.
        """
        concept_map = remove_nexus_annotations(CONCEPT_MAP)
        h5_data_dict = collections.defaultdict(lambda: None)
        h5_data_paths = collections.defaultdict(lambda: None)
        for h5_key, data_key in concept_map.items():
            if isinstance(data_key, dict):
                if h5_key == raw_data.get('metadata', {}).get('scan_type', ''):
                    h5_data_dict.update(
                        self.prepare_hdf5_data(data_key, archive, logger)
                    )
            else:
                data_source_type, data_source_path = data_key.split('.', maxsplit=1)
                if data_source_type == 'raw_data':
                    data_source = raw_data
                elif data_source_type == 'archive':
                    data_source = archive
                else:
                    continue

                value = walk_through_object(data_source, data_source_path)

                if value is not None:
                    h5_data_dict[h5_key] = value
                    if isinstance(value, np.ndarray) and data_source_type == 'raw_data':
                        # edit raw_data to contain the path to the data
                        if data_source_path.endswith('.magnitude'):
                            data_source_path = data_source_path.rsplit('.', 1)[0]
                        h5_data_paths[data_source_path] = (
                            f'/uploads/{archive.m_context.upload_id}/raw/'
                            f'{self.auxiliary_file}#{h5_key}'
                        )

        raw_data.update(h5_data_paths)

        return h5_data_dict

    def create_nx_file(self, archive: 'EntryArchive', logger: 'BoundLogger'):
        """
        Method for creating a NeXus file which contains the array data along with other
        archive data in a NeXus view.

        Args:
            archive (EntryArchive): The archive containing the section.
            logger (BoundLogger): A structlog logger.
        """
        raise NotImplementedError('Method `create_nx_file` is not implemented.')
        # TODO add archive data to `hdf5_data_dict` before creating the nexus file. Use
        # `populate_hdf5_data_dict` method for each quantity that is needed in .nxs
        # file. Create a NeXus file with the data in `hdf5_data_dict`.

    def create_hdf5_file(self, archive: 'EntryArchive', logger: 'BoundLogger'):
        """
        TODO make it independent of prepare_hdf5_data

        Args:
            archive (EntryArchive): The archive containing the section.
            logger (BoundLogger): A structlog logger.
        """

        # pivot from .nxs to .h5
        self.auxiliary_file = f'{self.data_file}.h5'
        for archive_path, hdf5_path in self.hdf5_references.items():
            self.hdf5_references[archive_path] = remove_nexus_annotations(hdf5_path)
        tmp_dict = {}
        for key, value in self.hdf5_data_dict.items():
            tmp_dict[remove_nexus_annotations(key)] = value
        self.hdf5_data_dict = tmp_dict

        # create the HDF5 file
        with archive.m_context.raw_file(self.auxiliary_file, 'w') as h5file:
            with h5py.File(h5file.name, 'w') as h5:
                for key, value in self.hdf5_data_dict.items():
                    if value is None:
                        continue

                    value_is_unit = False
                    if key.endswith('@units'):
                        value_is_unit = True
                        # remove the '@units' suffix
                        key = key.rsplit('/', 1)[0]

                    group_name, dataset_name = key.rsplit('/', 1)
                    group = h5.require_group(group_name)

                    if value_is_unit:
                        try:
                            h5[f'{group_name}/{dataset_name}'].attrs['units'] = str(
                                value
                            )
                        except KeyError:
                            logger.error(
                                f'Could not set units for "{group_name}/{dataset_name}"'
                                'as the dataset does not exist.'
                            )
                    else:
                        group.create_dataset(
                            dataset_name, data=value, compression='gzip'
                        )
                        # group.attrs['axes'] = 'time'
                        # group.attrs['signal'] = 'value'
                        # group.attrs['NX_class'] = 'NXdata'

    def create_auxiliary_file(
        self,
        archive: 'EntryArchive',
        logger: 'BoundLogger',
    ):
        """
        Method for creating an auxiliary file.

        Args:
            archive (EntryArchive): The archive containing the section.
            logger (BoundLogger): A structlog logger.
        """
        try:
            self.create_nx_file(archive, logger)
        except Exception:
            logger.warning('Error creating nexus file. Creating h5 file instead')
            self.create_hdf5_file(archive, logger)

        # add the references for the HDF5Reference quantities
        for archive_path, hdf5_path in self.hdf5_references.items():
            self.set_hdf5_reference(self, archive_path, hdf5_path)

    @staticmethod
    def set_hdf5_reference(section: 'Section', path: str, ref: str):
        """
        Method for setting the HDF5Reference of a quantity in a section. It can handle
        nested quantities and repeatable sections, provided that the quantity itself
        is of type `HDF5Reference`.
        For example, one can set the reference for a quantity path like
        `data.results[0].intensity`.

        Args:
            section (Section): The NOMAD section containing the quantity.
            path (str): The path to the quantity.
            ref (str): The reference to the HDF5 dataset.
        """
        attr = section
        path = path.split('.')
        quantity_name = path.pop()

        for subpath in path:
            if re.match(r'.*\[.*\]', subpath):
                index = int(subpath.split('[')[1].split(']')[0])
                attr = attr.m_get(subpath.split('[')[0], index=index)
            else:
                attr = attr.m_get(subpath)

        if isinstance(
            attr.m_get_quantity_definition(quantity_name).type, HDF5Reference
        ):
            attr.m_set(quantity_name, ref)

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

        scan_type = metadata_dict.get('scan_type', None)
        if scan_type not in ['line', 'rsm']:
            logger.error(f'Scan type `{scan_type}` is not supported.')
            return

        # Create a new result section
        results = []
        result = None
        if scan_type == 'line':
            result = XRDResult1D_HDF5()
        elif scan_type == 'rsm':
            result = XRDResultRSM_HDF5()

        if result is not None:
            result.scan_axis = metadata_dict.get('scan_axis', None)
            result.normalize(archive, logger)
            results.append(result)

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
        xrd_settings = XRDSettings(source=source)
        xrd_settings.normalize(archive, logger)

        samples = []
        if metadata_dict.get('sample_id', None) is not None:
            sample = CompositeSystemReference(
                lab_id=metadata_dict['sample_id'],
            )
            sample.normalize(archive, logger)
            samples.append(sample)

        xrd = ELNXRayDiffraction(
            results=results,
            xrd_settings=xrd_settings,
            samples=samples,
        )

        merge_sections(self, xrd, logger)

        self.populate_hdf5_data_dict(
            '/ENTRY[entry]/experiment_result/intensity',
            'results[0].intensity',
            xrd_dict.get('intensity', None),
            logger,
        )
        self.populate_hdf5_data_dict(
            '/ENTRY[entry]/experiment_result/two_theta',
            'results[0].two_theta',
            xrd_dict.get('2Theta', None),
            logger,
        )
        self.populate_hdf5_data_dict(
            '/ENTRY[entry]/experiment_result/omega',
            'results[0].omega',
            xrd_dict.get('Omega', None),
            logger,
        )
        self.populate_hdf5_data_dict(
            '/ENTRY[entry]/experiment_result/chi',
            'results[0].chi',
            xrd_dict.get('Chi', None),
            logger,
        )
        self.populate_hdf5_data_dict(
            '/ENTRY[entry]/experiment_result/phi',
            'results[0].phi',
            xrd_dict.get('Phi', None),
            logger,
        )
        self.populate_hdf5_data_dict(
            '/ENTRY[entry]/experiment_result/integration_time',
            'results[0].integration_time',
            xrd_dict.get('countTime', None),
            logger,
        )

    def backward_compatibility(self):
        """
        Method for backward compatibility.
        """
        # Migration to using HFD5References: removing exisiting results
        if self.results:
            self.results = []

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger'):
        """
        The normalize function of the `ELNXRayDiffraction` section.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        self.backward_compatibility()
        if self.data_file is not None:
            read_function, write_function = self.get_read_write_functions()
            if read_function is None or write_function is None:
                logger.warn(
                    f'No compatible reader found for the file: "{self.data_file}".'
                )
            else:
                with archive.m_context.raw_file(self.data_file) as file:
                    xrd_dict = read_function(file.name, logger)
                self.auxiliary_file = f'{self.data_file}.nxs'
                self.hdf5_dataset_paths = NEXUS_DATASET_PATHS
                write_function(xrd_dict, archive, logger)
                self.create_auxiliary_file(archive, logger)
        super().normalize(archive, logger)
        if not self.results:
            return

        self.figures = self.results[0].generate_plots(archive, logger)


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
