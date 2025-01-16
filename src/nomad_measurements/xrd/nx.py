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

"""
The following connects the nexus file paths to the archive paths.
The nexus file paths come from the nexus_definitions available at:
https://github.com/FAIRmat-NFDI/nexus_definitions/ in the following file:
`contributed_definitions/NXxrd_pan.nxdl.xml`.
The archive paths are the paths in the NOMAD archive defined in the class:
`nomad_measurement.xrd.schema.ELNXRayDiffraction`.
"""

NEXUS_DATASET_MAP = {
    '/ENTRY[entry]/@default': 'experiment_result',
    '/ENTRY[entry]/definition': 'NXxrd_pan',
    '/ENTRY[entry]/experiment_result/intensity': 'archive.data.results[0].intensity',
    '/ENTRY[entry]/experiment_result/two_theta': 'archive.data.results[0].two_theta',
    '/ENTRY[entry]/experiment_result/omega': 'archive.data.results[0].omega',
    '/ENTRY[entry]/experiment_result/chi': 'archive.data.results[0].chi',
    '/ENTRY[entry]/experiment_result/phi': 'archive.data.results[0].phi',
    '/ENTRY[entry]/experiment_result/q_norm': 'archive.data.results[0].q_norm',
    '/ENTRY[entry]/experiment_result/q_parallel': 'archive.data.results[0].q_parallel',
    '/ENTRY[entry]/experiment_result/q_perpendicular': (
        'archive.data.results[0].q_perpendicular'
    ),
    '/ENTRY[entry]/method': 'archive.data.method',
    '/ENTRY[entry]/measurement_type': 'archive.data.diffraction_method_name',
    '/ENTRY[entry]/experiment_result/@signal': 'intensity',
    '/ENTRY[entry]/experiment_config/count_time': 'archive.data.results[0].count_time',
    '/ENTRY[entry]/INSTRUMENT[instrument]/DETECTOR[detector]/scan_axis': (
        'archive.data.results[0].scan_axis'
    ),
    '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/xray_tube_material': (
        'archive.data.xrd_settings.source.xray_tube_material'
    ),
    '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/xray_tube_current': (
        'archive.data.xrd_settings.source.xray_tube_current'
    ),
    '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/xray_tube_voltage': (
        'archive.data.xrd_settings.source.xray_tube_voltage'
    ),
    '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/k_alpha_one': (
        'archive.data.xrd_settings.source.kalpha_one'
    ),
    '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/k_alpha_two': (
        'archive.data.xrd_settings.source.kalpha_two'
    ),
    '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/ratio_k_alphatwo_k_alphaone': (
        'archive.data.xrd_settings.source.ratio_kalphatwo_kalphaone'
    ),
    '/ENTRY[entry]/INSTRUMENT[instrument]/SOURCE[source]/kbeta': (
        'archive.data.xrd_settings.source.kbeta'
    ),
}
