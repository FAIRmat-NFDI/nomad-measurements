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

from nomad.datamodel import EntryArchive
from nomad.metainfo import (
    Quantity,
)
from nomad.parsing import MatchingParser
from nomad.datamodel.metainfo.annotations import (
    ELNAnnotation,
)
from nomad.datamodel.data import (
    EntryData,
)

from nomad_measurements.utils import create_archive
from nomad_measurements.xrd import ELNXRayDiffraction


class XRDDataFile(EntryData):
    '''
    Section for a XRD data file.
    '''
    measurement = Quantity(
        type=ELNXRayDiffraction,
        a_eln=ELNAnnotation(
            component='ReferenceEditQuantity',
        )
    )


class XRDParser(MatchingParser):
    '''
    Parser for matching XRD files and creating instances of ELNXRayDiffraction
    '''
    def __init__(self):
        super().__init__(
            code_name='XRD Parser',
        )

    def parse(
            self, mainfile: str, archive: EntryArchive, logger=None, child_archives=None
        ) -> None:
        data_file = mainfile.split('/')[-1]
        entry = ELNXRayDiffraction.m_from_dict(ELNXRayDiffraction.m_def.a_template)
        entry.data_file = data_file
        file_name = f'{data_file[:-6]}.archive.json'
        archive.data = XRDDataFile(measurement=create_archive(entry,archive,file_name))
        archive.metadata.entry_name = data_file[:-6] + ' data file'
