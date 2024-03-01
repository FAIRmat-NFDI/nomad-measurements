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
import numpy as np
import collections
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
    entity_entry = entity.m_to_dict(with_root_def=True)
    if isinstance(archive.m_context, ClientContext):
        with open(file_name, 'w') as outfile:
            json.dump({"data": entity_entry}, outfile, indent=4)
        return os.path.abspath(file_name)
    if not archive.m_context.raw_path_exists(file_name):
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
    If the value is a pint quantity, it is converted to the given unit.

    Args:
        value (Any): Value of the quantity.
        unit (str): Unit of the quantity.

    Returns:
        Any: Processed quantity with datatype depending on the value.
    '''
    if isinstance(value, str) or value is None:
        return value
    if isinstance(value, ureg.Quantity):
        if unit is None:
            return value
        return value.to(unit)
    return value * ureg(unit)

def are_all_identical(arr_list):
    '''
    Check if all the arrays in the list are identical. Also works if the arrays are
    pint.Quantity.

    Args:
        arr_list (list): A list of numpy arrays.

    Returns:
        bool: True if all the arrays are identical, False otherwise.
    '''
    first_arr = arr_list[0]
    if isinstance(first_arr, ureg.Quantity):
        first_arr = first_arr.magnitude

    for arr in arr_list[1:]:
        if isinstance(arr, ureg.Quantity):
            arr = arr.magnitude
        if not np.array_equal(first_arr, arr):
            return False
    return True

def detect_scan_type(scan_data):
    '''
    Based on the shape of data vectors, decide whether the scan_type is `line` (single
    line scan), `multiline` (multiple line scans), or `rsm` (reciprocal space mapping).
    For a 2D scan, if the conditions for `rsm` are not met, it is considered a `multiline`
    scan.

    Args:
        scan_data (dict): The X-ray diffraction data in a Python dictionary. Each key is
            a list of pint.Quantity.

    Returns:
        str: The type of scan.
    '''
    if len(scan_data['intensity']) == 1:
        return 'line'

    # if intensity data is not a regular 2D array, it is not `rsm`
    for scan_intensity in scan_data['intensity'][1:]:
        if scan_intensity.shape != scan_data['intensity'][0].shape:
            return 'multiline'

    intensity_data = np.array(scan_data['intensity']).squeeze()
    if intensity_data.ndim == 2:
        if not are_all_identical(scan_data['2Theta']):
            return 'multiline'
        # find axis that updates from one scan to other
        var_axis = []
        for key in ['Omega', 'Chi', 'Phi', 'Theta']:
            if key not in scan_data:
                continue
            data = scan_data[key]
            if not are_all_identical(data):
                var_axis.append(key)
        # if only one var_axis
        # and dimensions of 2theta, var_axis, and intensity are consistent, it is a rsm
        if len(var_axis) == 1:
            two_theta = np.array(scan_data['2Theta'])
            omega = np.array(scan_data[var_axis[0]])
            if (
                intensity_data.shape == two_theta.shape \
                and intensity_data.shape[0] == np.unique(omega).shape[0]
            ):
                return 'rsm'
        return 'multiline'
    else:
        raise AssertionError(f'Scan type not detected. `intensity.ndim` must be 1 or 2.\
                             Found: {intensity_data.ndim}')

def modify_scan_data(scan_data: dict, scan_type: str):
    '''
    Modifies the scan data based on the scan type:

    If the scan type is `line`, the data is converted to 1D arrays.

    If the scan type is `rsm`, data is converted into 2D arrays. Reduction of dimensions
    is performed wherever possible. Matrix of shape (1,n) is converted to a 1D array of
    length `n`. Further, if the vector contains identical elements, it is reduced to a
    point vector of size 1. In case the rows of the 2D array are identical, it is reduced
    to a 1D array containing the first row. Similar to before, if the elements of this row
    are identical, it is reduced to a point vector of size 1.

    If the scan type is `multiline`, the data is converted into a list of 1D arrays.
    TODO: Add support for `multiline` scans.

    Args:
        scan_data (dict): The X-ray diffraction data in a Python dictionary. Each key is
            a list of pint.Quantity.
        scan_type (str): The type of scan.
    '''
    output = collections.defaultdict(lambda: None)

    if scan_type not in ['line', 'rsm', 'multiline']:
        raise ValueError(f'Invalid scan type: {scan_type}')

    if scan_type == 'line':
        for key, value in scan_data.items():
            if value is None:
                continue
            data = value[0].magnitude
            if np.all(np.diff(data, axis=0) == 0):
                # if elements are identical, pick the first one
                data = np.array([data[0]])
            output[key] = data * value[0].units
        return output

    elif scan_type == 'multiline':
        raise NotImplementedError(f'Scan type {scan_type} is not supported.')

    elif scan_type == 'rsm':
        for key, value in scan_data.items():
            if value is None:
                continue
            data = np.array(value)
            # if it is column vector, make it a row vector
            if data.shape[1] == 1:
                data = data.reshape(-1)
            # if rows (or elements of a row) are identical, pick the first one
            if np.all(np.diff(data, axis=0) == 0):
                data = data[0].reshape(-1)
            output[key] = data * value[0].units
        return output

def get_bounding_range_2d(ax1, ax2):
    '''
    Calculates the range of the smallest rectangular grid that can contain arbitrarily
    distributed 2D data.

    Args:
        ax1 (np.ndarray): array of first axis values
        ax2 (np.ndarray): array of second axis values

    Returns:
        (list, list): ax1_range, ax2_range
    '''
    ax1_range_length = np.max(ax1) - np.min(ax1)
    ax2_range_length = np.max(ax2) - np.min(ax2)

    if ax1_range_length > ax2_range_length:
        ax1_range = [np.min(ax1),np.max(ax1)]
        ax2_mid = np.min(ax2) + ax2_range_length/2
        ax2_range = [
            ax2_mid-ax1_range_length/2,
            ax2_mid+ax1_range_length/2,
        ]
    else:
        ax2_range = [np.min(ax2),np.max(ax2)]
        ax1_mid = np.min(ax1) + ax1_range_length/2
        ax1_range = [
            ax1_mid-ax2_range_length/2,
            ax1_mid+ax2_range_length/2,
        ]

    return ax1_range, ax2_range