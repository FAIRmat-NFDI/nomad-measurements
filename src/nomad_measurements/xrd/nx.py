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
import re
from collections import OrderedDict
from typing import TYPE_CHECKING

from pynxtools import dataconverter
from pynxtools.nomad.dataconverter import populate_nexus_subsection

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import (
        BoundLogger,
    )


CONCEPT_MAP = OrderedDict(
    {
        # Mapping data in raw_data: data in the raw file from the instrument
        # Make sure to defines the mapping for magnitude before the mapping for units
        '/ENTRY[entry]/experiment_result/intensity': 'raw_data.intensity.magnitude',
        '/ENTRY[entry]/experiment_result/two_theta': 'raw_data.2Theta.magnitude',
        '/ENTRY[entry]/experiment_result/two_theta/@units': 'raw_data.2Theta.units',
        '/ENTRY[entry]/experiment_result/omega': 'raw_data.Omega.magnitude',
        '/ENTRY[entry]/experiment_result/omega/@units': 'raw_data.Omega.units',
        '/ENTRY[entry]/experiment_result/chi': 'raw_data.Chi.magnitude',
        '/ENTRY[entry]/experiment_result/chi/@units': 'raw_data.Chi.units',
        '/ENTRY[entry]/experiment_result/phi': 'raw_data.Phi.magnitude',
        '/ENTRY[entry]/experiment_result/phi/@units': 'raw_data.Phi.units',
        '/ENTRY[entry]/experiment_config/count_time': 'raw_data.countTime.magnitude',
        '/ENTRY[entry]/experiment_config/count_time/@units': 'raw_data.countTime.units',
        'line': {
            '/ENTRY[entry]/experiment_result/q_norm': 'raw_data.q_norm.magnitude',
            '/ENTRY[entry]/experiment_result/q_norm/@units': 'raw_data.q_norm.units',
        },
        'rsm': {
            '/ENTRY[entry]/experiment_result/q_parallel': 'raw_data.q_parallel',
            '/ENTRY[entry]/experiment_result/q_parallel/@units': 'raw_data.q_parallel.units',
            '/ENTRY[entry]/experiment_result/q_perpendicular': 'raw_data.q_perpendicular.magnitude',
            '/ENTRY[entry]/experiment_result/q_perpendicular/@units': 'raw_data.q_perpendicular.units',
        },
        # Mapping data in NOMAD archive
        '/ENTRY[entry]/method': 'archive.data.method',
        '/ENTRY[entry]/measurement_type': 'archive.data.diffraction_method_name',
        '/ENTRY[entry]/INSTRUMENT[instrument]/DETECTOR[detector]/scan_axis': (
            'archive.data.results[0].scan_axis'
        ),
        '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/xray_tube_material': 'archive.data.xrd_settings.source.xray_tube_material',
        '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/xray_tube_current': 'archive.data.xrd_settings.source.xray_tube_current.magnitude',
        '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/xray_tube_current/@units': 'archive.data.xrd_settings.source.xray_tube_current.units',
        '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/xray_tube_voltage': 'archive.data.xrd_settings.source.xray_tube_voltage.magnitude',
        '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/xray_tube_voltage/@units': 'archive.data.xrd_settings.source.xray_tube_voltage.units',
        '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/k_alpha_one': 'archive.data.xrd_settings.source.kalpha_one.magnitude',
        '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/k_alpha_one/@units': 'archive.data.xrd_settings.source.kalpha_one.units',
        '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/k_alpha_two': 'archive.data.xrd_settings.source.kalpha_two.magnitude',
        '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/k_alpha_two/@units': 'archive.data.xrd_settings.source.kalpha_two.units',
        '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/ratio_k_alphatwo_k_alphaone': 'archive.data.xrd_settings.source.ratio_kalphatwo_kalphaone',
        '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/kbeta': 'archive.data.xrd_settings.source.kbeta.magnitude',
        '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/kbeta/@units': 'archive.data.xrd_settings.source.kbeta.units',
    }
)


def remove_nexus_annotations(mapping: dict) -> dict:
    """
    Remove the nexus related annotations from a keys of concept mapping.
    For example:
    '/ENTRY[entry]/experiment_result/intensity': 'raw_data.intensity.magnitude'
    will be converted to
    '/entry/experiment_result/intensity': 'raw_data.intensity.magnitude'

    Args:
        mapping: A mapping for the NeXus templates.

    Returns:
        dict: A new mapping with the nexus annotations removed.
    """
    pattern = r'.*\[.*\]'
    new_mapping = OrderedDict()
    for key, value in mapping.items():
        if isinstance(value, dict):
            new_mapping[key] = remove_nexus_annotations(value)
        elif isinstance(value, str):
            new_key = ''
            for part in key.split('/')[1:]:
                if re.match(pattern, part):
                    new_key += '/' + part.split('[')[0].strip().lower()
                else:
                    new_key += '/' + part
            new_mapping[new_key] = value
    return new_mapping


