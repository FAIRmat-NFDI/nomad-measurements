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
import re
import os
import json

import numpy as np

from nomad.datamodel.metainfo.basesections import (
    Measurement,
    MeasurementResult,
    CompositeSystemReference,
    ReadableIdentifiers,
)
from nomad.datamodel.metainfo.eln import (
    NexusDataConverter
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

from nomad_measurements import NOMADMeasurementsCategory

from pynxtools.dataconverter.convert import convert  # pylint: disable=import-error


m_package = Package(name='nomad-measurements Transmission')


class Operator(ArchiveSection):
    name=Quantity(
        type=str,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
        ),
    )
    affiliation=Quantity(
        type=str,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
        ),
    )
    address=Quantity(
        type=str,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
        ),
    )
    email=Quantity(
        type=str,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
        ),
    )


class Transmission(Measurement):
    data_file = Quantity(
        type=str,
        description='Data file containing the transmission spectrum.',
        a_eln=dict(
            component='FileEditQuantity',
        ),
    )
    operator = SubSection(
        section_def=Operator,
    )

    def normalize(self, archive, logger: BoundLogger) -> None:
        super(Transmission, self).normalize(archive, logger)
        raw_path = archive.m_context.raw_path()
        eln_filename = '_transmission_eln_temp.json'
        pattern = re.compile(r'(?P<file_name>.*)\.archive\.json$')
        re_match = pattern.match(archive.metadata.mainfile)
        output = f'{re_match["file_name"]}.nxs'
        eln_dict = {}
        if self.operator:
            if self.operator.name:
                eln_dict['/ENTRY[entry]/operator/name'] = self.name
            if self.operator.affiliation:
                eln_dict['/ENTRY[entry]/operator/affiliation'] = self.operator.affiliation
            if self.operator.address:
                eln_dict['/ENTRY[entry]/operator/address'] = self.operator.address
            if self.operator.email:
                eln_dict['/ENTRY[entry]/operator/email'] = self.operator.email
        if len(self.samples) > 0:
            if self.samples[0].lab_id:
                eln_dict['/ENTRY[entry]/SAMPLE[sample]/name'] = self.samples[0].lab_id
            else:
                eln_dict['/ENTRY[entry]/SAMPLE[sample]/name'] = self.samples[0].name
        if self.lab_id:
            eln_dict['/ENTRY[entry]/experiment_identifier'] = self.lab_id
        with archive.m_context.raw_file(eln_filename, 'w') as eln_file:
            json.dump(eln_dict, eln_file)
        converter_params = {
            'reader': 'transmission',
            'nxdl': 'NXtransmission',
            'input_file': [
                os.path.join(raw_path, self.data_file),
                os.path.join(raw_path, eln_filename),
            ],
            'output': os.path.join(raw_path, output)
        }
        try:
            convert(**converter_params)
        except Exception as e:
            logger.warn('could not convert to nxs', mainfile=output, exc_info=e)
            raise e

        try:
            archive.m_context.process_updated_raw_file(output, allow_modify=True)
        except Exception as e:
            logger.error('could not trigger processing', mainfile=output, exc_info=e)
            raise e
        else:
            logger.info('triggered processing', mainfile=output)



class ELNTransmission(Transmission, EntryData):
    m_def = Section(
        categories=[NOMADMeasurementsCategory],
        label='UV/Vis Transmission',
        a_eln=dict(
            lane_width='800px',
        ),
        a_template=dict(
            measurement_identifiers=dict(),
        ),
        a_plot=[],
    )
    measurement_identifiers = SubSection(
        section_def=ReadableIdentifiers,
    )
