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

from time import perf_counter, sleep
from typing import (
    TYPE_CHECKING,
)

from nomad.datamodel import EntryArchive
from nomad.datamodel.data import (
    EntryData,
)
from nomad.datamodel.metainfo.annotations import (
    ELNAnnotation,
)
from nomad.metainfo import Quantity
from nomad.parsing import MatchingParser

from nomad_material_processing.utils import create_archive

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import (
        EntryArchive,
    )

from nomad.datamodel import EntryArchive
from nomad.datamodel.metainfo.basesections import (
    BaseSection,
)

from nomad_measurements.ppms.schema import PPMSMeasurement


class PPMSFile(EntryData):
    measurement = Quantity(
        type=PPMSMeasurement,
        a_eln=ELNAnnotation(
            component='ReferenceEditQuantity',
        ),
    )


class PPMSParser(MatchingParser):
    def set_entrydata_definition(self):
        """
        Set the entry data definition for the parser.

        In this way, the parser will be able to create the correct entry data object
        and the parser can be inherited and specialized to be able to fill specific
        data
        """
        self.ppms_measurement = PPMSMeasurement

    def parse(self, mainfile: str, archive: EntryArchive, logger) -> None:
        from nomad.search import search

        data_file = mainfile.split('/')[-1]
        data_file_with_path = mainfile.split('raw/')[-1]
        entry = self.ppms_measurement()
        entry.data_file = data_file_with_path
        file_name = f'{data_file[:-4]}.archive.json'
        # entry.normalize(archive, logger)
        tic = perf_counter()
        while True:
            search_result = search(
                owner='user',
                query={
                    'results.eln.sections:any': ['PPMSSequenceFile'],
                    'upload_id:any': [archive.m_context.upload_id],
                },
                user_id=archive.metadata.main_author.user_id,
            )
            if len(search_result.data) > 0:
                for sequence in search_result.data:
                    entry.sequence_file = sequence['search_quantities'][0]['str_value']
                    logger.info(sequence['search_quantities'][0]['str_value'])
                    break
            sleep(0.1)
            toc = perf_counter()
            if toc - tic > 15:  # noqa: PLR2004
                logger.warning(
                    "The Sequence File entry/ies in the current upload were\
                          not found and couldn't be referenced."
                )
                break
        archive.data = PPMSFile(measurement=create_archive(entry, archive, file_name))
        archive.metadata.entry_name = data_file + ' measurement file'


class PPMSSequenceFile(BaseSection, EntryData):
    file_path = Quantity(
        type=str,
        a_eln=dict(component='FileEditQuantity'),
        a_browser=dict(adaptor='RawFileAdaptor'),
    )
    entry_type = Quantity(
        type=str,
    )


class PPMSSequenceParser(MatchingParser):
    def set_entrydata_definition(self):
        """
        Set the entry data definition for the parser.

        In this way, the parser will be able to create the correct entry data object
        and the parser can be inherited and specialized to be able to fill specific
        sequences
        """
        self.ppms_sequence = PPMSSequenceFile

    def parse(self, mainfile: str, archive: EntryArchive, logger) -> None:
        data_file = mainfile.split('/')[-1]
        data_file_with_path = mainfile.split('raw/')[-1]
        archive.data = self.ppms_sequence(
            file_path=data_file_with_path, entry_type='PPMSSequenceFile'
        )
        archive.metadata.entry_name = data_file + ' sequence file'
