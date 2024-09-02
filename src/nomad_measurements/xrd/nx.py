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


def connect_concepts_from_dict(xrd_dict, template, scan_type: str):
    """
    Connect the concepts between `ELNXrayDiffraction` and `NXxrd_pan` schema.

    Args:
        archive (EntryArchive): The Nomad archive object.
        xrd_dict (dict): A dictionary containing the data from experiment file and
                eln data under the key `eln_dict`.
        template (Template): A template object containing the NXxrd_pan schema.
        scan_type (str): The type of scan, either 'line' or 'rsm'
    """

    def __set_data_and_units(
        temp_key, data_dict, data_path=None, units=None, units_path=None, **kwargs
    ):
        data = data_dict.get(data_path, None)
        if data is not None:
            template[temp_key] = data
            if units:
                pass
            elif units_path is not None:
                units = data_dict.get(units_path, None)
            if units:
                template[temp_key + '/@units'] = units

    eln_dict = xrd_dict['eln_dict']

    # ruff: noqa: E501
    # Genneral concepts
    concept_links_from_eln_dict = {
        '/ENTRY[entry]/method': {'data_path': 'method', 'units': ''},
        '/ENTRY[entry]/measurement_type': {
            'data_path': 'diffraction_method_name',
            'units': '',
        },
        # Source
        '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/xray_tube_material': {
            'data_path': 'xray_tube_material',
            'units': '',
        },
        '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/xray_tube_current': {
            'data_path': 'xray_tube_current',
            'units_path': 'xray_tube_current/units',
        },
        '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/xray_tube_voltage': {
            'data_path': 'xray_tube_voltage',
            'units_path': 'xray_tube_voltage/units',
        },
        '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/k_alpha_one': {
            'data_path': 'kalpha_one',
            'units_path': 'kalpha_one/units',
        },
        '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/k_alpha_two': {
            'data_path': 'kalpha_two',
            'units_path': 'kalpha_two/units',
        },
        '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/ratio_k_alphatwo_k_alphaone': {
            'data_path': 'ratio_kalphatwo_kalphaone',
            'units_path': '',
        },
        '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/kbeta': {
            'data_path': 'kbeta',
            'units_path': 'kbeta/units',
        },
    }

    concept_links_from_xrd_dict = {
        '/ENTRY[entry]/experiment_result/intensity': {
            'data_path': 'intensity',
            'units': 'counts per second',
        },
        '/ENTRY[entry]/experiment_result/two_theta': {
            'data_path': '2Theta',
            'units': 'deg',
        },
        '/ENTRY[entry]/experiment_result/omega': {'data_path': 'Omega', 'units': 'deg'},
        '/ENTRY[entry]/experiment_result/chi': {'data_path': 'Chi', 'units': 'deg'},
        '/ENTRY[entry]/experiment_result/phi': {'data_path': 'Phi', 'units': 'deg'},
        '/ENTRY[entry]/INSTRUMENT[instrument]/DETECTOR[detector]/scan_axis': scan_type,
        '/ENTRY[entry]/experiment_config/count_time': {
            'data_path': 'countTime',
            'units': 's',
        },
        '/ENTRY[entry]/experiment_result/q_norm': {
            'data_path': 'q_norm',
            'units': '1/m',
        },
        # Scan type specific concepts
        'line': '',  # for future implementation
        'rsm': {
            '/ENTRY[entry]/experiment_result/q_parallel': {
                'data_path': 'q_parallel',
                'units': '1/m',
            },
            '/ENTRY[entry]/experiment_result/q_perpendicular': {
                'data_path': 'q_perpendicular',
                'units': '1/m',
            },
        },
    }

    for key, value in concept_links_from_xrd_dict.items():
        if key in ['line', 'rsm'] and isinstance(value, dict):
            # run for provided scan_type
            if key != scan_type:
                continue
            for k, v in value.items():
                __set_data_and_units(k, xrd_dict, **v)
        elif isinstance(value, dict):
            __set_data_and_units(key, xrd_dict, **value)
        elif value not in ['', None]:
            template[key] = value

    for key, value in concept_links_from_eln_dict.items():
        if isinstance(value, dict):
            __set_data_and_units(key, eln_dict, **value)
        elif value not in ['', None]:
            template[key] = value

    template['/ENTRY[entry]/definition'] = 'NXxrd_pan'
    template['/ENTRY[entry]/@default'] = 'experiment_result'
    # Links to the data and concepts
    template['/ENTRY[entry]/experiment_result/@signal'] = 'intensity'
    template['/ENTRY[entry]/experiment_result/@axes'] = 'two_theta'
    template['/ENTRY[entry]/q_data/q'] = {'link': '/entry/experiment_result/q_norm'}
    template['/ENTRY[entry]/q_data/intensity'] = {
        'link': '/entry/experiment_result/intensity'
    }
    template['/ENTRY[entry]/q_data/q_parallel'] = {
        'link': '/entry/experiment_result/q_parallel'
    }
    template['/ENTRY[entry]/q_data/q_perpendicular'] = {
        'link': '/entry/experiment_result/q_perpendicular'
    }


def write_nx_section_and_create_file(
    archive: 'EntryArchive', logger: 'BoundLogger', nx_file, xrd_dict, scan_type='line'
):
    """
    Uses the archive to generate the NeXus section and .nxs file.
    Args:
        archive (EntryArchive): The Nomad archive containing the root section.
        logger (BoundLogger): A structlog logger.
        nx_file (str): The name of the .nxs file to be generated
        xrd_dict (dict): A dictionary containing the data from experiment file and
                eln data under the key 'eln_dict
        scan_type (str): The type of scan, either 'line' or 'rsm'
    """
    app_def = 'NXxrd_pan'
    nxdl_root, _ = dataconverter.helpers.get_nxdl_root_and_path(app_def)
    template = dataconverter.template.Template()
    dataconverter.helpers.generate_template_from_nxdl(nxdl_root, template)
    connect_concepts_from_dict(
        xrd_dict=xrd_dict, template=template, scan_type=scan_type
    )

    populate_nexus_subsection(
        template=template,
        app_def=app_def,
        archive=archive,
        logger=logger,
        output_file_path=nx_file,
    )
