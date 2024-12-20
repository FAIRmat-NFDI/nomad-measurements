import os
from typing import (
    TYPE_CHECKING,
)

if TYPE_CHECKING:
    from nomad.datamodel import (
        EntryArchive,
    )
    from nomad.datamodel.data import (
        ArchiveSection,
    )
    from structlog.stdlib import (
        BoundLogger,
    )


def merge_sections(  # noqa: PLR0912
    section: 'ArchiveSection',
    update: 'ArchiveSection',
    overwrite_quantity: bool = False,
    logger: 'BoundLogger' = None,
) -> None:
    """
    Updates the `section` based on the `update` section.
    Unpopulated quantities and subsections in the `section` will be populated with the
    values from the `update` section.
    In case a repeating subsection in update section has a different number of entries,
    a warning will be issued, and `section` will remain unchanged.
    In case a quantity is present in both sections, the one in `section` will be
    overwritten provided that `overwrite_quantity` is set to `True`.

    Args:
        section (ArchiveSection): section to update.
        update (ArchiveSection): section to update from.
        overwrite_quantity (bool, optional): Whether to overwrite in `section`.
        logger (BoundLogger, optional): A structlog logger.

    Raises:
        TypeError: If the sections are of different types.
    """
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
            quantity.is_scalar
            and section.m_get(quantity) != update.m_get(quantity)
            or not quantity.is_scalar
            and (section.m_get(quantity) != update.m_get(quantity)).any()
        ):
            if overwrite_quantity:
                section.m_set(quantity, update.m_get(quantity))
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
            warning = (
                f'Merging sections with different number of "{name}" sub sections.'
            )
            if logger:
                logger.warning(warning)
            else:
                print(warning)


def get_reference(upload_id, entry_id):
    return f'../uploads/{upload_id}/archive/{entry_id}#/data'


def get_entry_id_from_file_name(file_name, archive):
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
