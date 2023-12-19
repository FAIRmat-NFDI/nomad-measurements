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

import pytest

from nomad.client import parse, normalize_all

@pytest.mark.parametrize('file', [
    'XRD-918-16_10.xrdml',
    'm54313_om2th_10.xrdml',
    '23-012-AG_2thomegascan_long.brml',
    'Omega-2Theta_scan_high_temperature.rasx',
    'RSM_111_sdd=350.rasx',
    'TwoTheta_scan_powder.rasx',
])
def test_parser(file):
    rel_file = os.path.join('tests', 'data', file)
    file_archive = parse(rel_file)[0]
    measurement = os.path.join('tests', 'data', '.'.join(file.split('.')[:-1]) + '.archive.json')
    assert file_archive.data.measurement.m_proxy_value == os.path.abspath(measurement)
    measurement_archive = parse(measurement)[0]
    normalize_all(measurement_archive)
    assert measurement_archive.data.xrd_settings.source.xray_tube_material == 'Cu'
