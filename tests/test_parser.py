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
import os
import pytest

from nomad.client import parse, normalize_all


@pytest.fixture(
    params=[
        'XRD-918-16_10.xrdml',
        'm54313_om2th_10.xrdml',
        'm82762_rc1mm_1_16dg_src_slit_phi-101_3dg_-420_mesh_long.xrdml',
        '23-012-AG_2thomegascan_long.brml',
        'EJZ060_13_004_RSM.brml',
        'Omega-2Theta_scan_high_temperature.rasx',
        'RSM_111_sdd=350.rasx',
        'TwoTheta_scan_powder.rasx',
    ]
)
def parsed_archive(request):
    """
    Sets up data for testing and cleans up after the test.
    """
    rel_file = os.path.join('tests', 'data', request.param)
    file_archive = parse(rel_file)[0]
    measurement = os.path.join(
        'tests', 'data', '.'.join(request.param.split('.')[:-1]) + '.archive.json'
    )
    assert file_archive.data.measurement.m_proxy_value == os.path.abspath(measurement)
    measurement_archive = parse(measurement)[0]

    yield measurement_archive

    for file_path in [measurement, measurement.replace('archive.json', 'nxs')]:
            if os.path.exists(file_path):
                os.remove(file_path)


def test_normalize_all(parsed_archive):
    normalize_all(parsed_archive)
    print(parsed_archive.data)
    assert parsed_archive.data.xrd_settings.source.xray_tube_material == 'Cu'
    assert parsed_archive.data.results[
        0
    ].source_peak_wavelength.magnitude == pytest.approx(1.540598, 1e-2)
    if len(parsed_archive.data.results[0].intensity.shape) == 1:
        assert parsed_archive.results.properties.structural.diffraction_pattern[
            0
        ].incident_beam_wavelength.magnitude * 1e10 == pytest.approx(1.540598, 1e-2)
