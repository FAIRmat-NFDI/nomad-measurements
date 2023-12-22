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
    Any,
)
from nomad.units import ureg

if TYPE_CHECKING:
    from nomad.datamodel.data import (
        ArchiveSection,
    )
    from nomad.datamodel.datamodel import (
        EntryArchive,
    )
    from structlog.stdlib import (
        BoundLogger,
    )


def get_reference(upload_id: str, entry_id: str) -> str:
    return f'../uploads/{upload_id}/archive/{entry_id}#data'


def get_entry_id_from_file_name(file_name: str, archive: 'EntryArchive') -> str:
    from nomad.utils import hash
    return hash(archive.metadata.upload_id, file_name)


def create_archive(
        entity: 'ArchiveSection',
        archive: 'EntryArchive',
        file_name: str,
    ) -> str:
    import json
    from nomad.datamodel.context import ClientContext
    if isinstance(archive.m_context, ClientContext):
        return None
    if not archive.m_context.raw_path_exists(file_name):
        entity_entry = entity.m_to_dict(with_root_def=True)
        with archive.m_context.raw_file(file_name, 'w') as outfile:
            json.dump({"data": entity_entry}, outfile)
        archive.m_context.process_updated_raw_file(file_name)
    return get_reference(
        archive.metadata.upload_id,
        get_entry_id_from_file_name(file_name, archive)
    )


def merge_sections(
        section: 'ArchiveSection',
        update: 'ArchiveSection',
        logger: 'BoundLogger'=None,
    ) -> None:
    if update is None:
        return
    if section is None:
        section = update.m_copy()
        return
    if not isinstance(section, type(update)):
        raise TypeError(
            'Cannot merge sections of different types: '
            f'{type(section)} and {type(update)}'
        )
    for name, quantity in update.m_def.all_quantities.items():
        if not update.m_is_set(quantity):
            continue
        if not section.m_is_set(quantity):
            section.m_set(quantity, update.m_get(quantity))
        elif (
            quantity.is_scalar and section.m_get(quantity) != update.m_get(quantity)
            or quantity.repeats and (section.m_get(quantity) != update.m_get(quantity)).any()
        ):
            warning = f'Merging sections with different values for quantity "{name}".'
            if logger:
                logger.warning(warning)
            else:
                print(warning)
    for name, sub_section_def in update.m_def.all_sub_sections.items():
        count = section.m_sub_section_count(sub_section_def)
        if count == 0:
            for update_sub_section in update.m_get_sub_sections(sub_section_def):
                section.m_add_sub_section(sub_section_def, update_sub_section)
        elif count == update.m_sub_section_count(sub_section_def):
            for i in range(count):
                merge_sections(
                    section.m_get_sub_section(sub_section_def, i),
                    update.m_get_sub_section(sub_section_def, i),
                    logger,
                )
        elif update.m_sub_section_count(sub_section_def) > 0:
            warning = f'Merging sections with different number of "{name}" sub sections.'
            if logger:
                logger.warning(warning)
            else:
                print(warning)


def to_pint_quantity(value: Any=None, unit: str=None) -> Any:
    '''
    Attempts to generate a pint quantity.
    In case the value is a string, it is returned as is.

    Args:
        value (Any): Value of the quantity.
        unit (str): Unit of the quantity.

    Returns:
        Any: Processed quantity with datatype depending on the value.
    '''
    if isinstance(value, str):
        return value
    return value * ureg(unit)
