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

from nomad.datamodel.metainfo.basesections import (
    Measurement,
    MeasurementResult,
    CompositeSystemReference,
    ReadableIdentifiers,
    System
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
from nomad_measurements import (
    NOMADMeasurementsCategory,
)
from nomad_measurements.xrf import readers
from nomad_measurements.utils import merge_sections, get_bounding_range_2d

m_package = Package(name='nomad_xrf')

class XRFResult(MeasurementResult, System):
    """
    Section containing the result of an X-ray fluorescence measurement.
    """

    thickness = Quantity(
        type=np.dtype(np.float64),
        unit=('nm'),
        a_eln=dict(component='NumberEditQuantity', defaultDisplayUnit='nm'))


class XRayFluorescence(Measurement):
    '''
    Generic X-ray fluorescence measurement.
    '''
    m_def = Section()
    method = Quantity(type=str,default='X-Ray Fluorescence (XRF)')

    data_file = Quantity(
        type=str,
        description='Data file containing the xrf results',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.FileEditQuantity,
        ),
    )

    xrf_settings = SubSection(
        section_def = XRFSettings
    )

    results = Measurement.results.m_copy()
    results.section_def = XRFResult

    def get_read_function(self) -> Callable:
        """
        Method for getting the correct read function for the current data file.

        Returns:
            Callable: The read function.
        """
        if self.data_file.endswith('.txt'): # specify more!?
            return readers.read_UBIK_trn

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger'):
        '''
        The normalize function of the `XRayFluorescence` section.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        '''
        super().normalize(archive, logger)

        if self.data_file is not None:
            read_function = self.get_read_function()
            if read_function is None:
                logger.warn(
                    f'No compatible reader found for the file: "{self.data_file}".'
                )
            else:
                with archive.m_context.raw_file(self.data_file) as file:
                    xrf_dict = read_function(file.name, logger)
                    results = XRFResult(
                        thickness = xrf_dict.get('thickness', None)
                    )
                    self.results.thickness = xrf_dict.get('thickness', None)

class XRFSettings(ArchiveSection):
    '''
    Section containing the settings for an XRF measurement.
    '''

    xray_energy = Quantity(
        type=np.dtype(np.float64),
        unit=('eV'),
        a_eln=dict(component='NumberEditQuantity', defaultDisplayUnit='eV'))

    current = Quantity(
        type=np.dtype(np.float64),
        unit=('uA'),
        a_eln=dict(component='NumberEditQuantity', defaultDisplayUnit='uA'))

    spot_size = Quantity(
        type=np.dtype(np.float64),
        unit=('mm'),
        a_eln=dict(component='NumberEditQuantity', defaultDisplayUnit='mm'))

    integration_time = Quantity(
        type=np.dtype(np.float64),
        unit=('s'),
        a_eln=dict(component='NumberEditQuantity', defaultDisplayUnit='s'))

    element_line = Quantity(
        type=str,
        a_eln=dict(component='StringEditQuantity'))


m_package.__init_metainfo__()