def walk_through_object(parent_obj, attr_chain, default=None):
    """
    Walk though the object until reach the leaf.

    Args:
        parent_obj: This is a python obj.
        attr_chain: Dot separated obj chain.
        default: A value to be returned by default, if not data is found.
    """
    try:
        expected_parts = 2
        if isinstance(attr_chain, str):
            parts = attr_chain.split('.', 1)

            if len(parts) == expected_parts:
                child_nm, rest_part = parts
                if '[' in child_nm:
                    child_nm, index = child_nm.split('[')
                    index = int(index[:-1])
                    child_obj = getattr(parent_obj, child_nm)[index]
                else:
                    child_obj = getattr(parent_obj, child_nm)
                return walk_through_object(child_obj, rest_part, default=default)
            else:
                return getattr(parent_obj, attr_chain, default)
    except (AttributeError, IndexError, KeyError, ValueError):
        return None


def connect_concepts(template, archive: 'EntryArchive', scan_type: str):  # noqa: PLR0912
    """
    Connect the concepts between `ELNXrayDiffraction` and `NXxrd_pan` schema.

    Args:
        template (Template): The pynxtools template, a inherited class from python dict.
        archive (EntryArchive): Nomad archive contains secttions, subsections and
            quantities.
        scan_type (str): Name of the scan type such as line and RSM.
    """

    for key, archive_concept in CONCEPT_MAP.items():
        if isinstance(archive_concept, dict):
            if key == scan_type:
                for sub_key, sub_archive_concept in archive_concept.items():
                    _, arch_attr = sub_archive_concept.split('.', 1)
                    value = walk_through_object(archive, arch_attr)
                    if value is not None:
                        template[sub_key] = (
                            str(value) if sub_key.endswith('units') else value
                        )
            else:
                continue
        elif archive_concept:
            _, arch_attr = archive_concept.split('.', 1)
            value = walk_through_object(archive, arch_attr)
            # Use multiple excepts to avoid catching all exceptions
            if value is not None:
                template[key] = str(value) if key.endswith('units') else value

    template['/ENTRY[entry]/definition'] = 'NXxrd_pan'

    # Links to the data and concepts
    template['/ENTRY[entry]/@default'] = 'experiment_result'
    template['/ENTRY[entry]/experiment_result/@signal'] = 'intensity'
    template['/ENTRY[entry]/experiment_result/@axes'] = 'two_theta'
    template['/ENTRY[entry]/q_data/q'] = {
        'link': '/ENTRY[entry]/experiment_result/q_norm'
    }
    template['/ENTRY[entry]/q_data/intensity'] = {
        'link': '/ENTRY[entry]/experiment_result/intensity'
    }
    template['/ENTRY[entry]/q_data/q_parallel'] = {
        'link': '/ENTRY[entry]/experiment_result/q_parallel'
    }
    template['/ENTRY[entry]/q_data/q_perpendicular'] = {
        'link': '/ENTRY[entry]/experiment_result/q_perpendicular'
    }


def write_nx_section_and_create_file(
    archive: 'EntryArchive', logger: 'BoundLogger', scan_type: str = 'line'
):
    """
    Uses the archive to generate the NeXus section and .nxs file.

    Args:
        archive (EntryArchive): The archive containing the section.
        logger (BoundLogger): A structlog logger.
        generate_nexus_file (boolean): If True, the function will generate a .nxs file.
        nxs_as_entry (boolean): If True, the function will generate a .nxs file
                as a nomad entry.
    """
    nxdl_root, _ = dataconverter.helpers.get_nxdl_root_and_path('NXxrd_pan')
    template = dataconverter.template.Template()
    dataconverter.helpers.generate_template_from_nxdl(nxdl_root, template)
    connect_concepts(template, archive, scan_type=scan_type)
    archive_name = archive.metadata.mainfile.split('.')[0]
    nexus_output = f'{archive_name}.nxs'

    populate_nexus_subsection(
        template=template,
        app_def='NXxrd_pan',
        archive=archive,
        logger=logger,
        output_file_path=nexus_output,
    )
