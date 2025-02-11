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
import copy
import os.path
import re
from collections import OrderedDict
from typing import (
    TYPE_CHECKING,
    Any,
    Optional,
)

import h5py
import numpy as np
import pint
from nomad.datamodel.hdf5 import HDF5Reference
from nomad.units import ureg
from pydantic import BaseModel, Field
from pynxtools.dataconverter.helpers import (
    generate_template_from_nxdl,
    get_nxdl_root_and_path,
)
from pynxtools.dataconverter.template import Template
from pynxtools.dataconverter.writer import Writer as pynxtools_writer

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


class NXFileGenerationError(Exception):
    pass


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
    """
    Unpopulated quantities and subsections in the `section` will be populated with the
    values from the `update` section.
    If a quantity is present in both sections but with different values, no change is
    made.
    If a repeating subsection is present in both sections, and they are of the same
    length, the subsections will be merged recursively. Else, no change is made.

    Args:
        section (ArchiveSection): section to update.
        update (ArchiveSection): section to update from.
        logger (BoundLogger, optional): A structlog logger.
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
        elif _not_equal(section.m_get(quantity), update.m_get(quantity)):
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


class Dataset(BaseModel):
    """
    Pydantic model for the dataset to be stored in the HDF5 file.
    """

    data: Any = Field(
        description='The data to be stored in the HDF5 file. If `internal_reference` '
        'is True, this should be the path to the existing dataset.'
    )
    archive_path: Optional[str] = Field(
        None,
        description='If the provided dataset is to be referenced by a `HDF5Reference` '
        'quantity in a NOMAD entry archive, `archive_path` is the path to this '
        'quantity in the archive. '
        'For example, "data.results[0].plot_intensity.intensity".',
    )
    internal_reference: Optional[bool] = Field(
        False,
        description='If True, an internal reference is set to an existing HDF5 '
        'dataset. The path to the referenced dataset should be provided in the data.',
    )


class HDF5Handler:
    """
    Class for handling the creation of auxiliary files (e.g. NeXus, HDF5) to store big
    data arrays outside the main archive file.
    """

    def __init__(
        self,
        filename: str,
        archive: 'EntryArchive',
        logger: 'BoundLogger',
        nexus_dataset_map: dict = None,
    ):
        """
        Initialize the handler with at least the filename, NOMAD archive, and a logger.
        If the optional `nexus_dataset_map` is provided, the auxialiary file is created
        as a NeXus file. Otherwise, it is created as an HDF5 file. Additionally, the
        path of the added datasets is validated against the `nexus_dataset_map`.

        Args:
            filename (str): The name of the auxiliary file.
            archive (EntryArchive): The NOMAD archive.
            logger (BoundLogger): A structlog logger.
            nexus_dataset_map (dict): The NeXus dataset map containing the nexus file
                dataset paths and the corresponding archive paths.
        """
        if not filename.endswith(('.nxs', '.h5')):
            raise ValueError('Only .nxs and .h5 files are supported.')

        self.filename = filename
        self.archive = archive
        self.logger = logger
        self.nexus_dataset_map = nexus_dataset_map

        self._nexus_generation_error = False
        self._hdf5_datasets: OrderedDict[str, Dataset] = OrderedDict()
        self._hdf5_attributes: OrderedDict[str, dict] = OrderedDict()
        self._hdf5_path_map: OrderedDict[str, str] = OrderedDict()

    def add_dataset(
        self,
        path: str,
        dataset: Dataset,
        validate_path: bool = True,
    ):
        """
        Add a dataset to the HDF5 file. The dataset is written to the file when
        `write_file` method is called. The `path` is validated against the
        `nexus_dataset_map` if provided before adding the data.

        `dataset` should be an instance of the basemodel `Dataset`.

        Args:
            path (str): The dataset path to be used in the HDF5 file.
            params (dict): The dataset parameters.
            validate_path (bool): If `nexus_dataset_map` is provided to the handler,
                the dataset path is validated against it.
        """
        if not dataset:
            self.logger.warning(f'No params provided for path "{path}". Skipping.')
            return

        if dataset.data is None:
            self.logger.warning(f'No data provided for the path "{path}". Skipping.')
            return
        if (
            validate_path
            and self.nexus_dataset_map
            and path not in self.nexus_dataset_map
        ):
            self.logger.warning(f'Invalid dataset path "{path}". Skipping.')
            return

        # handle the pint.Quantity and add data
        if isinstance(dataset.data, pint.Quantity):
            self.add_attribute(
                path=path,
                params=dict(
                    units=str(dataset.data.units),
                ),
            )
            dataset.data = dataset.data.magnitude

        self._hdf5_datasets[path] = dataset
        if dataset.archive_path:
            self._hdf5_path_map[dataset.archive_path] = path

    def add_attribute(
        self,
        path: str,
        params: dict,
    ):
        """
        Add an attribute to the dataset or group at the given path. The attribute is
        written to the file when `write_file` method is called.

        Args:
            path (str): The dataset or group path in the HDF5 file.
            params (dict): The attributes to be added.
        """
        if not params:
            self.logger.warning(f'No params provided for attribute {path}.')
            return
        self._hdf5_attributes[path] = params

    def read_dataset(self, path: str, is_archive_path: bool = False):
        """
        Returns the dataset at the given path. If the quantity has `units` as an
        attribute, tries to returns a `pint.Quantity`.
        If the dataset available in the `self._hdf5_datasets`, it is returned directly.

        Args:
            path (str): The dataset path in the HDF5 file.
            is_archive_path (bool): If True, the given path is assumed to be the archive
                path of quantity in the entry archive. It returns the dataset that was
                added to the handler with the same archive path. For example, if a
                dataset with the archive path `data.results[0].intensity` was added
                previously and the same path is queried in this method, the HDF5
                path will be resolved automatically and the dataset will be returned.
        """
        if path is None:
            return
        if is_archive_path and path in self._hdf5_path_map:
            path = self._hdf5_path_map[path]
            if path is None:
                return
        if '#' not in path:
            dataset_path = path
        else:
            dataset_path = path.rsplit('#', 1)

        # find path in the instance variables
        value = None
        if dataset_path in self._hdf5_datasets:
            value = self._hdf5_datasets[dataset_path].data
            if dataset_path in self._hdf5_attributes:
                if units := self._hdf5_attributes[dataset_path].get('units'):
                    value *= ureg(units)
            return value

        # find path in the HDF5 file
        with h5py.File(self.archive.m_context.raw_file(self.filename, 'rb')) as h5:
            if dataset_path not in h5:
                self.logger.warning(f'Dataset "{dataset_path}" not found.')
            else:
                value = h5[dataset_path][...]
                try:
                    units = h5[dataset_path].attrs['units']
                    value *= ureg(units)
                except KeyError:
                    pass
            return value

        return None

    def write_file(self):
        """
        Method for creating an auxiliary file to store big data arrays outside the
        main archive file (e.g. NeXus, HDF5). If the `nexus_dataset_map` is provided,
        a NeXus file is created. Otherwise, an HDF5 file is created. If an error is
        encountered while creating the NeXus file, an HDF5 file is created instead.
        """
        if self.nexus_dataset_map and not self._nexus_generation_error:
            try:
                self._write_nx_file()
            except Exception as e:
                self._nexus_generation_error = True
                self.logger.warning(
                    f"""NeXusFileGenerationError: Encountered '{e}' error while creating
                    nexus file. Creating h5 file instead."""
                )
                self._write_hdf5_file()
        else:
            self._write_hdf5_file()

        self.set_hdf5_references()

    def _write_nx_file(self):
        """
        Method for creating a NeXus file. The `nexus_dataset_map` is used to create the
        NeXus file. The data is extracted from the archive and added to the NeXus file
        based on the `nexus_dataset_map`. Additionally, the datasets and attributes
        added to the handler are written to the file. If the dataset is an internal
        reference, a link is created to the existing dataset in the NeXus file.
        """

        app_def = self.nexus_dataset_map.get('/ENTRY[entry]/definition')
        nxdl_root, nxdl_f_path = get_nxdl_root_and_path(app_def)
        template = Template()
        generate_template_from_nxdl(nxdl_root, template)
        attr_dict = {}
        dataset_dict = {}
        self.populate_nx_dataset_and_attribute(
            attr_dict=attr_dict, dataset_dict=dataset_dict
        )
        for nx_path, dset_original in list(self._hdf5_datasets.items()) + list(
            dataset_dict.items()
        ):
            dset = copy.deepcopy(dset_original)
            if dset.internal_reference:
                # convert to the nexus type link
                dset.data = {'link': self._remove_nexus_annotations(dset.data)}

            try:
                template[nx_path] = dset.data
            except KeyError:
                template['optional'][nx_path] = dset.data

        for nx_path, attr_d in list(self._hdf5_attributes.items()) + list(
            attr_dict.items()
        ):
            for attr_k, attr_v in attr_d.items():
                if attr_v != 'dimensionless' and attr_v:
                    try:
                        template[f'{nx_path}/@{attr_k}'] = attr_v
                    except KeyError:
                        template['optional'][f'{nx_path}/@{attr_k}'] = attr_v

        nx_full_file_path = os.path.join(
            self.archive.m_context.raw_path(), self.filename
        )

        pynxtools_writer(
            data=template, nxdl_f_path=nxdl_f_path, output_path=nx_full_file_path
        ).write()
        self.archive.m_context.process_updated_raw_file(
            self.filename, allow_modify=True
        )

    def _write_hdf5_file(self):
        """
        Method for creating an HDF5 file. Datasets and attributes added to the handler
        are written to the file. If the dataset is an internal reference, a hard link is
        created to the existing dataset in `.h5` file. The nexus annotations are removed
        from the dataset paths before writing to the file.
        """
        if self.filename.endswith('.nxs'):
            self.filename = self.filename.replace('.nxs', '.h5')
        if not self._hdf5_datasets and not self._hdf5_attributes:
            return
        # remove the nexus annotations from the dataset paths if any
        self._hdf5_datasets = OrderedDict(
            (self._remove_nexus_annotations(key), value)
            for key, value in self._hdf5_datasets.items()
        )
        self._hdf5_attributes = OrderedDict(
            (self._remove_nexus_annotations(key), value)
            for key, value in self._hdf5_attributes.items()
        )

        # create the HDF5 file
        mode = 'r+b' if self.archive.m_context.raw_path_exists(self.filename) else 'wb'
        with h5py.File(self.archive.m_context.raw_file(self.filename, mode), 'a') as h5:
            for key, value in self._hdf5_datasets.items():
                data = value.data
                if value.internal_reference:
                    # resolve the internal reference
                    try:
                        data = h5[self._remove_nexus_annotations(value.data)]
                    except KeyError:
                        self.logger.warning(
                            f'Internal reference "{value.data}" not found. Skipping.'
                        )
                        continue

                group_name, dataset_name = key.rsplit('/', 1)
                group = h5.require_group(group_name)

                if key in h5:
                    # remove the existing dataset if any
                    del h5[key]

                if value.internal_reference:
                    # create a hard link to the existing dataset
                    group[dataset_name] = data
                else:
                    # create the dataset
                    group.create_dataset(
                        name=dataset_name,
                        data=data,
                    )
            for key, value in self._hdf5_attributes.items():
                if key in h5:
                    h5[key].attrs.update(value)
                else:
                    self.logger.warning(f'Path "{key}" not found to add attribute.')

    def set_hdf5_references(self):
        """
        Method for adding the HDF5 references to the archive quantities.
        """
        for key, value in self._hdf5_datasets.items():
            if value.archive_path:
                reference = self._remove_nexus_annotations(key)
                self._set_hdf5_reference(
                    self.archive,
                    value.archive_path,
                    f'/uploads/{self.archive.m_context.upload_id}/raw'
                    f'/{self.filename}#{reference}',
                )

    def populate_nx_dataset_and_attribute(self, attr_dict: dict, dataset_dict: dict):
        """
        Extracts the data from the entry archive, according to the given map in
        `nexus_dataset_map`and populates the given datasets and attributes dictionaries.
        Skips the datasets and attributes that have been added to the handler.

        Args:
            attr_dict (dict): The dictionary to store the attributes.
            dataset_dict (dict): The dictionary to store the datasets.
        """

        for nx_path, arch_path in self.nexus_dataset_map.items():
            if nx_path in self._hdf5_datasets or nx_path in self._hdf5_attributes:
                continue
            if arch_path.startswith('archive.'):
                data = resolve_path(self.archive, arch_path.split('archive.', 1)[1])
            else:
                data = arch_path  # default value

            dataset = Dataset(data=data)

            if (
                isinstance(data, pint.Quantity)
                and str(data.units) != 'dimensionless'
                and str(data.units)
            ):
                attr_tmp = {nx_path: dict(units=str(data.units))}
                attr_dict |= attr_tmp
                dataset.data = data.magnitude

            l_part, r_part = nx_path.rsplit('/', 1)
            if r_part.startswith('@'):
                attr_dict[l_part] = {r_part.replace('@', ''): data}
            else:
                dataset_dict[nx_path] = dataset

    @staticmethod
    def _remove_nexus_annotations(path: str) -> str:
        """
        Remove the nexus related annotations from the dataset path.
        For e.g.,
        '/ENTRY[entry]/experiment_result/intensity' ->
        '/entry/experiment_result/intensity'

        Args:
            path (str): The dataset path with nexus annotations.

        Returns:
            str: The dataset path without nexus annotations.
        """
        if not path:
            return path

        pattern = r'.*\[.*\]'
        return ''.join(
            (
                '/' + part.split('[')[0].strip().lower()
                if re.match(pattern, part)
                else f'/{part}'
            )
            for part in path.split('/')[1:]
        )

    @staticmethod
    def _set_hdf5_reference(
        section: 'ArchiveSection' = None, path: str = None, ref: str = None
    ):
        """
        Method for setting a HDF5Reference quantity in a section.
        For example, one can set the reference for a quantity path like
        `data.results[0].intensity`.
        In case the section is not initialized, the method returns without setting
        the reference.

        Args:
            section (Section): The NOMAD section containing the quantity.
            path (str): The path to the quantity.
            ref (str): The reference to the HDF5 dataset.
        """
        if not section or not path or not ref:
            return

        section_path, quantity_name = path.rsplit('.', 1)
        resolved_section = resolve_path(section, section_path)

        if resolved_section and isinstance(
            resolved_section.m_get_quantity_definition(quantity_name).type,
            HDF5Reference,
        ):
            resolved_section.m_set(quantity_name, ref)


def resolve_path(section: 'ArchiveSection', path: str, logger: 'BoundLogger' = None):
    """
    Resolves the attribute path within the given NOMAD section.
    For example, if the path is `data.results[0].intensity`, the method returns the
    value of the `intensity` quantity in the `results` subsection of the `data` section.

    Args:
        section (ArchiveSection): The NOMAD section.
        path (str): The dot-separated path to the attribute.
        logger (BoundLogger): A structlog logger.

    Returns:
        The resolved section or attribute or None if not found.
    """
    attr = section
    parts = path.split('.')
    try:
        for part in parts:
            attr_path = part
            if re.match(r'.*\[.*\]', attr_path):
                attr_path, index = part[:-1].split('[')
                index = int(index)
            else:
                index = None
            attr = attr.m_get(attr_path, index=index)
    except (KeyError, ValueError, AttributeError) as e:
        if logger:
            logger.error(
                f'Unable to resolve part "{part}" of the given path "{path}". '
                f'Encountered error "{e}".'
            )
        return None

    return attr
