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

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive


def check_and_connect_concept(xrd_pan_concept, eln_xrd_dif_concept, template):
    """Check the concept between two schema (ELNXrayDiffraction and NXxrd_pan)

    The ELNXrayDiffraction and NXxrd_pan both can handle multiple techniques of the
    X-ray diffraction measurements (e.g. Bragg-Brentano, Reciprocal Space Mapping (RSM)).
    So, all the concepts in this schema not the exactly the same for all techniques.

    This function will check the concept between the two schema and connect the concepts
    if they are available in both schema.

    Args:
        xrd_pan_concept (str): The concept from NXxrd_pan schema e.g. /ENTRY[entry]/definition.
        eln_xrd_dif_concept (Archive.quantity): The concept from ELNXrayDiffraction schema.
        template (dict): The template of the NXxrd_pan schema.
    """
    try:
        template[xrd_pan_concept] = eln_xrd_dif_concept
    except Exception as e:
        pass


def connect_concepts(template, archive: 'EntryArchive'):
    """Connect the concepts between ELNXrayDiffraction and NXxrd_pan schema."""
    template['/ENTRY[entry]/definition'] = 'NXxrd_pan'
    check_and_connect_concept('/ENTRY[entry]/method', archive.data.method, template)
    check_and_connect_concept(
        '/ENTRY[entry]/measurement_type', archive.data.diffraction_method_name, template
    )
    check_and_connect_concept(
        '/ENTRY[entry]/experiment_result/intensity',
        archive.data.results[0].intensity.magnitude,
        template,
    )
    check_and_connect_concept(
        '/ENTRY[entry]/experiment_result/two_theta',
        archive.data.results[0].two_theta.magnitude,
        template,
    )
    check_and_connect_concept(
        '/ENTRY[entry]/experiment_result/two_theta/@units',
        archive.data.results[0].two_theta.units,
        template,
    )
    check_and_connect_concept(
        '/ENTRY[entry]/experiment_result/omega',
        archive.data.results[0].omega.magnitude,
        template,
    )
    check_and_connect_concept(
        '/ENTRY[entry]/experiment_result/omega/@units',
        archive.data.results[0].omega.units,
        template,
    )
    check_and_connect_concept(
        '/ENTRY[entry]/experiment_result/chi',
        archive.data.results[0].chi.magnitude,
        template,
    )
    check_and_connect_concept(
        '/ENTRY[entry]/experiment_result/chi/@units',
        archive.data.results[0].chi.units,
        template,
    )
    check_and_connect_concept(
        '/ENTRY[entry]/experiment_result/phi',
        archive.data.results[0].phi.magnitude,
        template,
    )
    check_and_connect_concept(
        '/ENTRY[entry]/experiment_result/phi/@units',
        archive.data.data.results[0].phi.units,
        template,
    )
    check_and_connect_concept(
        '/ENTRY[entry]/experiment_result/q_parallel',
        archive.data.results[0].q_parallel.magnitude,
        template,
    )
    check_and_connect_concept(
        '/ENTRY[entry]/experiment_result/q_parallel/@units',
        archive.data.results[0].q_parallel.units,
        template,
    )
    check_and_connect_concept(
        '/ENTRY[entry]/experiment_result/q_perpendicular',
        archive.data.results[0].q_perpendicular.magnitude,
        template,
    )
    check_and_connect_concept(
        '/ENTRY[entry]/experiment_result/q_perpendicular/@units',
        archive.data.results[0].q_perpendicular.units,
        template,
    )
    check_and_connect_concept(
        '/ENTRY[entry]/experiment_result/q_norm',
        archive.data.results[0].q_norm.magnitude,
        template,
    )
    check_and_connect_concept(
        '/ENTRY[entry]/experiment_result/q_norm/@units',
        archive.data.results[0].q_norm.units,
        template,
    )

    template['/ENTRY[entry]/2theta_plot/intensity'] = archive.data.results[
        0
    ].intensity.magnitude
    template['/ENTRY[entry]/2theta_plot/two_theta'] = archive.data.results[
        0
    ].two_theta.magnitude
    template['/ENTRY[entry]/2theta_plot/two_theta/@units'] = str(
        archive.data.results[0].two_theta.units
    )
