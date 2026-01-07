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
from typing import TYPE_CHECKING

from nomad.datamodel.context import ServerContext
from nomad.parsing import MatchingParser

from nomad_measurements.utils import create_archive
from nomad_measurements.xrd.schema import (
    ELNXRayDiffraction,
    RawFileXRDData,
)

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import (
        EntryArchive,
    )


class XRDParser(MatchingParser):
    """
    Parser for matching XRD files and creating instances of ELNXRayDiffraction
    """

    def is_mainfile(
        self,
        filename: str,
        mime: str,
        buffer: bytes,
        decoded_buffer: str,
        compression: str = None,
    ):
        """
        Override to add specific header check for .raw files.
        For Bruker .raw files, verify they have the RAW4.00 binary header.
        """
        # First check using parent's matching logic (extension, MIME type)
        if not super().is_mainfile(filename, mime, buffer, decoded_buffer, compression):
            return False

        # Additional check: if it's a .raw file, verify Bruker RAW 4.00 header
        if filename.endswith('.raw'):
            # Check for Bruker RAW 4.00 binary header at the start
            if not buffer.startswith(b'RAW4.00'):
                return False

        return True

    def parse(
        self, mainfile: str, archive: 'EntryArchive', logger=None, child_archives=None
    ) -> None:
        data_file = mainfile.split('/')[-1]
        if isinstance(archive.m_context, ServerContext):
            data_file = mainfile.split('/raw/', 1)[1]
        entry = ELNXRayDiffraction.m_from_dict(ELNXRayDiffraction.m_def.a_template)
        entry.data_file = data_file
        file_name = f'{"".join(data_file.split(".")[:-1])}.archive.json'
        archive.data = RawFileXRDData(
            measurement=create_archive(entry, archive, file_name)
        )
        archive.metadata.entry_name = f'{data_file} data file'
