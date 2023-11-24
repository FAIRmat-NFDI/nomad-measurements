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

from nomad.metainfo.metainfo import (
    Category,
)
from nomad.datamodel.data import (
    EntryDataCategory,
)
from nomad.datamodel.metainfo.basesections import (
    SectionReference,
    Activity,
    Process,
    Measurement,
)
from structlog.stdlib import (
    BoundLogger,
)
from nomad.metainfo import (
    Quantity,
    SubSection,
)
from nomad.datamodel.metainfo.annotations import (
    ELNAnnotation,
    ELNComponentEnum,
)


class NOMADMeasurementsCategory(EntryDataCategory):
    '''
    A category for all measurements defined in the `nomad-measurements` plugin.
    '''
    m_def = Category(label='NOMAD Measurements', categories=[EntryDataCategory])


class ActivityReference(SectionReference):
    '''
    A section used for referencing an Activity.
    '''
    reference = Quantity(
        type=Activity,
        description='A reference to a NOMAD `Activity` entry.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.ReferenceEditQuantity,
            label='Activity Reference',
        ),
    )
    lab_id = Quantity(
        type=str,
        description='''
        The readable identifier for the activity.
        ''',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
        ),
    )

    def normalize(self, archive, logger: 'BoundLogger') -> None:
        '''
        The normalizer for the `EntityReference` class.
        Will attempt to fill the `reference` from the `lab_id` or vice versa.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger ('BoundLogger'): A structlog logger.
        '''
        super(ActivityReference, self).normalize(archive, logger)
        if self.reference is None and self.lab_id is not None:
            from nomad.search import search, MetadataPagination
            query = {
                'results.eln.lab_ids': self.lab_id
            }
            search_result = search(
                owner='all',
                query=query,
                pagination=MetadataPagination(page_size=1),
                user_id=archive.metadata.main_author.user_id)
            if search_result.pagination.total > 0:
                entry_id = search_result.data[0]["entry_id"]
                upload_id = search_result.data[0]["upload_id"]
                self.reference = f'../uploads/{upload_id}/archive/{entry_id}#data'
                if search_result.pagination.total > 1:
                    logger.warn(
                        f'Found {search_result.pagination.total} entries with lab_id: '
                        f'"{self.lab_id}". Will use the first one found.'
                    )
            else:
                logger.warn(
                    f'Found no entries with lab_id: "{self.lab_id}".'
                )
        elif self.lab_id is None and self.reference is not None:
            self.lab_id = self.reference.lab_id
        if self.name is None and self.lab_id is not None:
            self.name = self.lab_id


class ProcessReference(ActivityReference):
    '''
    A section used for referencing a Process.
    '''
    reference = Quantity(
        type=Process,
        description='A reference to a NOMAD `Process` entry.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.ReferenceEditQuantity,
            label='Process Reference',
        ),
    )


class InSituMeasurement(Measurement):
    '''
    A section used for a measurement performed in-situ during a process.
    '''
    process = SubSection(
        section_def=ProcessReference,
        description='A reference to the process during which the measurement occurred.',
    )