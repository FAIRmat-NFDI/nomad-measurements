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
import collections
import os.path
import re
from typing import (
    TYPE_CHECKING,
    Any,
    Optional,
)

import h5py
import copy
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

from nomad_measurements.xrd.nx import populate_nx_dataset_and_attribute

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


class DatasetModel(BaseModel):
    """
    Pydantic model for the dataset to be stored in the HDF5 file.
    """

    data: Any = Field(description='The data to be stored in the HDF5 file.')
    archive_path: Optional[str] = Field(
        None, description='The path of the quantity in the NOMAD archive.'
    )
    internal_reference: Optional[bool] = Field(
        False,
        description='If True, an internal reference is set to an existing HDF5 '
        'dataset.',
    )


class HDF5Handler:
    """
    Class for handling the creation of auxiliary files to store big data arrays outside
    the main archive file (e.g. HDF5, NeXus).
    """

    def __init__(
        self,
        filename: str,
        archive: 'EntryArchive',
        logger: 'BoundLogger',
        valid_dataset_paths: list = None,
        nexus: bool = False,
    ):
        """
        Initialize the handler.

        Args:
            filename (str): The name of the auxiliary file.
            archive (EntryArchive): The NOMAD archive.
            logger (BoundLogger): A structlog logger.
            valid_dataset_paths (list): The list of valid dataset paths.
            nexus (bool): If True, the file is created as a NeXus file.
        """
        if not filename.endswith(('.nxs', '.h5')):
            raise ValueError('Only .h5 or .nxs files are supported.')

        self.data_file = filename
        self.archive = archive
        self.logger = logger
        self.valid_dataset_paths = []
        if valid_dataset_paths:
            self.valid_dataset_paths = valid_dataset_paths
        self.nexus = nexus

        self._hdf5_datasets = collections.OrderedDict()
        self._hdf5_attributes = collections.OrderedDict()

    def add_dataset(
        self,
        path: str,
        params: dict,
        validate_path: bool = True,
    ):
        """
        Add a dataset to the HDF5 file. The dataset is written lazily to the file
        when `write_file` method is called. The `path` is validated against the
        `valid_dataset_paths` if provided before adding the data.

        `params` should be a dictionary containing `data`. Optionally,
        it can also contain `archive_path` and `internal_reference`:
        {
            'data': Any,
            'archive_path': str,
            'internal_reference': bool,
        }

        Args:
            path (str): The dataset path to be used in the HDF5 file.
            params (dict): The dataset parameters.
            validate_path (bool): If True, the dataset path is validated.
        """
        if not params:
            self.logger.warning('Dataset `params` must be provided.')
            return

        dataset = DatasetModel(
            **params,
        )
        if (
            validate_path
            and self.valid_dataset_paths
            and path not in self.valid_dataset_paths
        ):
            self.logger.warning(f'Invalid dataset path "{path}".')
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

    def add_attribute(
        self,
        path: str,
        params: dict,
    ):
        """
        Add an attribute to the dataset or group at the given path. The attribute is
        written lazily to the file when `write_file` method is called.

        Args:
            path (str): The dataset or group path in the HDF5 file.
            params (dict): The attributes to be added.
        """
        if not params:
            self.logger.warning('Attribute `params` must be provided.')
            return
        self._hdf5_attributes[path] = params

    def read_dataset(self, path: str):
        """
        Returns the dataset at the given path. If the quantity has `units` as an
        attribute, tries to returns a `pint.Quantity`.
        If the dataset available in the `self._hdf5_datasets`, it is returned directly.

        Args:
            path (str): The dataset path in the HDF5 file.
        """
        if path is None:
            return
        file_path, dataset_path = path.split('#')

        # find path in the instance variables
        value = None
        if dataset_path in self._hdf5_datasets:
            value = self._hdf5_datasets[dataset_path].data
            if dataset_path in self._hdf5_attributes:
                units = self._hdf5_attributes[dataset_path].get('units')
                if units:
                    value *= ureg(units)
            return value

        file_name = file_path.rsplit('/raw/', 1)[1]
        with h5py.File(self.archive.m_context.raw_file(file_name, 'rb')) as h5:
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

    def write_file(self):
        """
        Method for creating an auxiliary file to store big data arrays outside the
        main archive file (e.g. HDF5, NeXus).
        """
        if self.nexus:
            try:
                self._write_nx_file()
            except Exception as e:
                self.nexus = False
                self.logger.warning(
                    f'Encountered "{e}" error while creating nexus file. '
                    'Creating h5 file instead.'
                )
                self._write_hdf5_file()
        else:
            self._write_hdf5_file()

    def _write_nx_file(self):
        """
        Method for creating a NeXus file. Additional data from the archive is added
        to the `hdf5_data_dict` before creating the nexus file. This provides a NeXus
        view of the data in addition to storing array data.
        """
        from nomad.processing.data import Entry

        app_def = 'NXxrd_pan'
        nxdl_root, nxdl_f_path = get_nxdl_root_and_path(app_def)
        template = Template()
        generate_template_from_nxdl(nxdl_root, template)
        attr_dict = {}
        dataset_dict = {}
        populate_nx_dataset_and_attribute(
            archive=self.archive, attr_dict=attr_dict, dataset_dict=dataset_dict
        )
        for nx_path, dset_ori in list(self._hdf5_datasets.items()) + list(
            dataset_dict.items()
        ):
            dset = copy.deepcopy(dset_ori)
            if dset.internal_reference:
                # convert to the nexus type link
                dset.data = {'link': self._remove_nexus_annotations(dset.data)}

            try:
                template[nx_path] = dset.data
            except KeyError:
                template['optional'][nx_path] = dset.data

            hdf5_path = self._remove_nexus_annotations(nx_path)
            self._set_hdf5_reference(
                self.archive,
                dset.archive_path,
                f'/uploads/{self.archive.m_context.upload_id}/raw'
                f'/{self.data_file}#{hdf5_path}',
            )
        for nx_path, attr_d in list(self._hdf5_attributes.items()) + list(
            attr_dict.items()
        ):
            # hdf5_path = self._remove_nexus_annotations(nx_path)
            for attr_k, attr_v in attr_d.items():
                if attr_v != 'dimensionless' and attr_v:
                    try:
                        template[f'{nx_path}/@{attr_k}'] = attr_v
                    except KeyError:
                        template['optional'][f'{nx_path}/@{attr_k}'] = attr_v
        try:
            nx_full_file_path = os.path.join(
                self.archive.m_context.raw_path(), self.data_file
            )
            if self.archive.m_context.raw_path_exists(self.data_file):
                os.remove(nx_full_file_path)

            pynxtools_writer(
                data=template, nxdl_f_path=nxdl_f_path, output_path=nx_full_file_path
            ).write()

            entry_list = Entry.objects(
                upload_id=self.archive.m_context.upload_id, mainfile=self.data_file
            )
            if not entry_list:
                self.archive.m_context.process_updated_raw_file(self.data_file)

        except Exception as exc:
            if os.path.exists(self.data_file):
                os.remove(self.data_file)
                self.data_file = self.data_file.rsplit(os.pathsep, 1)[-1]
            raise Exception('NeXus file can not be generated.') from exc

    def _write_hdf5_file(self):  # noqa: PLR0912
        """
        Method for creating an HDF5 file.
        """
        if self.data_file.endswith('.nxs'):
            self.data_file = self.data_file.replace('.nxs', '.h5')
        if not self._hdf5_datasets and not self._hdf5_attributes:
            return
        # remove the nexus annotations from the dataset paths if any
        tmp_dict = {}
        for key, value in self._hdf5_datasets.items():
            new_key = self._remove_nexus_annotations(key)
            tmp_dict[new_key] = value
        self._hdf5_datasets = tmp_dict
        tmp_dict = {}
        for key, value in self._hdf5_attributes.items():
            tmp_dict[self._remove_nexus_annotations(key)] = value
        self._hdf5_attributes = tmp_dict

        # create the HDF5 file
        mode = 'r+b' if self.archive.m_context.raw_path_exists(self.data_file) else 'wb'
        with h5py.File(
            self.archive.m_context.raw_file(self.data_file, mode), 'a'
        ) as h5:
            for key, value in self._hdf5_datasets.items():
                if value.data is None:
                    self.logger.warning(f'No data found for "{key}". Skipping.')
                    continue
                elif value.internal_reference:
                    # resolve the internal reference
                    try:
                        data = h5[self._remove_nexus_annotations(value.data)]
                    except KeyError:
                        self.logger.warning(
                            f'Internal reference "{value.data}" not found. Skipping.'
                        )
                        continue
                else:
                    data = value.data

                group_name, dataset_name = key.rsplit('/', 1)
                group = h5.require_group(group_name)

                if key in h5:
                    group[dataset_name][...] = data
                else:
                    group.create_dataset(
                        name=dataset_name,
                        data=data,
                    )
                self._set_hdf5_reference(
                    self.archive,
                    value.archive_path,
                    f'/uploads/{self.archive.m_context.upload_id}/raw'
                    f'/{self.data_file}#{key}',
                )
            for key, value in self._hdf5_attributes.items():
                if key in h5:
                    h5[key].attrs.update(value)
                else:
                    self.logger.warning(f'Path "{key}" not found to add attribute.')

        # reset hdf5 datasets and atttributes
        self._hdf5_datasets = collections.OrderedDict()
        self._hdf5_attributes = collections.OrderedDict()

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
        new_path = ''
        for part in path.split('/')[1:]:
            if re.match(pattern, part):
                new_path += '/' + part.split('[')[0].strip().lower()
            else:
                new_path += '/' + part
        new_path = new_path.replace('.nxs', '.h5')
        return new_path

    @staticmethod
    def _set_hdf5_reference(
        section: 'ArchiveSection' = None, path: str = None, ref: str = None
    ):
        """
        Method for setting a HDF5Reference quantity in a section. It can handle
        nested quantities and repeatable sections, provided that the quantity itself
        is of type `HDF5Reference`.
        For example, one can set the reference for a quantity path like
        `data.results[0].intensity`.

        Args:
            section (Section): The NOMAD section containing the quantity.
            path (str): The path to the quantity.
            ref (str): The reference to the HDF5 dataset.
        """
        # TODO handle the case when section in the path is not initialized

        if not section or not path or not ref:
            return
        attr = section
        path = path.split('.')
        quantity_name = path.pop()

        for subpath in path:
            if re.match(r'.*\[.*\]', subpath):
                index = int(subpath.split('[')[1].split(']')[0])
                attr = attr.m_get(subpath.split('[')[0], index=index)
            else:
                attr = attr.m_get(subpath)

        if isinstance(
            attr.m_get_quantity_definition(quantity_name).type, HDF5Reference
        ):
            attr.m_set(quantity_name, ref)
