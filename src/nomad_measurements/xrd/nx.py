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

from typing import TYPE_CHECKING, Any, Optional
import pint

import copy
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive


NEXUS_DATASET_PATHS = [
    '/ENTRY[entry]/experiment_result/intensity',
    '/ENTRY[entry]/experiment_result/two_theta',
    '/ENTRY[entry]/experiment_result/omega',
    '/ENTRY[entry]/experiment_result/chi',
    '/ENTRY[entry]/experiment_result/phi',
    '/ENTRY[entry]/experiment_config/count_time',
    '/ENTRY[entry]/experiment_result/q_norm',
    '/ENTRY[entry]/experiment_result/q_parallel',
    '/ENTRY[entry]/experiment_result/q_perpendicular',
    '/ENTRY[entry]/method',
    '/ENTRY[entry]/measurement_type',
    '/ENTRY[entry]/INSTRUMENT[instrument]/DETECTOR[detector]/scan_axis',
    '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/xray_tube_material',
    '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/xray_tube_current',
    '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/xray_tube_voltage',
    '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/k_alpha_one',
    '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/k_alpha_two',
    '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/ratio_k_alphatwo_k_alphaone',
    '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/kbeta',
]


CONCEPT_MAP = {
    '/ENTRY[entry]/@default': 'experiment_result',
    '/ENTRY[entry]/definition': 'NXxrd_pan',
    '/ENTRY[entry]/method': 'archive.data.method',
    '/ENTRY[entry]/measurement_type': 'archive.data.diffraction_method_name',
    '/ENTRY[entry]/experiment_result/@signal': 'intensity',
    '/ENTRY[entry]/INSTRUMENT[instrument]/DETECTOR[detector]/scan_axis': 'archive.data.results[0].scan_axis',
    '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/xray_tube_material': 'archive.data.xrd_settings.source.xray_tube_material',
    '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/xray_tube_current': 'archive.data.xrd_settings.source.xray_tube_current',
    '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/xray_tube_voltage': 'archive.data.xrd_settings.source.xray_tube_voltage',
    '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/k_alpha_one': 'archive.data.xrd_settings.source.kalpha_one',
    '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/k_alpha_two': 'archive.data.xrd_settings.source.kalpha_two',
    '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/ratio_k_alphatwo_k_alphaone': 'archive.data.xrd_settings.source.ratio_kalphatwo_kalphaone',
    '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/kbeta': 'archive.data.xrd_settings.source.kbeta',
}


def walk_through_object(parent_obj, attr_chain):
    """
    Walk though the object until reach the leaf.

    Args:
        parent_obj: This is a python obj.
            e.g.Arvhive
        attr_chain: Dot separated obj chain.
            e.g. 'archive.data.xrd_settings.source.xray_tube_material'
        default: A value to be returned by default, if not data is found.
    """
    if parent_obj is None:
        return parent_obj

    if isinstance(attr_chain, str) and attr_chain.startswith('archive.'):
        parts = attr_chain.split('.')
        child_obj = None
        for part in parts[1:]:
            child_nm = part
            if '[' in child_nm:
                child_nm, index = child_nm.split('[')
                index = int(index[:-1])
                # section always exists
                child_obj = getattr(parent_obj, child_nm)[index]
            else:
                child_obj = getattr(parent_obj, child_nm, None)
            parent_obj = child_obj

        return child_obj


def populate_nx_dataset_and_attribute(
    archive: 'EntryArchive', attr_dict: dict, dataset_dict: dict
):
    """Construct datasets and attributes for nexus and populate."""
    from nomad_measurements.utils import DatasetModel

    concept_map = copy.deepcopy(CONCEPT_MAP)
    for nx_path, arch_path in concept_map.items():
        if arch_path.startswith('archive.'):
            data = walk_through_object(archive, arch_path)
        else:
            data = arch_path  # default value

        dataset = DatasetModel(
            data=data,
        )

        if isinstance(data, pint.Quantity):
            if str(data.units) != 'dimensionless' and str(data.units):
                attr_tmp = {nx_path: dict(units=str(data.units))}
                attr_dict.update(attr_tmp)
                # attr_dict[nx_path].update({'units': str(data.units)})
                dataset.data = data.magnitude

        l_part, r_part = nx_path.split('/', 1)
        if r_part.startswith('@'):
            attr_dict[l_part] = {r_part.replace('@', ''): data}
        else:
            dataset_dict[nx_path] = dataset


def add_group_and_return_child_group(child_group_name, parent_group=None, nxclass=None):
    """Create group with name `child_group_name` under the parent_group"""

    if (parts := child_group_name.split('[', 1)) and len(parts) > 1:
        nxclass = parts[0]
        grp_name_tmp = parts[1].split(']')[0]
    else:
        grp_name_tmp = child_group_name
    parent_group.require_group(grp_name_tmp)
    child_group = parent_group[grp_name_tmp]
    if nxclass:
        child_group.attrs['NX_class'] = 'NX' + nxclass.lower()

    return child_group
