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
from nomad_measurements import xrd
from pynxtools.nomad.dataconverter import populate_nexus_subsection
from pynxtools import dataconverter


if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive


# source_peak_wavelength
def connect_concepts_from_archive(archive: 'EntryArchive', template, scan_type: str):
    """Connect the concepts between ELNXrayDiffraction and NXxrd_pan schema."""

    # Genneral concepts
    try:
        template['/ENTRY[entry]/definition'] = 'NXxrd_pan'
    except AttributeError as e:
        pass

    try:
        template['/ENTRY[entry]/method'] = archive.data.method
    except AttributeError as e:
        pass

    try:
        template['/ENTRY[entry]/measurement_type'] = (
            archive.data.diffraction_method_name
        )
    except AttributeError as e:
        pass

    # Technique specific concepts
    if scan_type == 'line':
        try:
            template['/ENTRY[entry]/experiment_result/intensity'] = archive.data.results[0].intensity.magnitude
        except AttributeError as e:
            pass

        try:
            template['/ENTRY[entry]/experiment_result/two_theta'] = archive.data.results[0].two_theta.magnitude
            template['/ENTRY[entry]/experiment_result/two_theta/@units'] = archive.data.results[0].two_theta.units.__str__()
        except AttributeError as e:
            pass

        try:
            template['/ENTRY[entry]/experiment_result/omega'] = archive.data.results[0].omega.magnitude
            template['/ENTRY[entry]/experiment_result/omega/@units'] = archive.data.results[0].omega.units.__str__()
        except AttributeError as e:
            pass

        try:
            template['/ENTRY[entry]/experiment_result/chi'] = archive.data.results[0].chi.magnitude
            template['/ENTRY[entry]/experiment_result/chi/@units'] = archive.data.results[0].chi.units.__str__()
        except AttributeError as e:
            pass

        try:
            template['/ENTRY[entry]/experiment_result/phi'] = archive.data.results[0].phi.magnitude
            template['/ENTRY[entry]/experiment_result/phi/@units'] = archive.data.results[0].phi.units.__str__()
        except AttributeError as e:
            pass

        try:
            template[
                '/ENTRY[entry]/INSTRUMENT[instrument]/DETECTOR[detector]/scan_axis'
            ] = archive.data.results[0].scan_axis
        except AttributeError as e:
            pass

        try:
            template['/ENTRY[entry]/experiment_config/count_time'] = archive.data.results[0].count_time.magnitude
        except AttributeError as e:
            pass
    # rsm
    elif scan_type == 'rsm':
        try:
            template['/ENTRY[entry]/experiment_result/intensity'] = archive.data.results[0].intensity.magnitude
        except AttributeError as e:
            pass

        try:
            template['/ENTRY[entry]/experiment_result/two_theta'] = archive.data.results[0].two_theta.magnitude
            template['/ENTRY[entry]/experiment_result/two_theta/@units'] = archive.data.results[0].two_theta.units.__str__()
        except AttributeError as e:
            pass

        try:
            template['/ENTRY[entry]/experiment_result/omega'] = archive.data.results[0].omega.magnitude
            template['/ENTRY[entry]/experiment_result/omega/@units'] = archive.data.results[0].omega.units.__str__()
        except AttributeError as e:
            pass

        try:
            template['/ENTRY[entry]/experiment_result/chi'] = archive.data.results[0].chi.magnitude
            template['/ENTRY[entry]/experiment_result/chi/@units'] = archive.data.results[0].chi.units.__str__()
        except AttributeError as e:
            pass

        try:
            template['/ENTRY[entry]/experiment_result/phi'] = archive.data.results[0].phi.magnitude
            template['/ENTRY[entry]/experiment_result/phi/@units'] = archive.data.results[0].phi.units.__str__()
        except AttributeError as e:
            pass

        try:
            template[
                '/ENTRY[entry]/INSTRUMENT[instrument]/DETECTOR[detector]/scan_axis'
            ] = archive.data.results[0].scan_axis
        except AttributeError as e:
            pass

        try:
            template['/ENTRY[entry]/experiment_config/count_time'] = archive.data.results[0].count_time.magnitude
        except AttributeError as e:
            pass

        try:
            template['/ENTRY[entry]/experiment_result/q_parallel'] = archive.data.results[0].q_parallel,
            template['/ENTRY[entry]/experiment_result/q_parallel/@units'] = archive.data.results[0].q_parallel.units.__str__()
        except AttributeError as e:
            pass

        try:
            template['/ENTRY[entry]/experiment_result/q_perpendicular'] = archive.data.results[0].q_perpendicular.magnitude
            template['/ENTRY[entry]/experiment_result/q_perpendicular/@units'] = archive.data.results[0].q_perpendicular.units.__str__()
        except AttributeError as e:
            pass

        try:
            template['/ENTRY[entry]/experiment_result/q_norm'] = archive.data.results[0].q_norm.magnitude
            template['/ENTRY[entry]/experiment_result/q_norm/@units'] = archive.data.results[0].q_norm.units.__str__()
        except AttributeError as e:
            pass

    # Source
    try:
        template[
            '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/xray_tube_material'
        ] = archive.data.xrd_settings.source.xray_tube_material
    except AttributeError as e:
        pass

    try:
        template[
            '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/xray_tube_current'
        ] = archive.data.xrd_settings.source.xray_tube_current.magnitude
        template[
            '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/xray_tube_current/@units'
        ] = archive.data.xrd_settings.source.xray_tube_current.units.__str__()
    except AttributeError as e:
        pass

    try:
        template[
            '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/xray_tube_voltage'
        ] = archive.data.xrd_settings.source.xray_tube_voltage.magnitude
        template[
            '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/xray_tube_voltage/@units'
        ] = archive.data.xrd_settings.source.xray_tube_voltage.units.__str__()
    except AttributeError as e:
        pass

    try:
        template[
            '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/k_alpha_one'
        ] = archive.data.xrd_settings.source.kalpha_one.magnitude
        template[
            '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/k_alpha_one/@units'
        ] = archive.data.xrd_settings.source.kalpha_one.units.__str__()
    except AttributeError as e:
        pass

    try:
        template[
            '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/k_alpha_two'
        ] = archive.data.xrd_settings.source.kalpha_two.magnitude
        template[
            '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/k_alpha_two/@units'
        ] = archive.data.xrd_settings.source.kalpha_two.units.__str__()
    except AttributeError as e:
        pass

    try:
        template[
            '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/ratio_k_alphatwo_k_alphaone'
        ] = archive.data.xrd_settings.source.ratio_kalphatwo_kalphaone
    except AttributeError as e:
        pass

    try:
        template['/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/kbeta'] = archive.data.xrd_settings.source.kbeta.magnitude
        template[
            '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/kbeta/@units'
        ] = archive.data.xrd_settings.source.kbeta.units.__str__()
    except AttributeError as e:
        pass
    
    # Links to the data and concepts
    template["//ENTRY[entry]/@default"] = "experiment_result"
    template["/ENTRY[entry]/experiment_result/@signal"] = "intensity"
    template["/ENTRY[entry]/experiment_result/@axes"] = "two_theta"
    template["/ENTRY[entry]/q_data/q"] = {
        "link": "/ENTRY[entry]/experiment_result/q_norm"
    }
    template["/ENTRY[entry]/q_data/intensity"] = {
        "link": "/ENTRY[entry]/experiment_result/intensity"
    }
    template["/ENTRY[entry]/q_data/q_parallel"] = {
        "link": "/ENTRY[entry]/experiment_result/q_parallel"
    }
    template["/ENTRY[entry]/q_data/q_perpendicular"] = {
        "link": "/ENTRY[entry]/experiment_result/q_perpendicular"
    }

