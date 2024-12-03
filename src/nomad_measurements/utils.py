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
import os.path
from typing import (
    TYPE_CHECKING,
)

import numpy as np

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

    entity_entry = entity.m_to_dict(with_root_def=True)
    if isinstance(archive.m_context, ClientContext):
        with open(file_name, 'w') as outfile:
            json.dump({'data': entity_entry}, outfile, indent=4)
        return os.path.abspath(file_name)
    if not archive.m_context.raw_path_exists(file_name):
        with archive.m_context.raw_file(file_name, 'w') as outfile:
            json.dump({'data': entity_entry}, outfile)
        archive.m_context.process_updated_raw_file(file_name)
    return get_reference(
        archive.metadata.upload_id, get_entry_id_from_file_name(file_name, archive)
    )


def _not_equal(a, b) -> bool:
    comparison = a != b
    if isinstance(comparison, np.ndarray):
        return comparison.any()
    return comparison


def merge_sections(  # noqa: PLR0912
    section: 'ArchiveSection',
    update: 'ArchiveSection',
    logger: 'BoundLogger' = None,
) -> None:
    if update is None:
        return
    if section is None:
        section = update.m_copy()
        return
    if update.m_def in [section.m_def, *section.m_def.all_base_sections]:
        raise TypeError(
            'Cannot merge sections of different types: '
            f'{type(section)} and {type(update)}'
        )
    for name, quantity in update.m_def.all_quantities.items():
        if not update.m_is_set(quantity):
            continue
        if not section.m_is_set(quantity):
            section.m_set(quantity, update.m_get(quantity))
        elif _not_equal(section.m_get(quantity), update.m_get(quantity)):
            warning = f'Merging sections with different values for quantity "{name}".'
            if logger:
                logger.warning(warning)
            else:
                print(warning)
    for name, _ in update.m_def.all_sub_sections.items():
        count = section.m_sub_section_count(name)
        if count == 0:
            for update_sub_section in update.m_get_sub_sections(name):
                section.m_add_sub_section(name, update_sub_section)
        elif count == update.m_sub_section_count(name):
            for i in range(count):
                merge_sections(
                    section.m_get_sub_section(name, i),
                    update.m_get_sub_section(name, i),
                    logger,
                )
        elif update.m_sub_section_count(name) > 0:
            warning = (
                f'Merging sections with different number of "{name}" sub sections.'
            )
            if logger:
                logger.warning(warning)
            else:
                print(warning)


def get_bounding_range_2d(ax1, ax2):
    """
    Calculates the range of the smallest rectangular grid that can contain arbitrarily
    distributed 2D data.

    Args:
        ax1 (np.ndarray): array of first axis values
        ax2 (np.ndarray): array of second axis values

    Returns:
        (list, list): ax1_range, ax2_range
    """
    ax1_range_length = np.max(ax1) - np.min(ax1)
    ax2_range_length = np.max(ax2) - np.min(ax2)

    if ax1_range_length > ax2_range_length:
        ax1_range = [np.min(ax1), np.max(ax1)]
        ax2_mid = np.min(ax2) + ax2_range_length / 2
        ax2_range = [
            ax2_mid - ax1_range_length / 2,
            ax2_mid + ax1_range_length / 2,
        ]
    else:
        ax2_range = [np.min(ax2), np.max(ax2)]
        ax1_mid = np.min(ax1) + ax1_range_length / 2
        ax1_range = [
            ax1_mid - ax2_range_length / 2,
            ax1_mid + ax2_range_length / 2,
        ]

    return ax1_range, ax2_range
