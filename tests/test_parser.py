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
import pytest
from nomad.client import normalize_all

test_files = [
    'tests/data/xrd/XRD-918-16_10.xrdml',
    'tests/data/xrd/m54313_om2th_10.xrdml',
    'tests/data/xrd/m82762_rc1mm_1_16dg_src_slit_phi-101_3dg_-420_mesh_long.xrdml',
    'tests/data/xrd/23-012-AG_2thomegascan_long.brml',
    'tests/data/xrd/EJZ060_13_004_RSM.brml',
    'tests/data/xrd/Omega-2Theta_scan_high_temperature.rasx',
    'tests/data/xrd/RSM_111_sdd=350.rasx',
    'tests/data/xrd/TwoTheta_scan_powder.rasx',
]
log_levels = ['error', 'critical']


@pytest.mark.parametrize(
    'parsed_measurement_archive, caplog',
    [(file, log_level) for file in test_files for log_level in log_levels],
    indirect=True,
)
def test_normalize_all(parsed_measurement_archive, caplog):
    """
    Tests the normalization of the parsed archive.

    Args:
        parsed_archive (pytest.fixture): Fixture to handle the parsing of archive.
        caplog (pytest.fixture): Fixture to capture errors from the logger.
    """
    normalize_all(parsed_measurement_archive)

    assert (
        parsed_measurement_archive.data.xrd_settings.source.xray_tube_material == 'Cu'
    )
    assert parsed_measurement_archive.data.results[
        0
    ].source_peak_wavelength.magnitude == pytest.approx(1.540598, 1e-2)
    if len(parsed_measurement_archive.data.results[0].intensity.shape) == 1:
        assert (
            parsed_measurement_archive.results.properties.structural.diffraction_pattern[
                0
            ].incident_beam_wavelength.magnitude
            * 1e10
            == pytest.approx(1.540598, 1e-2)
        )