# source_peak_wavelength
def connect_concepts_from_dict(xrd_dict, archive: 'EntryArchive', template, scan_type: str):
    """Connect the concepts between ELNXrayDiffraction and NXxrd_pan schema."""

    eln_dict = xrd_dict['eln_dict']
    # Genneral concepts
    template['/ENTRY[entry]/definition'] = 'NXxrd_pan'

    try:
        print(' #################### ', eln_dict)

        template['/ENTRY[entry]/method'] = eln_dict['method']
        print(' #################### ')
    except KeyError as e:
        pass

    try:
        template['/ENTRY[entry]/measurement_type'] = eln_dict['diffraction_method_name']
    except KeyError as e:
        pass

    # Source
    try:
        template[
            '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/xray_tube_material'
        ] = eln_dict['xray_tube_material']
    except KeyError as e:
        pass

    try:
        template[
            '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/xray_tube_current'
        ] = eln_dict['xray_tube_current']
        template[
            '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/xray_tube_current/@units'
        ] = eln_dict['xray_tube_current/unit']
    except KeyError as e:
        pass

    try:
        template[
            '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/xray_tube_voltage'
        ] = eln_dict['xray_tube_voltage']
        template[
            '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/xray_tube_voltage/@units'
        ] = eln_dict['xray_tube_voltage/unit']
    except KeyError as e:
        pass

    try:
        template[
            '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/k_alpha_one'
        ] = eln_dict['kalpha_one']
        template[
            '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/k_alpha_one/@units'
        ] = eln_dict['kalpha_one/unit']
    except KeyError as e:
        pass

    try:
        template[
            '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/k_alpha_two'
        ] = eln_dict['kalpha_two']
        template[
            '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/k_alpha_two/@units'
        ] = eln_dict['kalpha_two/unit']
    except KeyError as e:
        pass

    try:
        template[
            '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/ratio_k_alphatwo_k_alphaone'
        ] = eln_dict['ratio_kalphatwo_kalphaone']
    except KeyError as e:
        pass

    try:
        template['/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/kbeta'] = eln_dict['kbeta']
        template[
            '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/kbeta/@units'
        ] = eln_dict['kbeta/unit']
    except KeyError as e:
        pass

    # Result or scattering data
    try:
        template['/ENTRY[entry]/experiment_result/intensity'] = xrd_dict['intensity']
        template['/ENTRY[entry]/experiment_result/intensity/@units'] = 'counts per second'
    except KeyError as e:
        pass

    try:
        template['/ENTRY[entry]/experiment_result/two_theta'] = xrd_dict['2Theta']
        template['/ENTRY[entry]/experiment_result/two_theta/@units'] = 'deg'
    except KeyError as e:
        pass

    try:
        template['/ENTRY[entry]/experiment_result/omega'] = xrd_dict['Omega'],
        template['/ENTRY[entry]/experiment_result/omega/@units'] = 'deg'
    except KeyError as e:
        pass

    try:
        template['/ENTRY[entry]/experiment_result/chi'] = xrd_dict['Chi']
        template['/ENTRY[entry]/experiment_result/chi/@units'] = 'deg'
    except KeyError as e:
        pass

    try:
        template['/ENTRY[entry]/experiment_result/phi'] = xrd_dict['Phi']
        template['/ENTRY[entry]/experiment_result/phi/@units'] = 'deg'
    except KeyError as e:
        pass

    try:
        template[
            '/ENTRY[entry]/INSTRUMENT[instrument]/DETECTOR[detector]/scan_axis'
        ] = xrd_dict['metadata']['scan_axis']
    except KeyError as e:
        pass

    try:
        template['/ENTRY[entry]/experiment_config/count_time'] = xrd_dict['countTime']
        template['/ENTRY[entry]/experiment_config/count_time/@units'] = 's'
    except KeyError as e:
        pass
    try:
        template['/ENTRY[entry]/experiment_result/q_norm'] = xrd_dict['q_norm']
        template['/ENTRY[entry]/experiment_result/q_norm/@units'] = '1/m'
    except KeyError as e:
        pass


    if scan_type == 'line':
        pass
    # rsm
    elif scan_type == 'rsm':
        try:
            template['/ENTRY[entry]/experiment_result/q_parallel'] = xrd_dict['q_parallel']
            template['/ENTRY[entry]/experiment_result/q_parallel/@units'] = '1/m'
        except KeyError as e:
            pass

        try:
            template['/ENTRY[entry]/experiment_result/q_perpendicular'] = xrd_dict['q_perpendicular']
            template['/ENTRY[entry]/experiment_result/q_perpendicular/@units'] = '1/m'
        except KeyError as e:
            pass


    # Links to the data and concepts
    template["//ENTRY[entry]/@default"] = "experiment_result"
    template["/ENTRY[entry]/experiment_result/@signal"] = "intensity"
    template["/ENTRY[entry]/experiment_result/@axes"] = "two_theta"
    template["/ENTRY[entry]/q_data/q"] = {
        "link": "/entry/experiment_result/q_norm"
    }
    template["/ENTRY[entry]/q_data/intensity"] = {
        "link": "/entry/experiment_result/intensity"
    }
    template["/ENTRY[entry]/q_data/q_parallel"] = {
        "link": "/entry/experiment_result/q_parallel"
    }
    template["/ENTRY[entry]/q_data/q_perpendicular"] = {
        "link": "/entry/experiment_result/q_perpendicular"
    }


