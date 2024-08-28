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

from pynxtools import dataconverter
from pynxtools.nomad.dataconverter import populate_nexus_subsection

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import (
        BoundLogger,
    )


def walk_through_object(parent_obj, attr_chain, default=None):
    """
    Walk though the object until reach the leaf.

    Args:
        parent_obj: This is a python obj.
        attr_chain: Dot separated obj chain.
        default: A value to be returned by default, if not data is found.
    """
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


def connect_concepts(template, archive: 'EntryArchive', scan_type: str):
    """
    Connect the concepts between `ELNXrayDiffraction` and `NXxrd_pan` schema.

    Args:
        template (Template): The pynxtools template, a inherited class from python dict.
        archive (EntryArchive): Nomad archive contains secttions, subsections and
            quantities.
        scan_type (str): Name of the scan type such as line and RSM.
    """

    # General concepts
    # ruff: noqa: E501
    concept_map = {
        '/ENTRY[entry]/method': 'archive.data.method',
        '/ENTRY[entry]/measurement_type': 'archive.data.diffraction_method_name',
        '/ENTRY[entry]/experiment_result/intensity': 'archive.data.results[0].intensity.magnitude',
        '/ENTRY[entry]/experiment_result/two_theta': 'archive.data.results[0].two_theta.magnitude',
        '/ENTRY[entry]/experiment_result/two_theta/@units': 'archive.data.results[0].two_theta.units',
        '/ENTRY[entry]/experiment_result/omega': 'archive.data.results[0].omega.magnitude',
        '/ENTRY[entry]/experiment_result/omega/@units': 'archive.data.results[0].omega.units',
        '/ENTRY[entry]/experiment_result/chi': 'archive.data.results[0].chi.magnitude',
        '/ENTRY[entry]/experiment_result/chi/@units': 'archive.data.results[0].chi.units',
        '/ENTRY[entry]/experiment_result/phi': 'archive.data.results[0].phi.magnitude',
        '/ENTRY[entry]/experiment_result/phi/@units': 'archive.data.results[0].phi.units',
        '/ENTRY[entry]/INSTRUMENT[instrument]/DETECTOR[detector]/scan_axis': 'archive.data.results[0].scan_axis',
        '/ENTRY[entry]/experiment_config/count_time': 'archive.data.results[0].count_time.magnitude',
        'line': '',  # For future implementation
        'rsm': {
            '/ENTRY[entry]/experiment_result/q_parallel': 'archive.data.results[0].q_parallel',
            '/ENTRY[entry]/experiment_result/q_parallel/@units': 'archive.data.results[0].q_parallel.units',
            '/ENTRY[entry]/experiment_result/q_perpendicular': 'archive.data.results[0].q_perpendicular.magnitude',
            '/ENTRY[entry]/experiment_result/q_perpendicular/@units': 'archive.data.results[0].q_perpendicular.units',
            '/ENTRY[entry]/experiment_result/q_norm': 'archive.data.results[0].q_norm.magnitude',
            '/ENTRY[entry]/experiment_result/q_norm/@units': 'archive.data.results[0].q_norm.units',
        },
        # Source
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

    for key, archive_concept in concept_map.items():
        if isinstance(archive_concept, dict):
            if key == scan_type:
                for sub_key, sub_archive_concept in archive_concept.items():
                    _, arch_attr = sub_archive_concept.split('.', 1)
                    value = None
                    try:
                        value = walk_through_object(archive, arch_attr)
                    except (AttributeError, IndexError, KeyError, ValueError):
                        pass
                    finally:
                        if value is not None:
                            template[sub_key] = (
                                str(value)
                                if sub_key.endswith('units')
                                else value
                            )
            else:
                continue
        elif archive_concept:
            _, arch_attr = archive_concept.split('.', 1)
            value = None
            try:
                value = walk_through_object(archive, arch_attr)
            # Use multiple excepts to avoid catching all exceptions
            except (AttributeError, IndexError, KeyError, ValueError):
                pass
            finally:
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
