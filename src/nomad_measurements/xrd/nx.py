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
from pynxtools.nomad.dataconverter import populate_nexus_subsection
from pynxtools import dataconverter


if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive


def check_hdf5_incompatible_unit(unit: str):
    """In hdf5 file degree symbol 'o' is incompatible getting an error.

    TypeError: Object dtype dtype('O') has no native HDF5 equivalent
    As 'O' is not a string type.
    """
    if unit == 'degree' or unit == 'deg':
        return 'degree'
    return unit

# source_peak_wavelength
def connect_concepts(template, archive: 'EntryArchive', scan_type: str):
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
            template['/ENTRY[entry]/experiment_result/two_theta/@units'] = check_hdf5_incompatible_unit(archive.data.results[0].two_theta.units)
        except AttributeError as e:
            pass

        try:
            template['/ENTRY[entry]/experiment_result/omega'] = archive.data.results[0].omega.magnitude
            template['/ENTRY[entry]/experiment_result/omega/@units'] = check_hdf5_incompatible_unit(archive.data.results[0].omega.units)
        except AttributeError as e:
            pass

        try:
            template['/ENTRY[entry]/experiment_result/chi'] = archive.data.results[0].chi.magnitude
            template['/ENTRY[entry]/experiment_result/chi/@units'] = check_hdf5_incompatible_unit(archive.data.results[0].chi.units)
        except AttributeError as e:
            pass

        try:
            template['/ENTRY[entry]/experiment_result/phi'] = archive.data.results[0].phi.magnitude
            template['/ENTRY[entry]/experiment_result/phi/@units'] = check_hdf5_incompatible_unit(archive.data.results[0].phi.units)
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
            template['/ENTRY[entry]/experiment_result/two_theta/@units'] = check_hdf5_incompatible_unit(archive.data.results[0].two_theta.units)
        except AttributeError as e:
            pass

        try:
            template['/ENTRY[entry]/experiment_result/omega'] = archive.data.results[0].omega.magnitude
            template['/ENTRY[entry]/experiment_result/omega/@units'] = check_hdf5_incompatible_unit(archive.data.results[0].omega.units)
        except AttributeError as e:
            pass

        try:
            template['/ENTRY[entry]/experiment_result/chi'] = archive.data.results[0].chi.magnitude
            template['/ENTRY[entry]/experiment_result/chi/@units'] = check_hdf5_incompatible_unit(archive.data.results[0].chi.units)
        except AttributeError as e:
            pass

        try:
            template['/ENTRY[entry]/experiment_result/phi'] = archive.data.results[0].phi.magnitude
            template['/ENTRY[entry]/experiment_result/phi/@units'] = check_hdf5_incompatible_unit(archive.data.results[0].phi.units)
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
            template['/ENTRY[entry]/experiment_result/q_parallel/@units'] = check_hdf5_incompatible_unit(archive.data.results[0].q_parallel.units)
        except AttributeError as e:
            pass

        try:
            template['/ENTRY[entry]/experiment_result/q_perpendicular'] = archive.data.results[0].q_perpendicular.magnitude
            template['/ENTRY[entry]/experiment_result/q_perpendicular/@units'] = check_hdf5_incompatible_unit(archive.data.results[0].q_perpendicular.units)
        except AttributeError as e:
            pass

        try:
            template['/ENTRY[entry]/experiment_result/q_norm'] = archive.data.results[0].q_norm.magnitude
            template['/ENTRY[entry]/experiment_result/q_norm/@units'] = check_hdf5_incompatible_unit(archive.data.results[0].q_norm.units)
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
        ] = archive.data.xrd_settings.source.xray_tube_current.units
    except AttributeError as e:
        pass

    try:
        template[
            '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/xray_tube_voltage'
        ] = archive.data.xrd_settings.source.xray_tube_voltage.magnitude
        template[
            '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/xray_tube_voltage/@units'
        ] = archive.data.xrd_settings.source.xray_tube_voltage.units
    except AttributeError as e:
        pass

    try:
        template[
            '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/k_alpha_one'
        ] = archive.data.xrd_settings.source.kalpha_one.magnitude
        template[
            '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/k_alpha_one/@units'
        ] = archive.data.xrd_settings.source.kalpha_one.units
    except AttributeError as e:
        pass

    try:
        template[
            '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/k_alpha_two'
        ] = archive.data.xrd_settings.source.kalpha_two.magnitude
        template[
            '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/k_alpha_two/@units'
        ] = archive.data.xrd_settings.source.kalpha_two.units
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
        ] = archive.data.xrd_settings.source.kbeta.units
    except AttributeError as e:
        pass
    
    # Some links to the data and concepts
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
    },

def write_nx_section_and_create_file(archive: 'EntryArchive', 
                                     logger: 'BoundLogger',
                                     generate_nexus_file,
                                     nxs_as_entry):
    '''
    Uses the archive to generate the NeXus section and .nxs file.

    Args:
        archive (EntryArchive): The archive containing the section.
        logger (BoundLogger): A structlog logger.
        generate_nexus_file (boolean): If True, the function will generate a .nxs file.
        nxs_as_entry (boolean): If True, the function will generate a .nxs file
                as a nomad entry.
    '''
    entry_type = archive.metadata.entry_type
    nxdl_root, _ = dataconverter.helpers.get_nxdl_root_and_path("NXxrd_pan")
    template = dataconverter.template.Template()
    dataconverter.helpers.generate_template_from_nxdl(nxdl_root, template)
    connect_concepts(template, archive, scan_type='line')
    archive_name = archive.metadata.mainfile.split('.')[0]
    nexus_output = f'{archive_name}_output.nxs'

    populate_nexus_subsection(
        template=template,
        app_def="NXxrd_pan",
        archive=archive,
        logger=logger,
        output_file_path=nexus_output,
        on_temp_file=generate_nexus_file,
        nxs_as_entry=nxs_as_entry
    )
    archive.metadata.entry_type = entry_type