def write_nx_section_and_create_file(archive: 'EntryArchive',
                                     logger: 'BoundLogger',
                                     nx_file,
                                     nxs_as_entry,
                                     scan_type,
                                     xrd_dict = None,
                                     ):
    '''
    Uses the archive to generate the NeXus section and .nxs file.

    Args:
        archive (EntryArchive): The archive containing the section.
        logger (BoundLogger): A structlog logger.
        nx_file (str): The name of the .nxs file to be generated
        nxs_as_entry (boolean): If True, the function will generate a .nxs file
                as a nomad entry.
        scan_type (str): The type of scan, either 'line' or 'rsm'
        xrd_dict (dict): A dictionary containing the data from experiment file and 
                eln data under the key 'eln_dict
    '''
    entry_type = archive.metadata.entry_type
    nxdl_root, _ = dataconverter.helpers.get_nxdl_root_and_path("NXxrd_pan")
    template = dataconverter.template.Template()
    dataconverter.helpers.generate_template_from_nxdl(nxdl_root, template)
    # connect_concepts_from_archive(archive, template, scan_type='line')
    connect_concepts_from_dict(xrd_dict=xrd_dict,
                               archive=archive, 
                               template=template, 
                               scan_type=scan_type)

    populate_nexus_subsection(
        template=template,
        app_def="NXxrd_pan",
        archive=archive,
        logger=logger,
        output_file_path=nx_file,
        on_temp_file=False,
        nxs_as_entry=nxs_as_entry
    )
    archive.metadata.entry_type = entry_type
